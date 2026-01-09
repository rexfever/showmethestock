# 스케줄러 v2/v3 동시 스캔 변경 계획

**작성일**: 2026-01-08  
**목적**: 사용자가 v2, v3를 선택해서 사용할 수 있도록 v2와 v3 스캔을 모두 실행

---

## 현재 상황

### 현재 스케줄러 동작
- **실행 시점**: 매일 오후 3시 42분 KST
- **실행 함수**: `run_scan()`
- **동작 방식**: `get_active_engine()`으로 활성 엔진 확인 후 해당 엔진만 실행
- **문제점**: v2와 v3 중 하나만 실행되므로, 사용자가 선택할 수 없음

### 현재 `/scan` API 동작
- `get_active_engine()`으로 활성 엔진 확인
- 활성 엔진에 따라 v1/v2/v3 중 하나만 실행
- `scanner_version` 파라미터 없음

---

## 변경 계획

### 목표
1. 스케줄러에서 v2와 v3 스캔을 모두 실행
2. 각 버전의 결과를 `scan_rank` 테이블에 저장
3. 사용자는 프론트엔드에서 v2 또는 v3 선택 가능

---

## 구현 계획

### 1단계: `/scan` API에 `scanner_version` 파라미터 추가

**변경 파일**: `backend/main.py`

**변경 내용**:
```python
@app.get('/scan', response_model=ScanResponse)
def scan(
    kospi_limit: int = None, 
    kosdaq_limit: int = None, 
    save_snapshot: bool = True, 
    sort_by: str = 'score', 
    date: str = None,
    scanner_version: Optional[str] = None  # 추가
):
    # scanner_version이 있으면 해당 버전 사용
    # 없으면 get_active_engine() 사용 (하위 호환성)
    
    if scanner_version and scanner_version in ['v1', 'v2', 'v3']:
        target_engine = scanner_version
    else:
        from scanner_settings_manager import get_active_engine
        target_engine = get_active_engine()
    
    # target_engine에 따라 스캔 실행
    if target_engine == 'v3':
        # V3 엔진 실행
        ...
    elif target_engine == 'v2':
        # V2 엔진 실행
        ...
    else:
        # V1 엔진 실행
        ...
```

**장점**:
- 하위 호환성 유지 (기존 코드 영향 없음)
- 명시적으로 버전 지정 가능
- 테스트 용이

---

### 2단계: 스케줄러에서 v2와 v3 모두 실행

**변경 파일**: `backend/scheduler.py`

**변경 내용**:

#### 옵션 A: 순차 실행 (권장)
```python
def run_scan():
    """한국 주식 스캔 실행 (15:42) - v2와 v3 모두 실행"""
    if not is_trading_day():
        logger.info(f"오늘은 거래일이 아닙니다. 스캔을 건너뜁니다.")
        return
    
    try:
        env_info = get_environment_info()
        backend_url = "http://localhost:8010"
        
        # v2 스캔 실행
        logger.info("📈 한국 주식 v2 스캔 시작...")
        response_v2 = requests.get(
            f"{backend_url}/scan?save_snapshot=true&scanner_version=v2", 
            timeout=300
        )
        
        if response_v2.status_code == 200:
            data_v2 = response_v2.json()
            matched_count_v2 = data_v2.get('matched_count', 0)
            logger.info(f"✅ v2 스캔 완료: {matched_count_v2}개 종목 매칭")
        else:
            logger.error(f"v2 스캔 실패: HTTP {response_v2.status_code}")
        
        # v3 스캔 실행
        logger.info("📈 한국 주식 v3 스캔 시작...")
        response_v3 = requests.get(
            f"{backend_url}/scan?save_snapshot=true&scanner_version=v3", 
            timeout=300
        )
        
        if response_v3.status_code == 200:
            data_v3 = response_v3.json()
            matched_count_v3 = data_v3.get('matched_count', 0)
            logger.info(f"✅ v3 스캔 완료: {matched_count_v3}개 종목 매칭")
        else:
            logger.error(f"v3 스캔 실패: HTTP {response_v3.status_code}")
        
        # 알림 발송 (v2와 v3 중 더 많은 매칭 수 사용)
        total_matched = max(matched_count_v2, matched_count_v3)
        send_auto_notification(total_matched)
        
    except Exception as e:
        logger.error(f"한국 주식 자동 스캔 중 오류 발생: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
```

#### 옵션 B: 병렬 실행 (성능 최적화)
```python
import concurrent.futures

def run_scan():
    """한국 주식 스캔 실행 (15:42) - v2와 v3 병렬 실행"""
    if not is_trading_day():
        logger.info(f"오늘은 거래일이 아닙니다. 스캔을 건너뜁니다.")
        return
    
    try:
        env_info = get_environment_info()
        backend_url = "http://localhost:8010"
        
        def run_scan_version(version: str):
            """특정 버전의 스캔 실행"""
            try:
                logger.info(f"📈 한국 주식 {version} 스캔 시작...")
                response = requests.get(
                    f"{backend_url}/scan?save_snapshot=true&scanner_version={version}", 
                    timeout=300
                )
                
                if response.status_code == 200:
                    data = response.json()
                    matched_count = data.get('matched_count', 0)
                    logger.info(f"✅ {version} 스캔 완료: {matched_count}개 종목 매칭")
                    return {'version': version, 'matched_count': matched_count, 'success': True}
                else:
                    logger.error(f"{version} 스캔 실패: HTTP {response.status_code}")
                    return {'version': version, 'matched_count': 0, 'success': False}
            except Exception as e:
                logger.error(f"{version} 스캔 중 오류: {e}")
                return {'version': version, 'matched_count': 0, 'success': False}
        
        # v2와 v3 병렬 실행
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future_v2 = executor.submit(run_scan_version, 'v2')
            future_v3 = executor.submit(run_scan_version, 'v3')
            
            result_v2 = future_v2.result()
            result_v3 = future_v3.result()
        
        # 알림 발송
        total_matched = max(result_v2['matched_count'], result_v3['matched_count'])
        send_auto_notification(total_matched)
        
    except Exception as e:
        logger.error(f"한국 주식 자동 스캔 중 오류 발생: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
```

**권장**: 옵션 A (순차 실행)
- 구현 간단
- 에러 추적 용이
- 리소스 사용 예측 가능
- v2와 v3가 독립적으로 실행되므로 병렬화 이점 제한적

---

### 3단계: `save_scan_snapshot` 함수 확인

**확인 사항**:
- `save_scan_snapshot` 함수가 `scanner_version` 파라미터를 올바르게 처리하는지 확인
- v2와 v3 결과가 `scan_rank` 테이블에 올바르게 저장되는지 확인

**현재 코드** (`backend/services/scan_service.py`):
```python
def save_scan_snapshot(scan_items: List[Dict], today_as_of: str, scanner_version: str = None) -> None:
    # scanner_version이 None이면 현재 활성화된 버전 사용
    if scanner_version is None:
        try:
            from scanner_settings_manager import get_scanner_version
            scanner_version = get_scanner_version()
        except Exception:
            from config import config
            scanner_version = getattr(config, 'scanner_version', 'v1')
```

**확인 필요**:
- `/scan` API에서 `scanner_version`을 `save_scan_snapshot`에 전달하는지 확인
- v2와 v3 결과가 서로 덮어쓰지 않는지 확인

---

### 4단계: 프론트엔드 연동 확인

**확인 사항**:
- 프론트엔드에서 v2/v3 선택 시 올바른 데이터를 조회하는지 확인
- `get_latest_scan_from_db` 함수가 `scanner_version` 파라미터를 올바르게 처리하는지 확인

**현재 코드** (`backend/main.py`):
```python
def get_latest_scan_from_db(scanner_version: Optional[str] = None, ...):
    # scanner_version에 따라 올바른 데이터 조회
    # 이미 구현되어 있음
```

**확인 필요**:
- 프론트엔드에서 `scanner_version` 파라미터를 올바르게 전달하는지 확인

---

## 구현 단계별 체크리스트

### Phase 1: API 수정 (1일)
- [ ] `/scan` API에 `scanner_version` 파라미터 추가
- [ ] `scanner_version` 파라미터 처리 로직 구현
- [ ] 하위 호환성 확인 (기존 코드 영향 없음)
- [ ] 단위 테스트 작성

### Phase 2: 스케줄러 수정 (1일)
- [ ] `run_scan()` 함수 수정 (v2, v3 모두 실행)
- [ ] 에러 처리 강화 (한 버전 실패해도 다른 버전 실행)
- [ ] 로깅 개선 (각 버전별 결과 로그)
- [ ] 알림 로직 수정 (v2, v3 중 더 많은 매칭 수 사용)

### Phase 3: 테스트 및 검증 (1일)
- [ ] 수동 테스트 (로컬 환경)
- [ ] 스케줄러 실행 테스트
- [ ] DB 저장 확인 (v2, v3 결과 분리 저장)
- [ ] 프론트엔드 연동 확인

### Phase 4: 배포 (1일)
- [ ] 스테이징 환경 배포
- [ ] 프로덕션 환경 배포
- [ ] 모니터링 (스케줄러 실행 로그 확인)

---

## 예상 문제점 및 해결 방안

### 문제 1: 스캔 실행 시간 증가
**문제**: v2와 v3를 모두 실행하면 스캔 시간이 2배로 증가

**해결 방안**:
- 병렬 실행 고려 (옵션 B)
- 스캔 시간 모니터링 및 최적화
- 필요 시 스캔 시간 분산 (v2: 15:42, v3: 15:43)

### 문제 2: 리소스 사용 증가
**문제**: v2와 v3를 모두 실행하면 CPU/메모리 사용량 증가

**해결 방안**:
- 리소스 모니터링
- 필요 시 서버 스펙 업그레이드
- 캐시 활용으로 중복 계산 최소화

### 문제 3: DB 저장 충돌
**문제**: v2와 v3 결과가 같은 날짜에 저장될 때 충돌 가능성

**해결 방안**:
- `scan_rank` 테이블의 `scanner_version` 컬럼으로 분리 저장 (이미 구현됨)
- 저장 로직 확인 및 테스트

### 문제 4: 알림 중복
**문제**: v2와 v3 각각 알림 발송 시 중복 알림

**해결 방안**:
- 알림은 한 번만 발송 (v2, v3 중 더 많은 매칭 수 사용)
- 또는 사용자별 설정에 따라 선택적 알림

---

## 성능 영향 분석

### 현재 (단일 스캔)
- 실행 시간: 약 2-3분
- CPU 사용률: 평균 50-70%
- 메모리 사용: 평균 2-3GB

### 변경 후 (이중 스캔)
- 실행 시간: 약 4-6분 (순차 실행) 또는 2-3분 (병렬 실행)
- CPU 사용률: 평균 70-90% (순차) 또는 80-100% (병렬)
- 메모리 사용: 평균 3-4GB

**권장**: 순차 실행으로 시작하고, 성능 문제 발생 시 병렬 실행 고려

---

## 롤백 계획

### 문제 발생 시
1. 스케줄러 코드를 이전 버전으로 롤백
2. `/scan` API는 하위 호환성 유지 (기존 동작 유지)
3. DB 데이터는 영향 없음 (v2, v3 결과 분리 저장)

---

## 모니터링 계획

### 로그 모니터링
- v2 스캔 실행 시간
- v3 스캔 실행 시간
- 각 버전별 매칭 수
- 에러 발생 여부

### 메트릭 수집
- 스캔 실행 성공률
- 평균 실행 시간
- 리소스 사용량

---

## 참고 사항

### 관련 파일
- `backend/scheduler.py`: 스케줄러 설정
- `backend/main.py`: `/scan` API 엔드포인트
- `backend/services/scan_service.py`: 스캔 결과 저장
- `backend/scanner_settings_manager.py`: 스캐너 설정 관리

### 관련 문서
- `docs/database/SCANNER_SETTINGS_TABLE.md`: 스캐너 설정 테이블
- `docs/scanner-v2/SCANNER_V2_USAGE.md`: V2 스캐너 사용법

---

**작성일**: 2026-01-08  
**최종 업데이트**: 2026-01-08  
**상태**: 계획 수립 완료, 구현 대기


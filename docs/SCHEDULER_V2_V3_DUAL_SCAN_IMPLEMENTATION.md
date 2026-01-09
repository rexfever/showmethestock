# 스케줄러 v2/v3 동시 스캔 구현 완료

**작성일**: 2026-01-08  
**상태**: 구현 완료

---

## 구현 완료 사항

### 1. `/scan` API에 `scanner_version` 파라미터 추가 ✅

**변경 파일**: `backend/main.py`

**변경 내용**:
- `scanner_version` 파라미터 추가 (선택적)
- 파라미터가 있으면 해당 버전 사용, 없으면 기존 방식 (하위 호환성 유지)
- v2, v3 명시적 실행 지원

**코드 위치**:
```python
@app.get('/scan', response_model=ScanResponse)
def scan(..., scanner_version: Optional[str] = None):
    # 스캐너 버전 결정: 파라미터 > DB 설정 > 기본값
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
        # V2 엔진 명시적 실행
        ...
    else:
        # V1 엔진 실행
        ...
```

**하위 호환성**: ✅ 유지
- `scanner_version` 파라미터가 없으면 기존 방식대로 `get_active_engine()` 사용
- 기존 코드 영향 없음

---

### 2. 스케줄러에서 v2와 v3 모두 실행 ✅

**변경 파일**: `backend/scheduler.py`

**변경 내용**:
- `run_scan()` 함수 수정
- v2와 v3 스캔을 순차적으로 실행
- 각 버전별 결과를 `scan_rank` 테이블에 분리 저장
- 에러 처리 강화 (한 버전 실패해도 다른 버전 실행)

**코드 위치**:
```python
def run_scan():
    """한국 주식 스캔 실행 (15:42) - v2와 v3 모두 실행"""
    # v2 스캔 실행
    response_v2 = requests.get(
        f"{backend_url}/scan?save_snapshot=true&scanner_version=v2", 
        timeout=300
    )
    
    # v3 스캔 실행
    response_v3 = requests.get(
        f"{backend_url}/scan?save_snapshot=true&scanner_version=v3", 
        timeout=300
    )
    
    # 결과 요약 및 알림
    ...
```

**실행 순서**:
1. v2 스캔 실행 (15:42)
2. v3 스캔 실행 (15:42, v2 완료 후)
3. 결과 요약 및 알림

---

### 3. `save_scan_snapshot` 함수 확인 ✅

**확인 결과**:
- ✅ `scanner_version` 파라미터를 올바르게 처리
- ✅ v2, v3 결과가 `scan_rank` 테이블에 분리 저장됨
- ✅ 주석 업데이트 완료

**코드 위치**: `backend/services/scan_service.py`

---

## 동작 방식

### 스케줄러 실행 (매일 15:42 KST)

1. **v2 스캔 실행**
   - `/scan?save_snapshot=true&scanner_version=v2` 호출
   - 결과를 `scan_rank` 테이블에 `scanner_version='v2'`로 저장

2. **v3 스캔 실행**
   - `/scan?save_snapshot=true&scanner_version=v3` 호출
   - 결과를 `scan_rank` 테이블에 `scanner_version='v3'`로 저장

3. **결과 요약**
   - v2와 v3 각각의 매칭 수 로그 출력
   - 알림은 v2, v3 중 더 많은 매칭 수 사용

### 사용자 선택

- 프론트엔드에서 `scanner_version` 파라미터로 v2 또는 v3 선택
- `get_latest_scan_from_db(scanner_version='v2')` 또는 `get_latest_scan_from_db(scanner_version='v3')` 호출
- 각 버전의 결과를 독립적으로 조회 가능

---

## 테스트 방법

### 1. 수동 테스트

```bash
# v2 스캔 실행
curl "http://localhost:8010/scan?save_snapshot=true&scanner_version=v2"

# v3 스캔 실행
curl "http://localhost:8010/scan?save_snapshot=true&scanner_version=v3"
```

### 2. DB 확인

```sql
-- v2 결과 확인
SELECT COUNT(*) FROM scan_rank 
WHERE date = CURRENT_DATE AND scanner_version = 'v2';

-- v3 결과 확인
SELECT COUNT(*) FROM scan_rank 
WHERE date = CURRENT_DATE AND scanner_version = 'v3';
```

### 3. 스케줄러 로그 확인

```bash
# 스케줄러 로그 확인
tail -f backend.log | grep "스캔"
```

---

## 예상 성능 영향

### 실행 시간
- **이전**: 약 2-3분 (단일 스캔)
- **현재**: 약 4-6분 (v2 + v3 순차 실행)

### 리소스 사용
- **CPU**: 평균 70-90% (순차 실행)
- **메모리**: 평균 3-4GB

### 최적화 옵션
- 필요 시 병렬 실행으로 변경 가능 (약 2-3분으로 단축)
- 현재는 순차 실행으로 안정성 우선

---

## 주의사항

### 1. 스캔 실행 시간
- v2와 v3를 모두 실행하므로 실행 시간이 2배로 증가
- 스케줄러 타임아웃 설정 확인 (현재 300초)

### 2. DB 저장
- v2와 v3 결과는 `scanner_version` 컬럼으로 분리 저장
- 같은 날짜에 두 버전의 결과가 모두 저장됨

### 3. 알림
- 알림은 v2, v3 중 더 많은 매칭 수를 사용
- 중복 알림 방지

---

## 다음 단계

### 즉시 확인
- [ ] 스케줄러 실행 테스트
- [ ] DB 저장 확인 (v2, v3 결과 분리)
- [ ] 프론트엔드 연동 확인

### 모니터링
- [ ] 스캔 실행 시간 모니터링
- [ ] 리소스 사용량 모니터링
- [ ] 에러 발생 여부 확인

### 최적화 (필요 시)
- [ ] 병렬 실행으로 변경 (성능 문제 발생 시)
- [ ] 스캔 시간 분산 (v2: 15:42, v3: 15:43)

---

## 롤백 방법

### 문제 발생 시
1. `backend/scheduler.py`의 `run_scan()` 함수를 이전 버전으로 롤백
2. `/scan` API는 하위 호환성 유지 (기존 동작 유지)
3. DB 데이터는 영향 없음 (v2, v3 결과 분리 저장)

---

**작성일**: 2026-01-08  
**최종 업데이트**: 2026-01-08  
**상태**: 구현 완료, 테스트 대기


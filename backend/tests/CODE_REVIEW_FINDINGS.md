# v3 추천 시스템 코드 리뷰 결과

## 발견된 문제 및 수정 사항

### 1. 상태 전이 서비스 - dict/tuple 처리 오류

**문제**: `transition_recommendation_status`에서 `from_status`와 `ticker` 추출 시 dict/tuple 처리 로직이 잘못됨

**위치**: `backend/services/state_transition_service.py:53-54`

**수정 전**:
```python
from_status = current[0] if isinstance(current, dict) else current[0]
ticker = current[1] if isinstance(current, dict) else current[1]
```

**수정 후**:
```python
if isinstance(current, dict):
    from_status = current.get('status')
    ticker = current.get('ticker')
else:
    from_status = current[0]
    ticker = current[1]
```

### 2. 쿨다운 로직 개선

**문제**: `can_create_recommendation`에서 `broken_date`와 `scan_date`가 같을 때 쿨다운 미경과로 처리해야 함

**위치**: `backend/services/recommendation_service.py:183-185`

**수정 전**:
```python
trading_days = get_trading_days_between(broken_date, scan_date)
if trading_days < cooldown_days:
    return False, f"BROKEN 후 쿨다운 기간 중입니다 ({trading_days}/{cooldown_days} 거래일 경과)"
```

**수정 후**:
```python
# broken_date와 scan_date가 같으면 쿨다운 미경과로 처리
if broken_date >= scan_date:
    return False, f"BROKEN 후 쿨다운 기간 중입니다 (BROKEN일: {broken_date}, 스캔일: {scan_date})"

trading_days = get_trading_days_between(broken_date, scan_date)
# broken_date 당일은 제외하고 다음 거래일부터 계산
if trading_days <= cooldown_days:
    return False, f"BROKEN 후 쿨다운 기간 중입니다 ({trading_days}/{cooldown_days} 거래일 경과)"
```

### 3. 기존 ACTIVE 추천 ID 추출 로직 개선

**문제**: `create_recommendation`에서 기존 ACTIVE 추천 ID 추출 시 dict/tuple 처리 개선

**위치**: `backend/services/recommendation_service.py:258`

**수정 전**:
```python
existing_id = existing_active[0] if isinstance(existing_active, dict) else existing_active[0]
```

**수정 후**:
```python
if isinstance(existing_active, dict):
    existing_id = existing_active.get('id')
else:
    existing_id = existing_active[0]
```

### 4. scan_run_id 기본값 처리

**문제**: `scan_run_id`가 None일 때 빈 문자열로 처리되면 UNIQUE 제약에서 문제 발생 가능

**위치**: `backend/services/recommendation_service.py:79`

**수정**: `scan_run_id`가 None이거나 빈 문자열일 때 자동 생성

**수정 후**:
```python
if not scan_run_id:
    scan_run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
```

### 5. DB 스키마 - scan_run_id 기본값

**문제**: `scan_results` 테이블의 `scan_run_id`가 NULL일 수 있어 UNIQUE 제약에서 문제 발생 가능

**위치**: `backend/migrations/20251215_create_recommendations_tables.sql:9`

**수정**: `scan_run_id`에 기본값 설정

**수정 후**:
```sql
scan_run_id        TEXT DEFAULT '',  -- 스캔 실행 ID (같은 날짜 여러 실행 구분)
```

## 테스트 코드 작성

### 1. 단위 테스트
- `test_recommendation_service.py`: 추천 서비스 단위 테스트
- `test_state_transition_service.py`: 상태 전이 서비스 단위 테스트

### 2. 통합 테스트
- `test_recommendations_integration.py`: 추천 생성 플로우 통합 테스트

## 검증 항목

### ✅ 완료된 검증
1. 상태 전이 유효성 검증 로직
2. 쿨다운 로직 정확성
3. ACTIVE 유일성 보장
4. dict/tuple 처리 일관성

### ⚠️ 추가 검증 필요
1. 실제 DB 연결 테스트 (통합 테스트 환경)
2. 동시성 테스트 (동일 ticker 동시 추천 생성)
3. 트랜잭션 롤백 테스트
4. 성능 테스트 (대량 데이터 처리)

## 권장 사항

1. **에러 처리 강화**: 모든 DB 쿼리에 대한 예외 처리 추가
2. **로깅 개선**: 중요한 상태 변경 시 상세 로그 기록
3. **모니터링**: recommendations 테이블의 ACTIVE 중복 모니터링
4. **백업**: 상태 변경 이벤트 로그를 통한 감사 추적



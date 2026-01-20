# TTL 전이 문제 분석 리포트

**작성일**: 2026-01-03  
**문제**: TTL 만료일 이후에도 ACTIVE로 유지되는 문제

---

## 문제 발견

### 현상
- TTL_EXPIRED 케이스 2개가 TTL 만료일 이후에도 ACTIVE로 유지됨
- TTL 만료일: 2025-12-24, 2025-12-26
- 실제 ARCHIVED: 2026-01-05 (10일, 12일 지연)
- `broken_at`: None (BROKEN을 거치지 않음)

### 원인 분석

#### 1. `evaluate_active_recommendations` 미실행 가능성
- **스케줄러**: 매일 15:45 KST에 실행되어야 함
- **실제**: 2025-12-26 ~ 2026-01-05 사이에 실행되지 않았을 가능성
- **결과**: TTL 만료일이 지났는데도 ACTIVE 상태 유지

#### 2. `create_recommendation`에서 직접 ARCHIVED로 전환
- **경로**: `create_recommendation` → ACTIVE → ARCHIVED (직접 전환)
- **시점**: 2026-01-05에 스캔 실행 시 TTL을 체크하여 ARCHIVED로 전환
- **문제**: TTL 만료 시점의 수익률이 아니라 **현재 시점의 수익률**을 사용

---

## 코드 문제점

### 1. `create_recommendation` 함수

**파일**: `backend/services/recommendation_service.py`  
**위치**: line 278-331

**문제**:
```python
# TTL 체크: 전략별 TTL 이상이면 TTL_EXPIRED로 설정
if trading_days >= ttl_days:
    archive_reason = 'TTL_EXPIRED'
else:
    archive_reason = 'REPLACED'

# 현재 가격 조회 (❌ 문제: TTL_EXPIRED인데도 현재 시점 가격 사용)
df_today = api.get_ohlcv(ticker, 1, today_str)
current_price = float(df_today.iloc[-1]['close'])
current_return = ((current_price - anchor_close) / anchor_close) * 100
archive_return_pct = current_return  # ❌ TTL 만료 시점이 아님
```

**수정 완료**: TTL_EXPIRED인 경우 TTL 만료 시점의 가격을 조회하도록 수정

### 2. `evaluate_active_recommendations` 함수

**파일**: `backend/services/state_transition_service.py`  
**위치**: line 525-561

**현재 로직**:
- TTL 만료일이 지나면 BROKEN으로 전환
- 하지만 실제로는 전환이 안 되었음

**가능한 원인**:
1. 스케줄러가 실행되지 않음
2. 함수 실행 중 오류 발생
3. 전환 로직에서 예외 발생

---

## 수정 내용

### 1. `create_recommendation` 함수 수정

**변경 사항**:
- TTL_EXPIRED인 경우 TTL 만료 시점의 가격을 조회
- TTL 만료 시점의 수익률을 `archive_return_pct`로 저장

**코드 위치**: `backend/services/recommendation_service.py` (line 286-331)

### 2. `state_transition_service` 함수 수정

**변경 사항**:
- TTL_EXPIRED로 전환 시 TTL 만료 시점의 수익률 조회
- TTL 만료 시점의 수익률을 `broken_return_pct`로 저장

**코드 위치**: `backend/services/state_transition_service.py` (line 530-554)

---

## 근본 원인

### TTL 만료일 이후에도 ACTIVE로 유지되는 이유

1. **스케줄러 미실행**
   - `evaluate_active_recommendations`가 매일 실행되어야 하는데 실행되지 않음
   - 2025-12-26 ~ 2026-01-05 사이에 실행 이력 없음

2. **대체 경로 사용**
   - `create_recommendation`에서 TTL을 체크하여 직접 ARCHIVED로 전환
   - 이 경로는 정상 작동하지만, TTL 만료 시점의 수익률을 사용하지 않았음

3. **전환 지연**
   - TTL 만료일이 지나도 스캔이 실행될 때까지 ACTIVE 상태 유지
   - 스캔 실행 시에야 ARCHIVED로 전환됨

---

## 해결 방안

### 1. 즉시 조치 (완료)

- ✅ `create_recommendation`: TTL_EXPIRED인 경우 TTL 만료 시점 수익률 사용하도록 수정
- ✅ `state_transition_service`: TTL_EXPIRED로 전환 시 TTL 만료 시점 수익률 사용하도록 수정
- ✅ 기존 데이터 점검: 이미 정확함 (수정 불필요)

### 2. 모니터링 강화 (권장)

1. **스케줄러 실행 확인**
   - `evaluate_active_recommendations` 실행 로그 확인
   - 실행 실패 시 알림 추가

2. **TTL 만료 항목 감지**
   - TTL 만료일이 지났는데도 ACTIVE인 항목 자동 감지
   - 알림 또는 자동 전환 로직 추가

3. **전환 실패 감지**
   - BROKEN 전환 시도 후 실패하는 경우 로깅 및 알림

### 3. 코드 개선 (권장)

1. **전환 보장 메커니즘**
   - TTL 만료일이 지난 항목은 즉시 BROKEN으로 전환
   - 재시도 로직 추가

2. **이중 체크**
   - `evaluate_active_recommendations`와 `create_recommendation` 모두에서 TTL 체크
   - 어느 경로에서든 TTL 만료 시점 수익률 사용 보장

---

## 결론

### 문제 요약
1. **TTL 만료일 이후 ACTIVE 유지**: 스케줄러 미실행 또는 전환 실패
2. **TTL 만료 시점 수익률 미사용**: `create_recommendation`에서 현재 시점 수익률 사용

### 수정 완료
- ✅ `create_recommendation`: TTL 만료 시점 수익률 사용하도록 수정
- ✅ `state_transition_service`: TTL 만료 시점 수익률 사용하도록 수정

### 추가 조치 필요
- ⚠️ 스케줄러 실행 이력 확인
- ⚠️ TTL 만료 항목 모니터링 추가
- ⚠️ 전환 실패 감지 로직 추가

---

**작성자**: AI Assistant  
**상태**: 코드 수정 완료, 모니터링 강화 권장


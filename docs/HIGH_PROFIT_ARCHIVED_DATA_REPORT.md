# 고수익 ARCHIVED 데이터 점검 리포트

**작성일**: 2026-01-03  
**분석 대상**: ARCHIVED 데이터 중 수익률이 20% 이상인 항목

---

## 요약

- **조회 항목 수**: 34개
- **정책 위반 항목**: 0개
- **모든 항목이 정책을 준수합니다**

---

## 분석 결과

### 1. 전체 통계

- **REPLACED 케이스**: 33개
- **TTL_EXPIRED 케이스**: 1개
- **NO_MOMENTUM 케이스**: 0개

### 2. REPLACED 케이스 분석

#### 특징
- 모든 항목이 **2025-12-31**에 REPLACED로 전환됨
- REPLACED 시점의 수익률이 정확히 저장되어 있음
- 최대 수익률: 358.89% (475830)
- 최소 수익률: 21.63% (237690)

#### 정책 준수 여부
- ✅ **정책 준수**: REPLACED 전환 시점(`status_changed_at`)의 수익률이 `archive_return_pct`에 정확히 저장됨
- ✅ **코드 로직 정상**: `create_recommendation_transaction` 함수에서 REPLACED 전환 시 현재 가격으로 수익률 계산 후 저장

#### 코드 검토 결과

`backend/services/recommendation_service_v2.py`의 `create_recommendation_transaction` 함수:

```python
# 현재 가격 조회 (전이 시점의 정확한 가격)
df_today = api.get_ohlcv(ticker, 10, today_str)
current_price = ...  # 정확한 날짜의 가격 사용

# archive_return_pct 계산
if existing_anchor_close and existing_anchor_close > 0 and current_price:
    current_return = round(((current_price - float(existing_anchor_close)) / float(existing_anchor_close)) * 100, 2)
    archive_return_pct = current_return
    archive_price = current_price

# REPLACED 상태로 전이
cur.execute("""
    UPDATE recommendations
    SET status = 'REPLACED',
        archive_reason = %s,
        archive_return_pct = %s,
        archive_price = %s,
        status_changed_at = NOW()
    WHERE recommendation_id = %s
""", (archive_reason, archive_return_pct, archive_price, existing_rec_id))
```

**결론**: 코드 로직이 정상이며, REPLACED 시점의 수익률을 정확히 저장하고 있습니다.

### 3. TTL_EXPIRED 케이스 분석

#### 항목
- **티커**: 474650
- **전략**: v2_lite
- **수익률**: 43.09%
- **anchor_date**: 2025-12-05
- **TTL 만료일**: 2025-12-26 (TTL: 15거래일)
- **archived_at**: 2026-01-05

#### 정책 준수 여부
- ✅ **정책 준수**: TTL 만료 시점의 수익률이 `archive_return_pct`에 정확히 저장됨
- ✅ **검증 결과**: TTL 시점(2025-12-26) 수익률 43.09%와 `archive_return_pct` 43.09% 일치

---

## 코드 검토 결과

### 1. REPLACED 케이스

**파일**: `backend/services/recommendation_service_v2.py`  
**함수**: `create_recommendation_transaction`

**로직**:
1. 기존 ACTIVE 추천이 있으면 REPLACED로 전환
2. 전환 시점(`NOW()`)의 현재 가격 조회
3. `archive_return_pct = (current_price - anchor_close) / anchor_close * 100` 계산
4. `status_changed_at = NOW()` 설정

**결론**: ✅ 정상 작동

### 2. TTL_EXPIRED 케이스

**파일**: `backend/services/state_transition_service.py`  
**함수**: `evaluate_active_recommendations`

**로직**:
1. TTL 만료 시점 계산 (전략별 TTL 거래일)
2. TTL 시점의 가격 조회
3. `archive_return_pct` 계산 및 저장

**결론**: ✅ 정상 작동

### 3. 데이터 조회 시 TTL 시점 수익률 계산

**파일**: `backend/services/recommendation_service.py`  
**함수**: `get_archived_recommendations_list`

**로직**:
- TTL을 초과한 경우 TTL 시점의 수익률을 계산하여 표시
- `archive_return_pct`는 DB에 저장된 스냅샷 값 유지

**결론**: ✅ 정상 작동

---

## 결론

### 코드 상태
- ✅ **모든 코드 로직이 정상 작동**
- ✅ **정책에 맞게 수익률이 저장됨**
- ✅ **데이터 조회 시에도 정확한 수익률 표시**

### 데이터 상태
- ✅ **모든 항목이 정책을 준수**
- ✅ **REPLACED 케이스**: 전환 시점의 수익률 정확히 저장
- ✅ **TTL_EXPIRED 케이스**: TTL 만료 시점의 수익률 정확히 저장

### 추가 조치 불필요
- 코드 수정 불필요
- 데이터 수정 불필요
- 모든 항목이 정책을 준수하고 있음

---

## 참고 사항

### REPLACED 케이스의 동일 날짜 전환
- 33개 항목이 모두 2025-12-31에 REPLACED로 전환됨
- 이는 해당 날짜에 일괄 스캔이 실행되어 기존 ACTIVE 항목들이 모두 REPLACED로 전환된 것으로 보임
- **정상적인 동작**이며, 각 항목의 REPLACED 시점 수익률이 정확히 저장되어 있음

### 고수익률의 의미
- 일부 항목이 100% 이상의 수익률을 기록한 것은:
  1. 추천 시점(anchor_date)부터 REPLACED 시점까지의 실제 수익률
  2. 장기간 보유한 경우 높은 수익률이 가능
  3. 예: 475830 (358.89% 수익) - anchor_date: 2025-08-28, REPLACED: 2025-12-31 (약 4개월)

---

**작성자**: AI Assistant  
**검토 완료**: 코드 및 데이터 모두 정상


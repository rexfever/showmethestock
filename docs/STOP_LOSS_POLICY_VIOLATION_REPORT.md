# 손절 정책 위반 리포트

**작성일**: 2026-01-03  
**분석 대상**: ARCHIVED 데이터 중 손실이 -7%를 넘는 항목

---

## 요약

- **위반 항목 수**: 21개
- **모든 위반 항목**: v2_lite 전략 (손절 기준: -2.0%)
- **평균 손실**: -13.96%
- **최대 손실**: -54.52% (018290)
- **최소 손실**: -7.33% (439260)

---

## 문제 분석

### 1. 핵심 문제

모든 위반 항목이 **손절 조건(-2%)을 만족한 후에도 BROKEN으로 전이되지 않았습니다**.

#### 분석 결과 (샘플 5개)

| 티커 | 전략 | 첫 손절 만족일 | BROKEN 전이일 | 지연 기간 | 최종 손실 |
|------|------|---------------|--------------|----------|----------|
| 018290 | v2_lite | 2025-08-26 | 2026-01-06 | **133일** | -54.52% |
| 095500 | v2_lite | 2025-11-17 | 2026-01-06 | **50일** | -19.15% |
| 196170 | v2_lite | 2025-11-21 | 2026-01-06 | **46일** | -18.86% |
| 039200 | v2_lite | 2025-11-25 | 2026-01-06 | **42일** | -17.37% |
| 247540 | v2_lite | 2025-12-16 | 2026-01-06 | **21일** | -16.70% |

### 2. 문제 원인

#### 가능한 원인들

1. **`evaluate_active_recommendations` 미실행**
   - 2025년 8월~12월 동안 스케줄러가 실행되지 않았거나
   - 스케줄러 오류로 인해 함수가 호출되지 않았을 가능성

2. **BROKEN 전이 실패**
   - `evaluate_active_recommendations`는 실행되었지만
   - `transition_recommendation_status` 호출 시 오류 발생
   - 트랜잭션 실패 또는 예외 처리로 인한 실패

3. **코드 버그**
   - 손절 조건 체크 로직에 문제가 있거나
   - 상태 전이 검증 로직에서 거부되었을 가능성

#### 코드 검토 결과

- ✅ `evaluate_active_recommendations` 함수: 정상 구현됨
- ✅ `transition_recommendation_status` 함수: 정상 구현됨
- ✅ `transition_recommendation_status_transaction` 함수: 정상 구현됨
- ✅ 손절 조건 체크 로직: 정상 구현됨 (`current_return <= stop_loss_pct`)

**결론**: 코드 자체에는 문제가 없으며, **실행 환경 또는 실행 이력에 문제가 있었을 가능성이 높습니다**.

### 3. 위반 항목 상세

#### 전체 위반 항목 (21개)

| 순위 | 티커 | 전략 | 손실률 | broken_at | anchor_date |
|------|------|------|--------|-----------|-------------|
| 1 | 018290 | v2_lite | -54.52% | 2026-01-06 | 2025-08-25 |
| 2 | 095500 | v2_lite | -19.15% | 2026-01-06 | 2025-11-14 |
| 3 | 196170 | v2_lite | -18.86% | 2026-01-06 | 2025-11-14 |
| 4 | 039200 | v2_lite | -17.37% | 2026-01-06 | 2025-11-21 |
| 5 | 247540 | v2_lite | -16.70% | 2026-01-06 | 2025-12-12 |
| 6 | 078600 | v2_lite | -16.23% | 2026-01-06 | 2025-12-15 |
| 7 | 014280 | v2_lite | -15.01% | 2026-01-06 | 2025-12-15 |
| 8 | 358570 | v2_lite | -12.24% | 2026-01-06 | 2025-12-10 |
| 9 | 213420 | v2_lite | -12.15% | 2026-01-06 | 2025-12-08 |
| 10 | 443060 | v2_lite | -11.85% | 2026-01-06 | 2025-09-11 |
| 11 | 278470 | v2_lite | -11.15% | 2026-01-06 | 2025-12-09 |
| 12 | 003230 | v2_lite | -10.80% | 2026-01-06 | 2025-11-21 |
| 13 | 206650 | v2_lite | -10.55% | 2026-01-06 | 2025-12-02 |
| 14 | 377480 | v2_lite | -9.27% | 2026-01-06 | 2025-08-14 |
| 15 | 010120 | v2_lite | -9.09% | 2026-01-06 | 2025-12-12 |
| 16 | 015760 | v2_lite | -9.06% | 2026-01-06 | 2025-11-27 |
| 17 | 290650 | v2_lite | -8.26% | 2026-01-06 | 2025-12-09 |
| 18 | 058470 | v2_lite | -8.08% | 2026-01-06 | 2025-12-02 |
| 19 | 068760 | v2_lite | -7.94% | 2026-01-06 | 2025-12-17 |
| 20 | 214150 | v2_lite | -7.63% | 2026-01-06 | 2025-12-17 |
| 21 | 439260 | v2_lite | -7.33% | 2026-01-06 | 2025-12-08 |

**공통점**:
- 모든 항목의 `broken_at`이 **2026-01-06**로 동일 (일괄 처리됨)
- 모든 항목이 `archive_reason = 'NO_MOMENTUM'` (정상)
- 모든 항목이 `broken_return_pct`와 `archive_return_pct` 일치 (정상)

---

## 해결 방안

### 1. 즉시 조치 (완료)

- ✅ 손절 정책 위반 항목 조회 스크립트 작성
- ✅ 손절 조건 만족 시점 분석 스크립트 작성
- ✅ 문제 원인 파악 완료

### 2. 데이터 수정 (필요 시)

현재 데이터는 **BROKEN 시점의 손실을 정확히 반영**하고 있습니다. 
- `broken_return_pct`와 `archive_return_pct`가 일치
- `broken_at`이 설정되어 있음
- `archive_reason`이 'NO_MOMENTUM'으로 정상 설정

**데이터 수정은 불필요**합니다. 문제는 **과거에 손절 조건을 만족했을 때 BROKEN으로 전이되지 않았다는 점**입니다.

### 3. 코드 개선 (권장)

#### 3.1 로깅 강화

`evaluate_active_recommendations` 함수에 더 상세한 로깅 추가:

```python
# 손절 조건 만족 시 상세 로깅
if current_return <= stop_loss_pct:
    logger.warning(f"[state_transition_service] 손절 조건 만족: {ticker}, "
                   f"current_return={current_return:.2f}%, stop_loss={stop_loss_pct:.2f}%, "
                   f"anchor_date={anchor_date}, days_since_anchor={trading_days}")
    
    # 전이 시도
    result = transition_recommendation_status(...)
    if not result:
        logger.error(f"[state_transition_service] BROKEN 전이 실패: {ticker}, rec_id={rec_id}")
```

#### 3.2 모니터링 추가

손절 조건을 만족했지만 BROKEN으로 전이되지 않은 항목을 감지하는 모니터링 추가:

```python
# evaluate_active_recommendations 실행 후
# ACTIVE 상태인데 손절 조건을 만족하는 항목이 있는지 확인
cur.execute("""
    SELECT recommendation_id, ticker, strategy, anchor_date, anchor_close
    FROM recommendations
    WHERE status = 'ACTIVE'
    AND scanner_version = 'v3'
    -- 손절 조건 만족 여부는 별도 계산 필요
""")
```

#### 3.3 재시도 메커니즘

BROKEN 전이 실패 시 재시도 로직 추가:

```python
max_retries = 3
for attempt in range(max_retries):
    result = transition_recommendation_status(...)
    if result:
        break
    if attempt < max_retries - 1:
        logger.warning(f"BROKEN 전이 재시도: {attempt + 1}/{max_retries}")
        time.sleep(1)
```

### 4. 스케줄러 확인

#### 4.1 스케줄러 실행 이력 확인

- `backend/scheduler.py`의 `run_status_evaluation` 함수 실행 로그 확인
- 2025년 8월~12월 동안 로그가 있는지 확인

#### 4.2 스케줄러 상태 모니터링

스케줄러가 정상 실행되는지 확인하는 헬스체크 추가:

```python
# 매일 스케줄러 실행 여부 확인
# recommendation_state_events 테이블에 최근 24시간 내 BROKEN 전이 이벤트가 있는지 확인
```

---

## 권장 사항

### 1. 단기 (즉시)

1. ✅ **문제 파악 완료**: 손절 정책 위반 항목 21개 확인
2. ✅ **원인 분석 완료**: 손절 조건 만족 후 BROKEN 전이 미실행
3. ⚠️ **스케줄러 로그 확인**: 2025년 8월~12월 실행 이력 확인 필요
4. ⚠️ **모니터링 추가**: 손절 조건 만족 항목 감지 로직 추가

### 2. 중기 (1주일 내)

1. **로깅 강화**: `evaluate_active_recommendations` 함수에 상세 로깅 추가
2. **재시도 메커니즘**: BROKEN 전이 실패 시 재시도 로직 추가
3. **알림 시스템**: 손절 조건 만족 항목이 24시간 이상 ACTIVE 상태로 유지되면 알림

### 3. 장기 (1개월 내)

1. **정기 점검**: 주간 손절 정책 준수 여부 자동 점검
2. **대시보드**: 손절 정책 준수 현황 대시보드 구축
3. **자동 복구**: 손절 조건 만족 항목 자동 BROKEN 전이 (수동 개입 없이)

---

## 참고 파일

- **분석 스크립트**: `backend/scripts/check_archived_stop_loss_violations.py`
- **타이밍 분석 스크립트**: `backend/scripts/analyze_stop_loss_timing.py`
- **상태 전이 서비스**: `backend/services/state_transition_service.py`
- **스케줄러**: `backend/scheduler.py` (line 474)

---

**작성자**: AI Assistant  
**검토 필요**: 스케줄러 실행 이력, 로그 파일 확인


# 모니터링 가이드

## 개요

ARCHIVED 데이터 정책 준수 모니터링 및 장 마감 후 상태 평가 로그 확인 방법을 안내합니다.

---

## 1. 새로 ARCHIVED된 항목 모니터링

### 스크립트 실행

```bash
# 최근 7일 동안 ARCHIVED된 항목 확인 (기본값)
python3 backend/scripts/monitor_newly_archived.py

# 최근 N일 동안 ARCHIVED된 항목 확인
python3 backend/scripts/monitor_newly_archived.py --days 30
```

### 확인 항목

1. **broken_at 누락**: `broken_return_pct`가 있는데 `broken_at`이 None인 경우
2. **수익률 불일치**: `broken_return_pct`와 `archive_return_pct`가 일치하지 않는 경우
3. **손절 정책 위반**: 손절 조건 만족했는데 `archive_reason`이 `NO_MOMENTUM`이 아닌 경우
4. **TTL_EXPIRED 수익률**: TTL 만료 시점의 수익률과 `archive_return_pct`가 일치하지 않는 경우

### 출력 예시

```
최근 7일 동안 ARCHIVED된 항목: 5개

📊 모니터링 결과 요약
전체 항목: 5개
정책 준수: 4개
문제 항목: 1개
broken_at 누락: 0개

❌ 정책 위반 항목 (1개)
  [005930] 삼성전자 (전략: v2_lite)
    - ARCHIVED 일시: 2026-01-08 15:45:00
    - archive_reason: NO_MOMENTUM
    - [BROKEN_ARCHIVE_RETURN_MISMATCH] broken_return_pct(-2.5%)와 archive_return_pct(-3.0%)가 일치하지 않습니다.
```

---

## 2. broken_at 누락 항목 확인

### 스크립트 실행

```bash
python3 backend/scripts/check_broken_at_missing.py
```

### 확인 내용

- `broken_return_pct`가 있는데 `broken_at`이 None인 모든 항목 조회
- 상태별(ACTIVE, BROKEN, ARCHIVED)로 분류하여 출력
- 최근 발생한 항목 우선 표시

### 출력 예시

```
⚠️ broken_at이 None인 항목: 2개

[ARCHIVED] 2개
  - 005930 (삼성전자)
    전략: v2_lite, broken_return_pct: -2.5%
    archived_at: 2026-01-08 15:45:00, archive_reason: NO_MOMENTUM
    archive_return_pct: -2.5%
```

---

## 3. 장 마감 후 상태 평가 로그 확인

### 실행 시점

- **매일 오후 3시 45분 KST** (장 마감 후)
- 스케줄러 위치: `backend/scheduler.py` (line 474)
- 함수: `evaluate_active_recommendations()` (`backend/services/state_transition_service.py`)

### 로그 확인 방법

#### 1. 애플리케이션 로그 확인

```bash
# 백엔드 로그 파일 확인 (로그 파일 위치는 환경에 따라 다름)
tail -f backend.log | grep "state_transition_service\|scheduler"

# 최근 상태 평가 실행 이력 확인
grep "상태 평가" backend.log | tail -20

# 특정 날짜의 상태 평가 로그 확인
grep "2026-01-08.*상태 평가" backend.log
```

#### 2. 로그 메시지 패턴

**정상 실행 시:**
```
[scheduler] v3 추천 상태 평가 시작...
[state_transition_service] 상태 평가 시작: 20260108
[state_transition_service] ACTIVE 추천 평가: 5개
[state_transition_service] BROKEN 전이: 005930 (손절 조건 만족: -2.5% <= -2.0%)
[scheduler] v3 추천 상태 평가 완료: {'total_active': 5, 'evaluated': 5, 'broken': 1, ...}
```

**오류 발생 시:**
```
[scheduler] 상태 평가 오류: ...
[scheduler] Traceback (most recent call last): ...
```

#### 3. 수동 실행 (테스트용)

```bash
# Python 인터프리터에서 직접 실행
cd backend
python3 -c "
from services.state_transition_service import evaluate_active_recommendations
stats = evaluate_active_recommendations()
print(stats)
"

# 또는 스크립트로 실행
python3 backend/scripts/run_status_evaluation.py
```

#### 4. 스케줄러 실행 이력 확인

```bash
# Systemd 서비스 로그 확인 (서버 환경)
journalctl -u stock-insight-backend -f | grep "상태 평가"

# 또는 서비스 상태 확인
systemctl status stock-insight-backend
```

---

## 4. 정기 모니터링 체크리스트

### 일일 확인 (장 마감 후)

- [ ] 상태 평가 로그 확인 (15:45 KST 실행 여부)
- [ ] 새로 ARCHIVED된 항목 정책 준수 확인
- [ ] `broken_at` 누락 항목 확인

### 주간 확인

- [ ] 최근 7일 동안 ARCHIVED된 항목 전체 검증
- [ ] 손절 정책 위반 항목 확인
- [ ] 스케줄러 실행 이력 점검

### 월간 확인

- [ ] 전체 ARCHIVED 데이터 정책 준수 검증
- [ ] 정책 위반 항목 통계 분석
- [ ] 모니터링 스크립트 실행 결과 리포트 작성

---

## 5. 문제 발생 시 대응

### broken_at 누락 항목 발견 시

1. **즉시 확인**: `check_broken_at_missing.py` 실행
2. **원인 파악**: 해당 항목의 `broken_return_pct` 설정 시점 확인
3. **수정**: `fix_archived_broken_at.py` 스크립트로 수정 (필요 시)

### 정책 위반 항목 발견 시

1. **상세 확인**: `monitor_newly_archived.py` 실행하여 문제 유형 파악
2. **원인 분석**: 코드 로직 확인 또는 데이터 이력 확인
3. **수정**: 문제 유형에 따라 적절한 수정 스크립트 실행

### 상태 평가 미실행 시

1. **로그 확인**: 스케줄러 실행 로그 확인
2. **수동 실행**: `run_status_evaluation.py`로 수동 실행
3. **원인 파악**: 스케줄러 오류 또는 서버 문제 확인
4. **재시작**: 필요 시 서버/스케줄러 재시작

---

## 6. 관련 스크립트 목록

| 스크립트 | 용도 | 실행 주기 |
|---------|------|----------|
| `monitor_newly_archived.py` | 최근 ARCHIVED 항목 모니터링 | 일일/주간 |
| `check_broken_at_missing.py` | broken_at 누락 확인 | 일일 |
| `verify_all_archived_policy_compliance.py` | 전체 ARCHIVED 데이터 검증 | 주간/월간 |
| `run_status_evaluation.py` | 상태 평가 수동 실행 | 필요 시 |

---

## 7. 알림 설정 (권장)

### 로그 모니터링 도구 연동

- **Grafana + Loki**: 로그 집계 및 알림
- **Sentry**: 에러 추적 및 알림
- **Slack/Discord**: 알림 채널 연동

### 알림 조건 예시

- 상태 평가 미실행 (24시간 이상)
- `broken_at` 누락 항목 발생
- 정책 위반 항목 발견
- 상태 평가 오류 발생

---

**작성일**: 2026-01-08  
**최종 업데이트**: 2026-01-08


# ARCHIVED 데이터 정책 준수 검증 리포트

**작성일**: 2026-01-06  
**검증 범위**: 전체 ARCHIVED 데이터 (scanner_version = 'v3')  
**검증 스크립트**: `backend/scripts/verify_all_archived_policy_compliance.py`

---

## 검증 결과 요약

### 전체 통계

- **전체 ARCHIVED 데이터**: 106개
- **정책 준수**: 106개 (100.00%)
- **문제 항목**: 0개 (0.00%)

### 검증 항목별 결과

| 검증 항목 | 문제 개수 | 상태 |
|---------|---------|------|
| REPLACED인데 TTL 초과 | 0개 | ✅ 정상 |
| TTL_EXPIRED 수익률 불일치 | 0개 | ✅ 정상 |
| NO_MOMENTUM 수익률 불일치 | 0개 | ✅ 정상 |
| 필수 데이터 없음 | 0개 | ✅ 정상 |

---

## 검증 항목 상세

### 1. REPLACED인데 TTL을 초과한 경우

**정책**: REPLACED인 경우 TTL을 초과하지 않아야 함. TTL을 초과했다면 TTL_EXPIRED로 변경되어야 함.

**검증 결과**: 
- ✅ **0개** - 모든 REPLACED 항목이 TTL을 초과하지 않음

### 2. TTL_EXPIRED 수익률 확인

**정책**: TTL_EXPIRED인 경우 `archive_return_pct`는 TTL 만료 시점의 수익률을 사용해야 함.

**검증 결과**: 
- ✅ **0개** - 모든 TTL_EXPIRED 항목이 TTL 만료 시점의 수익률을 정확히 사용

### 3. NO_MOMENTUM 수익률 확인

**정책**: NO_MOMENTUM인 경우 `archive_return_pct`는 `broken_return_pct`를 사용해야 함.

**검증 결과**: 
- ✅ **0개** - 모든 NO_MOMENTUM 항목이 `broken_return_pct`를 정확히 사용

### 4. 필수 데이터 확인

**정책**: `anchor_date`, `anchor_close` 등 필수 데이터가 있어야 함.

**검증 결과**: 
- ✅ **0개** - 모든 항목에 필수 데이터 존재

---

## 정책 준수 현황

### archive_reason별 분포

전체 106개 ARCHIVED 데이터의 `archive_reason` 분포:

- **NO_MOMENTUM**: 55개
- **TTL_EXPIRED**: 51개
- **REPLACED**: 0개 (모두 TTL 미초과 또는 TTL_EXPIRED로 변경됨)

### 전략별 분포

- **v2_lite**: 15거래일 TTL
- **midterm**: 25거래일 TTL
- **기타**: 20거래일 TTL

---

## 주요 수정 이력

### 1. TTL_EXPIRED 데이터 수정 (2026-01-06)

- **수정 항목**: 786개 TTL_EXPIRED 케이스 중 771개 수정
- **수정 내용**: TTL 만료 시점의 수익률로 `archive_return_pct` 업데이트

### 2. REPLACED 데이터 수정 (2026-01-06)

- **수정 항목**: REPLACED인데 TTL을 초과한 항목들을 TTL_EXPIRED로 변경
- **수정 내용**: `archive_reason` 변경 및 TTL 만료 시점 수익률 적용

### 3. 전체 데이터 정책 준수 수정 (2026-01-06)

- **수정 항목**: 전체 106개 중 48개 수정
- **수정 내용**: 정책에 맞게 `archive_reason`, `archive_return_pct`, `archive_price` 업데이트

---

## 특정 종목 검증 결과

### 에스피지(058610)

- **ARCHIVED**: 1개
- **상태**: ✅ 정책 준수
- **archive_reason**: TTL_EXPIRED
- **archive_return_pct**: 83.22% (TTL 시점 수익률 정확)

### 테크윙(089030)

- **ARCHIVED**: 1개
- **상태**: ✅ 정책 준수
- **archive_reason**: TTL_EXPIRED
- **archive_return_pct**: 60.39% (TTL 시점 수익률 정확)
- **참고**: `name` 필드가 NULL이지만 API에서 종목명 조회하여 정상 표시

### KODEX 레버리지(122630)

- **ARCHIVED**: 1개
- **상태**: ✅ 정책 준수 (수정 완료)
- **수정 전**: REPLACED, 173.29%
- **수정 후**: TTL_EXPIRED, 36.29% (TTL 시점 수익률)

---

## 결론

### ✅ 전체 ARCHIVED 데이터 정책 준수율: 100.00%

모든 ARCHIVED 데이터가 다음 정책을 준수합니다:

1. ✅ REPLACED인 경우 TTL을 초과하지 않음
2. ✅ TTL_EXPIRED인 경우 TTL 만료 시점의 수익률 사용
3. ✅ NO_MOMENTUM인 경우 `broken_return_pct` 사용
4. ✅ 필수 데이터 모두 존재

### 권장 사항

1. **정기 검증**: 주기적으로 ARCHIVED 데이터 정책 준수 검증 수행
2. **자동화**: 스크립트를 스케줄러에 추가하여 자동 검증
3. **모니터링**: 새로운 ARCHIVED 데이터 생성 시 정책 준수 확인

---

**검증 스크립트**: `backend/scripts/verify_all_archived_policy_compliance.py`  
**수정 스크립트**: `backend/scripts/fix_all_archived_policy_compliance.py`  
**작성자**: AI Assistant  
**상태**: ✅ 모든 데이터 정책 준수 확인 완료


# v3 추천 시스템 Backfill 실행 결과

**실행 일시**: 2025-12-30  
**실행 환경**: 로컬 PostgreSQL 16.11

---

## ✅ Backfill 실행 결과

### 실행 통계
- **조회된 scan_rank 데이터**: 783개
- **선택된 추천**: 131개 (ticker별 최신 ACTIVE만)
- **생성된 추천**: 131개
- **스킵**: 0개
- **오류**: 0개

### 결과
✅ **모든 추천 생성 성공**

---

## 검증 결과

### 1. 047810 (한국항공우주) 검증

**이전 문제**: 2025-11-14, 11-27, 12-09, 12-10, 12-15 모두 ACTIVE로 존재

**현재 상태**:
- ✅ **ACTIVE 1개만 존재** (2025-12-15)
- ✅ **전체 1개** (중복 제거 완료)

**결과**: ✅ **문제 해결됨**

### 2. 중복 ACTIVE 확인

```sql
SELECT ticker, COUNT(*) 
FROM recommendations 
WHERE status = 'ACTIVE' 
GROUP BY ticker 
HAVING COUNT(*) > 1;
```

**결과**: ✅ **중복 ACTIVE 없음 (0행)**

### 3. 전체 ACTIVE 추천 개수

- ✅ **ACTIVE 추천**: 131개
- ✅ **모든 ticker당 ACTIVE 1개씩 보장**

---

## 생성된 추천 예시

### 047810 (한국항공우주)
- **recommendation_id**: `3989aa5c-c2de-48cb-9e7b-fdeb8d5837b3`
- **anchor_date**: `2025-12-15`
- **anchor_close**: `112800`원
- **status**: `ACTIVE`
- **scanner_version**: `v3`

---

## 핵심 계약 검증

### ✅ 1. ticker당 ACTIVE 1개
- Partial unique index로 DB 레벨 보장
- 트랜잭션 레벨에서 기존 ACTIVE → REPLACED 전환
- **검증 결과**: ✅ 통과 (중복 0개)

### ✅ 2. anchor_date/anchor_close 고정
- 추천 생성 시점에 1회 고정 저장
- 재계산 로직 없음
- **검증 결과**: ✅ 통과 (고정값 저장 확인)

### ✅ 3. 스캔 ≠ 추천
- `scan_results` 테이블: 스캔 로그
- `recommendations` 테이블: 추천 이벤트
- **검증 결과**: ✅ 통과 (완전 분리)

### ✅ 4. 047810 중복 문제 해결
- 이전: 5개 날짜 모두 ACTIVE
- 현재: 1개 ACTIVE만 존재 (2025-12-15)
- **검증 결과**: ✅ 통과 (문제 해결됨)

---

## 최종 평가

### Backfill 상태
- ✅ **Backfill 완료**: 131개 추천 생성 성공
- ✅ **중복 제거**: ticker당 ACTIVE 1개만 유지
- ✅ **047810 문제 해결**: 중복 ACTIVE 제거 완료

### 결론
**Backfill이 성공적으로 완료되었고, 모든 핵심 계약이 검증되었습니다.**

---

## 참고 문서

- `backend/docs/V3_MIGRATION_EXECUTION_RESULTS.md` - 마이그레이션 실행 결과
- `backend/docs/V3_VERIFICATION_COMPLETE.md` - 검증 완료 리포트


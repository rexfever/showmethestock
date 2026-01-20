# 코드 리뷰 발견 문제점

## 1. `get_scan_by_date` 함수의 첫 번째 `market_condition` 생성 로직 문제

### 위치
- `backend/main.py` line 2112-2204

### 문제점

1. **SELECT 문에 레짐 v4 필드 누락** (line 2135-2139)
   - `institution_flow` 컬럼 누락
   - `midterm_regime`, `longterm_regime`, `short_term_risk_score`, `final_regime` 컬럼 누락
   - SELECT 문이 22개 컬럼만 조회하지만, `keys` 리스트는 28개 필드를 기대함

2. **`keys` 리스트와 SELECT 컬럼 순서 불일치** (line 2149-2157)
   - `keys` 리스트에는 레짐 v4 필드가 포함되어 있음 (line 2155)
   - 하지만 SELECT 문에는 해당 필드가 없어서 `zip(keys, row_mc)`가 잘못된 매핑 생성

3. **`market_condition` dict 생성 시 레짐 v4 필드 누락** (line 2178-2201)
   - `midterm_regime`, `longterm_regime`, `short_term_risk_score`, `final_regime` 필드가 dict에 포함되지 않음

### 해결 방법

첫 번째 부분을 두 번째 부분 (`get_latest_scan_from_db` 함수, line 2383-2546)과 동일한 로직으로 수정:

1. SELECT 문에 레짐 v4 필드 추가
2. `institution_flow` 컬럼 존재 여부 확인 후 동적 SELECT
3. `MarketCondition` 객체 생성 후 `asdict`로 변환 (dict 직접 생성 대신)

### 참고: 두 번째 부분은 올바름
- `get_latest_scan_from_db` 함수 (line 2383-2546)는 올바르게 구현됨
- SELECT 문에 레짐 v4 필드 포함
- `MarketCondition` 객체 생성 후 `asdict`로 변환


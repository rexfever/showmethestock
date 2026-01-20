# 날짜 처리 복잡성 분석 및 개선 방안

## 왜 이렇게 복잡한가?

### 현재 복잡성의 원인

#### 1. SQLite → PostgreSQL 마이그레이션 레거시

**문제**: `db_patch.py`는 SQLite 호환성을 위해 만들어진 레이어입니다.

```python
# backend/db_patch.py
"""
sqlite3.connect 패치를 통해 PostgreSQL을 사용할 수 있도록 래퍼 제공.
"""
```

**영향**:
- SQLite는 날짜를 TEXT로 저장했음
- PostgreSQL은 DATE/TIMESTAMP 타입 사용
- 호환성을 위해 `db_patch.py`가 중간 변환 레이어 역할

#### 2. 불필요한 변환 단계

**현재 흐름**:
```
YYYYMMDD 문자열 
  → date 객체 
  → db_patch에서 YYYYMMDD 문자열로 다시 변환 
  → PostgreSQL이 DATE로 파싱
```

**문제점**:
- date 객체를 만들었다가 다시 문자열로 변환
- 불필요한 변환 단계가 많음

#### 3. 일관성 없는 변환 로직

**DATE 타입**: YYYYMMDD로 변환
```python
if isinstance(value, date):
    return value.strftime("%Y%m%d")  # YYYYMMDD
```

**TIMESTAMP 타입**: YYYY-MM-DD HH:MM:SS로 변환
```python
if isinstance(value, datetime):
    return value.strftime("%Y-%m-%d %H:%M:%S")  # YYYY-MM-DD HH:MM:SS
```

**문제점**:
- DATE와 TIMESTAMP가 다른 형식으로 변환됨
- 일관성 부족

---

## 개선 방안

### 옵션 1: db_patch.py 제거 (권장)

**장점**:
- 변환 단계 제거
- psycopg가 직접 date/datetime 객체 처리
- 코드 단순화

**방법**:
```python
# 현재 (db_patch.py를 통한 변환)
date_obj = yyyymmdd_to_date("20251124")
# db_patch에서 "20251124" 문자열로 변환
# PostgreSQL이 DATE로 파싱

# 개선 (직접 psycopg 사용)
date_obj = yyyymmdd_to_date("20251124")
# psycopg가 date 객체를 직접 DATE 타입으로 전달
# 변환 단계 없음
```

**변경 사항**:
1. `db_patch.py`의 `_convert_value`에서 date/datetime 변환 제거
2. psycopg가 자동으로 처리하도록 변경

### 옵션 2: 변환 로직 통일

**현재**:
- DATE: YYYYMMDD
- TIMESTAMP: YYYY-MM-DD HH:MM:SS

**개선**:
- 둘 다 ISO 8601 형식 사용 (YYYY-MM-DD 또는 YYYY-MM-DDTHH:MM:SS)
- 또는 둘 다 YYYYMMDD 사용 (DATE는 날짜만, TIMESTAMP는 시간 포함)

### 옵션 3: psycopg 직접 사용

**현재**: sqlite3 호환 레이어를 통해 사용
**개선**: psycopg를 직접 사용하여 타입 변환 자동 처리

```python
# psycopg는 Python 객체를 자동으로 PostgreSQL 타입으로 변환
import psycopg

date_obj = date(2025, 11, 24)
cur.execute("INSERT INTO scan_rank (date, ...) VALUES (%s, ...)", (date_obj,))
# psycopg가 자동으로 DATE 타입으로 변환
```

---

## 권장 개선 방안

### 단계별 개선 계획

#### Step 1: db_patch.py의 date/datetime 변환 제거

```python
# backend/db_patch.py 수정
@staticmethod
def _convert_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    # datetime과 date는 변환하지 않고 그대로 전달
    # psycopg가 자동으로 처리
    if isinstance(value, (datetime, date)):
        return value  # 변환 제거!
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (dict, list)):
        return json_module.dumps(value, ensure_ascii=False)
    return value
```

**효과**:
- 변환 단계 1개 제거
- psycopg의 자동 타입 변환 활용

#### Step 2: 코드 단순화

**Before**:
```python
# 1. YYYYMMDD → date 객체
date_obj = yyyymmdd_to_date("20251124")

# 2. date 객체 → db_patch에서 YYYYMMDD 문자열로 변환
# 3. PostgreSQL이 DATE로 파싱
```

**After**:
```python
# 1. YYYYMMDD → date 객체
date_obj = yyyymmdd_to_date("20251124")

# 2. psycopg가 date 객체를 직접 DATE 타입으로 전달
# 변환 단계 없음!
```

#### Step 3: 테스트 및 검증

1. 기존 데이터와 호환성 확인
2. 날짜 조회/저장 테스트
3. 성능 측정 (변환 단계 제거로 인한 개선)

---

## 복잡성 비교

### 현재 (복잡)

```
API 입력: "20251124"
  ↓
yyyymmdd_to_date() → date 객체
  ↓
db_patch._convert_value() → "20251124" 문자열
  ↓
PostgreSQL 파싱 → DATE 타입
  ↓
저장
  ↓
조회: DATE 타입
  ↓
psycopg 자동 변환 → date 객체
  ↓
timestamp_to_yyyymmdd() → "20251124" 문자열
  ↓
API 응답: "20251124"
```

**변환 단계**: 5단계

### 개선 후 (단순)

```
API 입력: "20251124"
  ↓
yyyymmdd_to_date() → date 객체
  ↓
psycopg 자동 변환 → DATE 타입 (직접)
  ↓
저장
  ↓
조회: DATE 타입
  ↓
psycopg 자동 변환 → date 객체
  ↓
timestamp_to_yyyymmdd() → "20251124" 문자열
  ↓
API 응답: "20251124"
```

**변환 단계**: 3단계 (40% 감소)

---

## 결론

### 복잡한 이유

1. **SQLite 호환성 레이어**: `db_patch.py`가 불필요한 변환을 수행
2. **이중 변환**: date 객체 → 문자열 → DATE 타입
3. **레거시 코드**: 마이그레이션 과정에서 남은 복잡성

### 개선 효과

- **코드 단순화**: 변환 단계 40% 감소
- **성능 개선**: 불필요한 변환 제거
- **유지보수성 향상**: 단순한 흐름으로 이해하기 쉬움
- **일관성 확보**: psycopg의 표준 타입 변환 사용

### 다음 단계

1. `db_patch.py`의 date/datetime 변환 제거
2. 테스트 실행
3. 기존 데이터 호환성 확인
4. 배포


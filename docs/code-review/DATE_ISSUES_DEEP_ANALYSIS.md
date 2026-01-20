# 날짜 문제 심층 분석 보고서

## 분석 일시
2025-11-24

## 분석 범위
- 데이터베이스 스키마 정의
- 테이블 생성 함수
- 날짜 저장 로직
- 날짜 조회 로직
- 날짜 비교 로직
- 날짜 형식 변환

---

## 🔴 심각한 문제점

### 1. popup_notice 테이블 스키마 불일치

#### 문제 상황

**코드에서 생성하는 스키마** (`main.py:114-127`):
```python
def create_popup_notice_table(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS popup_notice(
            id SERIAL PRIMARY KEY,
            is_enabled BOOLEAN DEFAULT FALSE,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            start_date TEXT NOT NULL,      # ❌ TEXT
            end_date TEXT NOT NULL,        # ❌ TEXT
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)
```

**실제 DB 스키마** (`postgres_schema.sql:66-75`):
```sql
CREATE TABLE IF NOT EXISTS popup_notice (
    id          BIGSERIAL PRIMARY KEY,
    is_enabled  BOOLEAN NOT NULL DEFAULT FALSE,
    title       TEXT NOT NULL,
    message     TEXT NOT NULL,
    start_date  TIMESTAMP WITH TIME ZONE NOT NULL,  # ✅ TIMESTAMP WITH TIME ZONE
    end_date    TIMESTAMP WITH TIME ZONE NOT NULL,  # ✅ TIMESTAMP WITH TIME ZONE
    created_at  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
```

#### 영향

1. **테이블이 이미 존재하는 경우**: `CREATE TABLE IF NOT EXISTS`로 인해 실제 스키마는 `TIMESTAMP WITH TIME ZONE`이지만, 코드는 `TEXT`로 가정
2. **날짜 저장 시**: `update_popup_notice()`에서 YYYYMMDD 문자열을 그대로 저장하려고 시도 → PostgreSQL이 자동 변환 시도하지만 실패 가능
3. **날짜 조회 시**: `get_popup_notice_status()`에서 TIMESTAMP 객체를 받지만, TEXT로 가정하고 처리 → 복잡한 변환 로직 필요

#### 코드 위치

- **저장**: `main.py:3080-3107` (`update_popup_notice`)
- **조회**: `main.py:3109-3193` (`get_popup_notice_status`)

---

### 2. scan_rank 테이블 스키마 불일치

#### 문제 상황

**코드에서 생성하는 스키마** (`scan_service.py:14-29`):
```python
def _ensure_scan_rank_table(cursor) -> None:
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scan_rank(
            date TEXT NOT NULL,      # ❌ TEXT
            code TEXT NOT NULL,
            ...
        )
    """)
```

**실제 DB 스키마** (`postgres_schema.sql:133-154`):
```sql
CREATE TABLE IF NOT EXISTS scan_rank (
    date                DATE NOT NULL,    # ✅ DATE
    code                TEXT NOT NULL,
    ...
);
```

**또 다른 스키마 정의** (`main.py:34-58`):
```python
def create_scan_rank_table(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS scan_rank(
            date TEXT NOT NULL,      # ❌ TEXT
            ...
        )
    """)
```

#### 영향

1. **테이블이 이미 존재하는 경우**: 실제 스키마는 `DATE`이지만, 코드는 `TEXT`로 가정
2. **날짜 저장 시**: `save_scan_snapshot()`에서 YYYYMMDD 문자열을 그대로 저장 → PostgreSQL이 자동 변환 시도하지만 실패 가능
3. **날짜 조회 시**: `get_scan_by_date()`에서 `WHERE date = %s OR date = %s`로 DATE와 TEXT를 동시에 비교 → 비효율적이고 오류 가능

#### 코드 위치

- **저장**: `scan_service.py:105-194` (`save_scan_snapshot`)
- **조회**: `main.py:1710-1807` (`get_scan_by_date`)

---

### 3. 날짜 저장 시 형식 변환 누락

#### popup_notice 저장 문제

**현재 코드** (`main.py:3091-3100`):
```python
cur.execute("""
    INSERT INTO popup_notice (is_enabled, title, message, start_date, end_date, updated_at)
    VALUES (%s, %s, %s, %s, %s, NOW())
""", (
    notice.is_enabled,
    notice.title,
    notice.message,
    notice.start_date,  # ❌ YYYYMMDD 문자열 그대로 저장
    notice.end_date     # ❌ YYYYMMDD 문자열 그대로 저장
))
```

**문제점**:
- `notice.start_date`와 `notice.end_date`는 YYYYMMDD 형식의 문자열 (예: "20251124")
- 실제 DB 스키마는 `TIMESTAMP WITH TIME ZONE`
- PostgreSQL이 문자열을 TIMESTAMP로 자동 변환하려고 시도하지만, 형식이 맞지 않으면 오류 발생
- 또는 변환은 되지만 예상과 다른 값으로 저장될 수 있음

**올바른 처리**:
```python
from datetime import datetime
start_dt = datetime.strptime(notice.start_date, "%Y%m%d").replace(tzinfo=pytz.timezone('Asia/Seoul'))
end_dt = datetime.strptime(notice.end_date, "%Y%m%d").replace(hour=23, minute=59, second=59, tzinfo=pytz.timezone('Asia/Seoul'))
```

#### scan_rank 저장 문제

**현재 코드** (`scan_service.py:140, 155-156, 173-174`):
```python
enhanced_rank.append({
    "date": today_as_of,  # ❌ YYYYMMDD 문자열 그대로 저장
    ...
})

cur_hist.execute("DELETE FROM scan_rank WHERE date = %s AND scanner_version = %s", 
               (today_as_of, scanner_version))  # ❌ TEXT로 비교

cur_hist.executemany("""
    INSERT INTO scan_rank (date, code, ...)
    VALUES (%s, %s, ...)
""", [
    (r["date"], ...)  # ❌ YYYYMMDD 문자열 그대로 저장
])
```

**문제점**:
- `today_as_of`는 YYYYMMDD 형식의 문자열 (예: "20251124")
- 실제 DB 스키마는 `DATE`
- PostgreSQL이 문자열을 DATE로 자동 변환하려고 시도하지만, 형식이 맞지 않으면 오류 발생
- 또는 변환은 되지만 예상과 다른 값으로 저장될 수 있음

**올바른 처리**:
```python
from datetime import datetime
date_obj = datetime.strptime(today_as_of, "%Y%m%d").date()
```

---

### 4. 날짜 조회 시 형식 불일치

#### get_scan_by_date 문제

**현재 코드** (`main.py:1731-1740`):
```python
target_date = datetime.strptime(formatted_date, "%Y%m%d").date()

cur.execute("""
    SELECT ...
    FROM scan_rank
    WHERE date = %s OR date = %s  # ❌ DATE와 TEXT를 동시에 비교
    ORDER BY ...
""", (target_date, formatted_date))  # ❌ date 객체와 문자열을 모두 전달
```

**문제점**:
1. `target_date`는 `date` 객체, `formatted_date`는 YYYYMMDD 문자열
2. 실제 DB의 `date` 컬럼은 `DATE` 타입
3. `date = %s OR date = %s`로 두 형식을 모두 비교하는 것은 비효율적이고 오류 가능
4. 만약 실제 DB가 `TEXT`라면 `date` 객체 비교가 실패할 수 있음
5. 만약 실제 DB가 `DATE`라면 문자열 비교가 실패할 수 있음

**올바른 처리**:
```python
target_date = datetime.strptime(formatted_date, "%Y%m%d").date()
cur.execute("""
    SELECT ...
    FROM scan_rank
    WHERE date = %s  # DATE 타입으로만 비교
    ORDER BY ...
""", (target_date,))
```

#### get_popup_notice_status 문제

**현재 코드** (`main.py:3128-3169`):
```python
start_date_raw = row[3]  # TIMESTAMP WITH TIME ZONE 객체
end_date_raw = row[4]    # TIMESTAMP WITH TIME ZONE 객체

# 복잡한 형식 변환 로직
if start_date_raw:
    if hasattr(start_date_raw, 'strftime'):
        start_date = start_date_raw.strftime('%Y%m%d')
    elif isinstance(start_date_raw, str):
        start_date = normalize_date(start_date_raw)
    else:
        start_date = str(start_date_raw)

# 날짜 범위 확인
start_dt = datetime.strptime(start_date, "%Y%m%d")  # timezone-naive
end_dt = datetime.strptime(end_date, "%Y%m%d")     # timezone-naive
now = get_kst_now()  # timezone-aware
now_date_naive = datetime(now.year, now.month, now.day)  # timezone-naive로 변환
```

**문제점**:
1. DB에서 받은 TIMESTAMP 객체를 YYYYMMDD 문자열로 변환하는 복잡한 로직
2. timezone-aware와 timezone-naive datetime을 혼용
3. 날짜 비교 시 timezone 정보 손실

**올바른 처리**:
```python
from datetime import datetime
import pytz

start_date_raw = row[3]  # TIMESTAMP WITH TIME ZONE 객체
end_date_raw = row[4]    # TIMESTAMP WITH TIME ZONE 객체

# KST로 변환하여 날짜만 추출
kst = pytz.timezone('Asia/Seoul')
start_date_kst = start_date_raw.astimezone(kst).date()
end_date_kst = end_date_raw.astimezone(kst).date()
now_date = get_kst_now().date()

# 날짜 범위 확인
if now_date < start_date_kst or now_date > end_date_kst:
    is_enabled = False
```

---

### 5. 날짜 비교 로직의 복잡성

#### 문제점

1. **여러 형식 혼용**: TEXT, DATE, TIMESTAMP WITH TIME ZONE, datetime 객체, date 객체
2. **Timezone 처리 불일치**: timezone-aware와 timezone-naive 혼용
3. **자동 변환 의존**: PostgreSQL의 자동 타입 변환에 의존하여 예측 불가능한 동작
4. **에러 처리 부족**: 형식 변환 실패 시 적절한 에러 처리 없음

---

## 📊 문제점 요약

| 문제 | 위치 | 심각도 | 영향 |
|------|------|--------|------|
| popup_notice 스키마 불일치 | `main.py:114-127` vs `postgres_schema.sql:66-75` | 🔴 높음 | 날짜 저장/조회 실패 가능 |
| scan_rank 스키마 불일치 | `scan_service.py:14-29` vs `postgres_schema.sql:133-154` | 🔴 높음 | 날짜 저장/조회 실패 가능 |
| popup_notice 날짜 저장 형식 변환 누락 | `main.py:3091-3100` | 🔴 높음 | 잘못된 날짜 저장 |
| scan_rank 날짜 저장 형식 변환 누락 | `scan_service.py:140, 155-156, 173-174` | 🔴 높음 | 잘못된 날짜 저장 |
| get_scan_by_date 날짜 조회 형식 불일치 | `main.py:1731-1740` | 🟡 중간 | 비효율적이고 오류 가능 |
| get_popup_notice_status 날짜 조회 복잡성 | `main.py:3128-3169` | 🟡 중간 | timezone 처리 오류 가능 |

---

## 🔧 권장 수정 사항

### 1. 스키마 통일

**옵션 A: 코드를 실제 DB 스키마에 맞추기 (권장)**
- `create_popup_notice_table()`: `TIMESTAMP WITH TIME ZONE` 사용
- `_ensure_scan_rank_table()`: `DATE` 사용
- `create_scan_rank_table()`: `DATE` 사용

**옵션 B: DB 스키마를 코드에 맞추기 (비권장)**
- `postgres_schema.sql` 수정
- 기존 데이터 마이그레이션 필요

### 2. 날짜 저장 시 명시적 변환

**popup_notice**:
```python
from datetime import datetime
import pytz

kst = pytz.timezone('Asia/Seoul')
start_dt = datetime.strptime(notice.start_date, "%Y%m%d").replace(tzinfo=kst)
end_dt = datetime.strptime(notice.end_date, "%Y%m%d").replace(hour=23, minute=59, second=59, tzinfo=kst)

cur.execute("""
    INSERT INTO popup_notice (is_enabled, title, message, start_date, end_date, updated_at)
    VALUES (%s, %s, %s, %s, %s, NOW())
""", (notice.is_enabled, notice.title, notice.message, start_dt, end_dt))
```

**scan_rank**:
```python
from datetime import datetime

date_obj = datetime.strptime(today_as_of, "%Y%m%d").date()

cur_hist.execute("DELETE FROM scan_rank WHERE date = %s AND scanner_version = %s", 
               (date_obj, scanner_version))

cur_hist.executemany("""
    INSERT INTO scan_rank (date, code, ...)
    VALUES (%s, %s, ...)
""", [
    (date_obj, r["code"], ...)  # date 객체 사용
])
```

### 3. 날짜 조회 시 단순화

**get_scan_by_date**:
```python
target_date = datetime.strptime(formatted_date, "%Y%m%d").date()

cur.execute("""
    SELECT ...
    FROM scan_rank
    WHERE date = %s
    ORDER BY ...
""", (target_date,))
```

**get_popup_notice_status**:
```python
from datetime import datetime
import pytz

kst = pytz.timezone('Asia/Seoul')
start_date_kst = row[3].astimezone(kst).date()
end_date_kst = row[4].astimezone(kst).date()
now_date = get_kst_now().date()

if now_date < start_date_kst or now_date > end_date_kst:
    is_enabled = False
```

### 4. 날짜 유틸리티 함수 추가

```python
def yyyymmdd_to_date(yyyymmdd: str) -> date:
    """YYYYMMDD 문자열을 date 객체로 변환"""
    return datetime.strptime(yyyymmdd, "%Y%m%d").date()

def yyyymmdd_to_timestamp(yyyymmdd: str, tz=pytz.timezone('Asia/Seoul')) -> datetime:
    """YYYYMMDD 문자열을 timezone-aware datetime 객체로 변환"""
    return datetime.strptime(yyyymmdd, "%Y%m%d").replace(tzinfo=tz)

def timestamp_to_yyyymmdd(dt: datetime, tz=pytz.timezone('Asia/Seoul')) -> str:
    """timezone-aware datetime 객체를 YYYYMMDD 문자열로 변환"""
    return dt.astimezone(tz).strftime('%Y%m%d')
```

---

## 🎯 우선순위

1. **즉시 수정 필요** (🔴 높음):
   - popup_notice 스키마 불일치
   - scan_rank 스키마 불일치
   - 날짜 저장 시 형식 변환 누락

2. **빠른 수정 권장** (🟡 중간):
   - 날짜 조회 시 형식 불일치
   - 날짜 비교 로직 단순화

3. **개선 권장**:
   - 날짜 유틸리티 함수 추가
   - 날짜 처리 일관성 확보

---

## 📝 참고사항

- 현재 코드는 PostgreSQL의 자동 타입 변환에 의존하고 있어, 예측 불가능한 동작이 발생할 수 있음
- 실제 DB 스키마와 코드의 스키마 정의가 다를 경우, `CREATE TABLE IF NOT EXISTS`로 인해 실제 스키마가 우선됨
- 날짜 형식 변환을 명시적으로 처리하여 예측 가능한 동작 보장 필요


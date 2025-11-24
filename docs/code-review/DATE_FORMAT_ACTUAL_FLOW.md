# 날짜 형식 실제 처리 흐름

## 질문: DB만 YYYY-MM-DD 형태이고 그 외는 YYYYMMDD인가?

**답변: 아니요. 실제로는 더 복잡합니다.**

---

## 실제 처리 흐름

### 1. scan_rank 테이블 (DATE 타입)

#### 저장 흐름

```
1. 입력: "20251124" (YYYYMMDD 문자열)
   ↓
2. 변환: yyyymmdd_to_date("20251124")
   → date(2025, 11, 24) (Python date 객체)
   ↓
3. db_patch.py 변환: date 객체 → YYYYMMDD 문자열
   → "20251124" (YYYYMMDD)
   ↓
4. PostgreSQL 저장: YYYYMMDD 문자열을 DATE로 파싱
   → 내부적으로 DATE 타입으로 저장
```

**코드 위치**:
```python
# backend/services/scan_service.py
date_obj = yyyymmdd_to_date("20251124")  # date 객체
cur.execute("INSERT INTO scan_rank (date, ...) VALUES (%s, ...)", (date_obj,))

# backend/db_patch.py (자동 변환)
def _convert_value(value):
    if isinstance(value, date):
        return value.strftime("%Y%m%d")  # YYYYMMDD로 변환!
```

#### 조회 흐름

```
1. PostgreSQL 조회: DATE 타입
   → Python date 객체로 자동 변환
   ↓
2. Python 코드: date 객체
   → yyyymmdd_to_date() 또는 .strftime('%Y%m%d')로 YYYYMMDD 변환
   ↓
3. API 응답: "20251124" (YYYYMMDD 문자열)
```

**코드 위치**:
```python
# backend/main.py
target_date = yyyymmdd_to_date("20251124")  # date 객체
cur.execute("SELECT * FROM scan_rank WHERE date = %s", (target_date,))
# PostgreSQL이 date 객체를 받아서 DATE 타입과 비교
```

---

### 2. popup_notice 테이블 (TIMESTAMP WITH TIME ZONE 타입)

#### 저장 흐름

```
1. 입력: "20251124" (YYYYMMDD 문자열)
   ↓
2. 변환: yyyymmdd_to_timestamp("20251124", hour=0, minute=0, second=0)
   → datetime(2025, 11, 24, 0, 0, 0, tzinfo=KST) (Python datetime 객체)
   ↓
3. db_patch.py 변환: datetime 객체 → YYYY-MM-DD HH:MM:SS 문자열
   → "2025-11-24 00:00:00" (YYYY-MM-DD HH:MM:SS)
   ↓
4. PostgreSQL 저장: 문자열을 TIMESTAMP WITH TIME ZONE으로 파싱
   → 내부적으로 TIMESTAMP WITH TIME ZONE 타입으로 저장
```

**코드 위치**:
```python
# backend/main.py
start_dt = yyyymmdd_to_timestamp("20251124", hour=0, minute=0, second=0)
cur.execute("INSERT INTO popup_notice (start_date, ...) VALUES (%s, ...)", (start_dt,))

# backend/db_patch.py (자동 변환)
def _convert_value(value):
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")  # YYYY-MM-DD HH:MM:SS로 변환!
```

#### 조회 흐름

```
1. PostgreSQL 조회: TIMESTAMP WITH TIME ZONE 타입
   → Python datetime 객체로 자동 변환
   ↓
2. Python 코드: datetime 객체
   → timestamp_to_yyyymmdd()로 YYYYMMDD 변환
   ↓
3. API 응답: "20251124" (YYYYMMDD 문자열)
```

---

## 핵심 포인트

### db_patch.py의 역할

`db_patch.py`는 Python 객체를 PostgreSQL이 이해할 수 있는 형식으로 변환합니다:

```python
# backend/db_patch.py
def _convert_value(value):
    if isinstance(value, date):
        return value.strftime("%Y%m%d")  # DATE → YYYYMMDD 문자열
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")  # DATETIME → YYYY-MM-DD HH:MM:SS 문자열
```

**중요**: 
- `date` 객체는 **YYYYMMDD**로 변환되어 PostgreSQL에 전달
- `datetime` 객체는 **YYYY-MM-DD HH:MM:SS**로 변환되어 PostgreSQL에 전달

### PostgreSQL의 처리

PostgreSQL은 받은 문자열을 자동으로 파싱하여 적절한 타입으로 저장:
- `"20251124"` → DATE 타입으로 파싱
- `"2025-11-24 00:00:00"` → TIMESTAMP WITH TIME ZONE으로 파싱

### 조회 시

PostgreSQL은 저장된 값을 Python 객체로 자동 변환:
- DATE → Python `date` 객체
- TIMESTAMP WITH TIME ZONE → Python `datetime` 객체

---

## 형식 요약

| 단계 | scan_rank (DATE) | popup_notice (TIMESTAMP) |
|------|------------------|---------------------------|
| **API 입력** | `"20251124"` (YYYYMMDD) | `"20251124"` (YYYYMMDD) |
| **Python 변환** | `date(2025, 11, 24)` | `datetime(2025, 11, 24, 0, 0, 0, tzinfo=KST)` |
| **db_patch 변환** | `"20251124"` (YYYYMMDD) | `"2025-11-24 00:00:00"` (YYYY-MM-DD HH:MM:SS) |
| **PostgreSQL 저장** | DATE 타입 (내부) | TIMESTAMP WITH TIME ZONE (내부) |
| **PostgreSQL 조회** | `date(2025, 11, 24)` | `datetime(2025, 11, 24, 0, 0, 0, tzinfo=KST)` |
| **Python 변환** | `"20251124"` (YYYYMMDD) | `"20251124"` (YYYYMMDD) |
| **API 응답** | `"20251124"` (YYYYMMDD) | `"20251124"` (YYYYMMDD) |

---

## 결론

1. **API 레벨**: 항상 YYYYMMDD 문자열 사용
2. **Python 코드**: date/datetime 객체 사용
3. **db_patch 변환**: 
   - DATE → YYYYMMDD 문자열
   - TIMESTAMP → YYYY-MM-DD HH:MM:SS 문자열
4. **PostgreSQL**: 내부적으로 적절한 타입으로 저장
5. **조회**: PostgreSQL이 Python 객체로 자동 변환

**따라서 "DB만 YYYY-MM-DD"가 아니라, db_patch.py가 중간에서 변환 역할을 하며, 실제로는:**
- DATE 타입: YYYYMMDD 문자열로 전달
- TIMESTAMP 타입: YYYY-MM-DD HH:MM:SS 문자열로 전달


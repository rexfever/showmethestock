# 날짜 형식 처리 가이드

## 개요

개선된 날짜 처리 시스템은 명시적 형식 변환을 통해 예측 가능한 동작을 보장합니다.

---

## 📋 날짜 형식 처리 흐름

### 1. 입력 형식 (API/코드)

모든 날짜 입력은 **YYYYMMDD 형식의 문자열**로 통일:
- 예: `"20251124"` (2025년 11월 24일)
- API 파라미터: `?date=20251124`
- 함수 파라미터: `today_as_of: str = "20251124"`

### 2. 저장 형식 (데이터베이스)

#### popup_notice 테이블
- **컬럼 타입**: `TIMESTAMP WITH TIME ZONE`
- **저장 형식**: timezone-aware datetime 객체
- **변환**: `YYYYMMDD` → `datetime` (KST timezone)

```python
# 저장 시
start_dt = yyyymmdd_to_timestamp("20251124", hour=0, minute=0, second=0)
# 결과: datetime(2025, 11, 24, 0, 0, 0, tzinfo=KST)

# DB에 저장
INSERT INTO popup_notice (start_date, ...) VALUES (%s, ...)
# %s = datetime 객체 (timezone-aware)
```

#### scan_rank 테이블
- **컬럼 타입**: `DATE`
- **저장 형식**: date 객체
- **변환**: `YYYYMMDD` → `date`

```python
# 저장 시
date_obj = yyyymmdd_to_date("20251124")
# 결과: date(2025, 11, 24)

# DB에 저장
INSERT INTO scan_rank (date, ...) VALUES (%s, ...)
# %s = date 객체
```

### 3. 조회 형식 (API 응답)

모든 날짜 조회는 **YYYYMMDD 형식의 문자열**로 반환:
- `TIMESTAMP WITH TIME ZONE` → `YYYYMMDD`
- `DATE` → `YYYYMMDD`

```python
# 조회 시
timestamp_obj = row["start_date"]  # TIMESTAMP WITH TIME ZONE 객체
start_date = timestamp_to_yyyymmdd(timestamp_obj)
# 결과: "20251124"

date_obj = row["date"]  # DATE 객체
date_str = date_obj.strftime('%Y%m%d')
# 결과: "20251124"
```

---

## 🔧 유틸리티 함수

### `yyyymmdd_to_date(yyyymmdd: str) -> date`

YYYYMMDD 문자열을 date 객체로 변환

```python
from date_helper import yyyymmdd_to_date

date_obj = yyyymmdd_to_date("20251124")
# 결과: date(2025, 11, 24)
```

**사용 위치**:
- `scan_rank` 테이블 저장 시
- `scan_rank` 테이블 조회 시 (WHERE 절)
- 날짜 비교 로직

### `yyyymmdd_to_timestamp(yyyymmdd: str, hour=0, minute=0, second=0, tz=KST) -> datetime`

YYYYMMDD 문자열을 timezone-aware datetime 객체로 변환

```python
from date_helper import yyyymmdd_to_timestamp

# 시작일: 00:00:00
start_dt = yyyymmdd_to_timestamp("20251124", hour=0, minute=0, second=0)
# 결과: datetime(2025, 11, 24, 0, 0, 0, tzinfo=KST)

# 종료일: 23:59:59
end_dt = yyyymmdd_to_timestamp("20251130", hour=23, minute=59, second=59)
# 결과: datetime(2025, 11, 30, 23, 59, 59, tzinfo=KST)
```

**사용 위치**:
- `popup_notice` 테이블 저장 시

### `timestamp_to_yyyymmdd(dt: datetime, tz=KST) -> str`

timezone-aware datetime 객체를 YYYYMMDD 문자열로 변환

```python
from date_helper import timestamp_to_yyyymmdd

timestamp_obj = row["start_date"]  # TIMESTAMP WITH TIME ZONE
date_str = timestamp_to_yyyymmdd(timestamp_obj)
# 결과: "20251124"
```

**사용 위치**:
- `popup_notice` 테이블 조회 시 (API 응답)

---

## 📊 실제 처리 예시

### 예시 1: popup_notice 저장

```python
# 입력: API 요청
POST /admin/popup-notice
{
  "start_date": "20251124",  # YYYYMMDD 문자열
  "end_date": "20251130"     # YYYYMMDD 문자열
}

# 처리: update_popup_notice()
from date_helper import yyyymmdd_to_timestamp

start_dt = yyyymmdd_to_timestamp("20251124", hour=0, minute=0, second=0)
end_dt = yyyymmdd_to_timestamp("20251130", hour=23, minute=59, second=59)

# 저장: DB에 datetime 객체로 저장
INSERT INTO popup_notice (start_date, end_date, ...)
VALUES (%s, %s, ...)
# %s = datetime 객체 (timezone-aware)
```

### 예시 2: popup_notice 조회

```python
# 조회: DB에서 TIMESTAMP WITH TIME ZONE 객체 받음
SELECT start_date, end_date FROM popup_notice
# row[3] = datetime(2025, 11, 24, 0, 0, 0, tzinfo=KST)
# row[4] = datetime(2025, 11, 30, 23, 59, 59, tzinfo=KST)

# 변환: YYYYMMDD 문자열로 변환
from date_helper import timestamp_to_yyyymmdd

start_date = timestamp_to_yyyymmdd(row[3])  # "20251124"
end_date = timestamp_to_yyyymmdd(row[4])   # "20251130"

# 응답: API 응답
{
  "start_date": "20251124",  # YYYYMMDD 문자열
  "end_date": "20251130"     # YYYYMMDD 문자열
}
```

### 예시 3: scan_rank 저장

```python
# 입력: 함수 호출
save_scan_snapshot(scan_items, "20251124", "v1")
# today_as_of = "20251124" (YYYYMMDD 문자열)

# 처리: save_scan_snapshot()
from date_helper import yyyymmdd_to_date

date_obj = yyyymmdd_to_date("20251124")
# 결과: date(2025, 11, 24)

# 저장: DB에 date 객체로 저장
INSERT INTO scan_rank (date, code, ...)
VALUES (%s, %s, ...)
# %s = date 객체
```

### 예시 4: scan_rank 조회

```python
# 입력: API 요청
GET /scan-by-date/20251124

# 처리: get_scan_by_date()
from date_helper import yyyymmdd_to_date

target_date = yyyymmdd_to_date("20251124")
# 결과: date(2025, 11, 24)

# 조회: DB에서 DATE 타입으로 조회
SELECT * FROM scan_rank WHERE date = %s
# %s = date 객체

# 응답: date 객체는 자동으로 문자열로 변환되어 JSON 응답
{
  "as_of": "20251124",  # YYYYMMDD 문자열
  ...
}
```

---

## 🔄 형식 변환 매트릭스

| 입력 형식 | 변환 함수 | 출력 형식 | 사용 위치 |
|----------|----------|----------|----------|
| `"20251124"` (str) | `yyyymmdd_to_date()` | `date(2025, 11, 24)` | scan_rank 저장/조회 |
| `"20251124"` (str) | `yyyymmdd_to_timestamp()` | `datetime(2025, 11, 24, 0, 0, 0, tzinfo=KST)` | popup_notice 저장 |
| `datetime(...)` | `timestamp_to_yyyymmdd()` | `"20251124"` (str) | popup_notice 조회 |
| `date(...)` | `.strftime('%Y%m%d')` | `"20251124"` (str) | scan_rank 조회 (직접) |

---

## ✅ 개선 효과

### Before (개선 전)
- ❌ 스키마 불일치: 코드는 TEXT, DB는 TIMESTAMP/DATE
- ❌ 자동 변환 의존: PostgreSQL 자동 변환에 의존
- ❌ 복잡한 변환 로직: 여러 형식 혼용
- ❌ 예측 불가능: 변환 실패 가능성

### After (개선 후)
- ✅ 스키마 일치: 코드와 DB 스키마 통일
- ✅ 명시적 변환: 모든 변환을 명시적으로 처리
- ✅ 단순한 로직: 유틸리티 함수로 일관성 확보
- ✅ 예측 가능: 명확한 변환 경로

---

## 📝 주의사항

1. **항상 유틸리티 함수 사용**: 직접 변환하지 말고 `date_helper` 함수 사용
2. **timezone 처리**: `popup_notice`는 항상 KST timezone 사용
3. **날짜 비교**: date 객체끼리 비교 (문자열 비교 금지)
4. **API 응답**: 항상 YYYYMMDD 문자열로 반환

---

## 🔗 관련 파일

- `backend/date_helper.py`: 날짜 유틸리티 함수
- `backend/main.py`: API 엔드포인트 (popup_notice, scan_rank 조회)
- `backend/services/scan_service.py`: scan_rank 저장 로직


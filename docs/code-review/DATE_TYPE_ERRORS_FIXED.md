# 날짜 타입 오류 수정 내역

## 🔴 발견된 심각한 오류들

### 1. **get_quarterly_analysis() - BETWEEN 쿼리 실패**
**위치**: `backend/main.py:2787-2816`
**문제**: YYYY-MM-DD 형식으로 BETWEEN 쿼리 수행 → DB의 YYYYMMDD 형식과 불일치
**수정**: YYYYMMDD 형식으로 변경
```python
# 수정 전
start_date = f"{year}-01-01"  # YYYY-MM-DD
end_date = f"{year}-03-31"    # YYYY-MM-DD

# 수정 후
start_date = f"{year}0101"    # YYYYMMDD
end_date = f"{year}0331"      # YYYYMMDD
```

### 2. **validate_from_snapshot() - base_dt 형식 불일치**
**위치**: `backend/main.py:771`
**문제**: `base_dt = as_of` - as_of가 YYYY-MM-DD 형식일 수 있음
**수정**: `compact_date` 사용 (이미 YYYYMMDD로 변환됨)
```python
# 수정 전
base_dt = as_of

# 수정 후
base_dt = compact_date
```

### 3. **날짜 비교 오류 - df_since['date'] >= base_dt**
**위치**: `backend/main.py:801`
**문제**: 문자열과 날짜 비교, 형식 불일치
**수정**: pd.to_datetime으로 변환 후 비교
```python
# 수정 전
sub = df_since[df_since['date'] >= base_dt]

# 수정 후
df_since['date_dt'] = pd.to_datetime(df_since['date'], format='%Y%m%d')
base_dt_dt = pd.to_datetime(base_dt, format='%Y%m%d')
sub = df_since[df_since['date_dt'] >= base_dt_dt]
```

### 4. **pd.to_datetime format 누락**
**위치**: `backend/main.py:1172-1173`
**문제**: format 지정 없이 pd.to_datetime 사용 → 자동 추론 실패 가능
**수정**: format='%Y%m%d' 지정
```python
# 수정 전
df['date'] = pd.to_datetime(df.index)
entry_date_dt = pd.to_datetime(entry_date)

# 수정 후
df['date_dt'] = pd.to_datetime(df['date'], format='%Y%m%d')  # 또는 df.index
entry_date_dt = pd.to_datetime(entry_date, format='%Y%m%d')
```

### 5. **pd.to_datetime format 누락 (returns_service)**
**위치**: `backend/services/returns_service.py:68`
**문제**: format 지정 없이 날짜 차이 계산
**수정**: format='%Y%m%d' 지정
```python
# 수정 전
days_diff = (pd.to_datetime(current_date) - pd.to_datetime(scan_date)).days

# 수정 후
days_diff = (pd.to_datetime(current_date, format='%Y%m%d') - pd.to_datetime(scan_date, format='%Y%m%d')).days
```

### 6. **SQLite date() 함수 사용 오류**
**위치**: `backend/new_recurrence_api.py:30, 102`
**문제**: SQLite date() 함수는 YYYY-MM-DD 형식만 지원, DB는 YYYYMMDD 형식
**수정**: Python에서 날짜 계산 후 YYYYMMDD 형식으로 쿼리
```python
# 수정 전
WHERE date >= date('now', '-{} days')

# 수정 후
from datetime import datetime, timedelta
end_date = datetime.now().strftime('%Y%m%d')
start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
WHERE date >= ? AND date <= ?
```

## ✅ 수정 완료 항목

1. ✅ `get_quarterly_analysis()` - YYYYMMDD 형식으로 수정
2. ✅ `validate_from_snapshot()` - compact_date 사용
3. ✅ `main.py:801` - 날짜 비교 형식 통일
4. ✅ `main.py:1172-1173` - pd.to_datetime format 지정
5. ✅ `services/returns_service.py:68` - pd.to_datetime format 지정
6. ✅ `new_recurrence_api.py` - SQLite date() 함수 제거

## 📊 영향도

### 높음 (즉시 영향)
- `get_quarterly_analysis()` - 분기별 분석이 작동하지 않음
- `validate_from_snapshot()` - 스냅샷 검증 실패

### 중간
- `new_recurrence_api.py` - 재등장 종목 조회 실패 가능
- 날짜 비교 오류 - 수익률 계산 오류 가능

### 낮음
- pd.to_datetime format 누락 - 일부 엣지 케이스에서만 문제

## 🔍 추가 검증 필요

1. 다른 서비스 파일들에서도 비슷한 패턴 확인
2. 테스트 코드 실행으로 모든 수정 사항 검증
3. 실제 DB에서 BETWEEN 쿼리 테스트




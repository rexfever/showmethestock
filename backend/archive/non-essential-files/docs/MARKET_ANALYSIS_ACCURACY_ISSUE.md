# 장세 분석 정확성 문제

## 문제 상황

**11월 17일 KOSPI 수익률:**
- 예상: **1.94%**
- 분석 결과: **2.13%**
- 차이: **0.19%p**

## 원인 분석

### 가능한 원인

1. **전일 거래일 찾기 오류**
   - 11월 17일 (월요일)의 전일은 11월 14일 (금요일)
   - 11월 15일, 16일은 휴일
   - 전일을 잘못 찾았을 가능성

2. **데이터 수집 시점 차이**
   - API에서 가져온 데이터의 시점이 다를 수 있음
   - 장 마감 후 확정 데이터 vs 장중 데이터

3. **get_ohlcv 반환 데이터 구조**
   - `get_ohlcv`는 `base_dt` 기준으로 데이터 반환
   - 마지막 행이 정확히 해당 날짜인지 확인 필요
   - date 컬럼으로 정확한 날짜 매칭 필요

## 해결 방안

### 1. date 컬럼 기반 날짜 매칭

```python
# date 컬럼이 있으면 날짜로 정확히 찾기
if 'date' in df.columns:
    # 당일 행 찾기
    date_str_clean = date.replace('-', '')
    for i in range(len(df)-1, -1, -1):
        if date_str_clean in str(df.iloc[i]['date']):
            current_idx = i
            break
    
    # 전일 거래일 찾기
    for i in range(current_idx - 1, -1, -1):
        prev_date_str = str(df.iloc[i]['date'])
        if is_trading_day(prev_date_str):
            prev_idx = i
            break
```

### 2. 로그 추가

- 전일 날짜와 종가 로그 출력
- 당일 날짜와 종가 로그 출력
- 계산된 수익률 로그 출력

### 3. 데이터 검증

- API에서 가져온 데이터의 날짜 확인
- 전일이 정확히 11월 14일인지 확인
- 종가 값이 정확한지 확인

## 현재 상태

- 거래일 필터링: ✅ 추가됨
- effective_return 계산: ✅ 개선됨 (일반적인 경우 종가 기준)
- 전일 찾기 로직: ⚠️ 개선 필요 (date 컬럼 기반 매칭)

## 다음 단계

1. date 컬럼 기반 날짜 매칭 로직 추가
2. 로그 추가하여 정확한 전일/당일 확인
3. 실제 데이터와 비교하여 정확성 검증


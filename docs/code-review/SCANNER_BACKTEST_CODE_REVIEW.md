# 스캐너 백테스트 스크립트 코드 리뷰

**작성일**: 2025-11-24

## 발견된 문제점

### 1. 성과 분석에서 거래일 조정 로직 문제 ⚠️

**위치**: `analyze_performance()` 함수 (라인 224-234)

**문제**:
```python
target_date = datetime.strptime(date, "%Y%m%d") + timedelta(days=days_after)
target_date_str = target_date.strftime("%Y%m%d")

# 거래일 조정
trading_days = get_trading_days(date, target_date_str)
if trading_days:
    target_date_str = trading_days[-1] if len(trading_days) > 1 else date
else:
    target_date_str = date
```

**이슈**:
- `get_trading_days(date, target_date_str)`는 시작일부터 종료일까지의 모든 거래일을 반환
- N일 후의 정확한 거래일을 찾는 것이 아니라, 마지막 거래일을 사용
- 예: `days_after=5`일 때, 주말/공휴일을 고려하지 않고 단순히 5일 후를 사용

**해결 방안**:
- N일 후의 정확한 거래일을 찾는 함수 필요
- 또는 `get_trading_days` 결과에서 N번째 거래일 선택

### 2. OHLCV 조회 시 base_dt 사용 문제 ⚠️

**위치**: `analyze_performance()` 함수 (라인 249)

**문제**:
```python
df = api.get_ohlcv(code, 1, target_date_str)
```

**이슈**:
- `count=1`로 조회하면 최신 1일 데이터만 가져옴
- `base_dt`가 지정되어도, 해당 날짜의 데이터가 없으면 빈 DataFrame 반환 가능
- 과거 날짜 조회 시 캐시 활용이 제대로 되는지 확인 필요

**해결 방안**:
- `base_dt`를 명시적으로 지정하여 해당 날짜 기준 데이터 조회
- 캐시 히트 여부 확인

### 3. 에러 처리 부족 ⚠️

**위치**: 여러 곳

**문제**:
- `analyze_performance()`에서 예외 발생 시 조용히 `continue`
- 에러 로그가 부족하여 디버깅 어려움
- 일부 실패가 전체 결과에 영향을 주지 않지만, 통계가 부정확해질 수 있음

**해결 방안**:
- 에러 카운터 추가
- 실패한 종목/날짜 추적
- 최종 리포트에 에러 통계 포함

### 4. 캐시 활용 확인 부족 ⚠️

**위치**: `run_scan_for_date()` 함수

**문제**:
- `use_cache` 플래그가 있지만, 실제 OHLCV 캐시 사용 여부를 강제하지 않음
- `market_analyzer.clear_cache()`만 호출하고, `api`의 캐시는 그대로 사용
- 디스크 캐시 활용 여부 확인 불가

**해결 방안**:
- 캐시 통계를 각 스캔 전후로 확인
- 캐시 히트율 로깅

### 5. 날짜 정규화 일관성 ⚠️

**위치**: 여러 곳

**문제**:
- `normalize_date()`를 사용하지만, 일부 곳에서는 직접 `strptime` 사용
- 날짜 형식이 일관되지 않을 수 있음

**해결 방안**:
- 모든 날짜 처리를 `normalize_date()`로 통일
- 날짜 검증 강화

### 6. 성과 분석에서 가격 조회 실패 시 처리 ⚠️

**위치**: `analyze_performance()` 함수 (라인 242-266)

**문제**:
```python
try:
    # 스캔 당일 가격
    scan_price = item.get("current_price") or item.get("close_price")
    if not scan_price:
        continue
    
    # N일 후 가격
    df = api.get_ohlcv(code, 1, target_date_str)
    if df.empty:
        continue
    ...
except Exception as e:
    continue
```

**이슈**:
- 조용히 `continue`하여 실패한 종목이 통계에서 제외됨
- 실패 원인을 알 수 없음
- 전체 성과 통계가 부정확해질 수 있음

**해결 방안**:
- 실패한 종목 추적
- 실패 원인 로깅
- 최종 리포트에 실패 통계 포함

### 7. 유니버스 조회 시 날짜 파라미터 미사용 ⚠️

**위치**: `get_universe()` 함수 (라인 52-64)

**문제**:
```python
def get_universe(kospi_limit: int = None, kosdaq_limit: int = None, date: str = None) -> List[str]:
    ...
    kospi = api.get_top_codes('KOSPI', kp)
    kosdaq = api.get_top_codes('KOSDAQ', kd)
```

**이슈**:
- `date` 파라미터를 받지만 사용하지 않음
- 과거 날짜의 유니버스를 조회할 수 없음
- 백테스트 시 과거 시점의 유니버스를 사용해야 함

**해결 방안**:
- `api.get_top_codes()`에 날짜 파라미터 지원 여부 확인
- 지원하지 않으면 현재 유니버스 사용 (제한사항 명시)

### 8. 메모리 사용량 최적화 부족 ⚠️

**위치**: 전체

**문제**:
- 대량 백테스트 시 모든 결과를 메모리에 보관
- 성과 분석 시 모든 종목의 OHLCV 데이터를 조회
- 메모리 사용량이 증가할 수 있음

**해결 방안**:
- 스트리밍 방식으로 결과 저장
- 배치 처리로 메모리 사용량 제한

## 개선 제안

### 우선순위 높음

1. **거래일 조정 로직 수정**: N일 후의 정확한 거래일 찾기
2. **OHLCV 조회 개선**: `base_dt` 명시적 사용 및 캐시 확인
3. **에러 처리 강화**: 실패 추적 및 로깅

### 우선순위 중간

4. **캐시 활용 확인**: 캐시 히트율 로깅
5. **날짜 정규화 통일**: 모든 날짜 처리 일관성
6. **유니버스 날짜 지원**: 과거 날짜 유니버스 조회

### 우선순위 낮음

7. **메모리 최적화**: 대량 백테스트 시 스트리밍 처리

## 테스트 필요 사항

1. 거래일 조정 로직 정확성
2. OHLCV 캐시 활용 여부
3. 에러 처리 및 복구
4. 날짜 경계 케이스 (월말, 연말, 공휴일)
5. 대량 데이터 처리 성능


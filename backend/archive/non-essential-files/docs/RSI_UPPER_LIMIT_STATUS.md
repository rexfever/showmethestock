# RSI 상한선 완화 상태

## ✅ 완화 적용 완료

### 변경 사항

**이전:**
- RSI 상한선: **70 (고정값)**
- 차단 비율: **83.3%** (11월 17일 기준)

**현재:**
- RSI 상한선: **rsi_threshold + 25.0 (동적 조정)**
- 중립장 기준: **57.0 + 25.0 = 82.0**
- 차단 비율: **15.2%** (11월 17일 기준)

### 코드 위치

```python
# backend/scanner.py (라인 608-617)
if market_condition and config.market_analysis_enable:
    # 시장 상황에 따라 RSI 상한선도 조정 (rsi_threshold + 여유분)
    # rsi_threshold는 신호 판단용, 상한선은 과매수 방지용이므로 더 높게 설정
    # 여유분을 15.0 → 25.0으로 증가 (더 많은 종목 통과)
    rsi_upper_limit = market_condition.rsi_threshold + 25.0  # 기본 70 = 57 + 13 → 82 = 57 + 25
else:
    rsi_upper_limit = config.rsi_upper_limit

cur = df.iloc[-1]
if cur.RSI_TEMA > rsi_upper_limit:
    return None  # RSI 상한선 초과 종목 즉시 제외
```

### 개선 효과

- **차단 비율**: 83.3% → 15.2% (68.1%p 개선)
- **통과 비율**: 16.7% → 84.8% (68.1%p 개선)

### 현재 상황

- ✅ RSI 상한선 완화: **적용 완료**
- ✅ 신호 개수 확장: **적용 완료** (4개 → 7개)
- ⚠️ 여전히 0개 결과: **다른 필터 원인** (신호 부족, 추세 조건 등)

## 결론

RSI 상한선 완화는 이미 적용되어 있고, 차단 비율이 크게 개선되었습니다. 하지만 여전히 0개가 나오는 것은 **신호 부족** 또는 **추세 조건** 때문일 가능성이 높습니다.


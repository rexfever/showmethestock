# 📊 스캐너 추세 변화 대응 방법

## 개요
10월 성과 하락(평균 수익률 20.22%, 승률 90.74%)에 대한 대응 방안 및 추세 변화 감지 및 적응 시스템 구축 가이드

---

## 🔍 1. 시장 상황 모니터링 강화

### 1.1 실시간 시장 지표 분석
```python
# backend/market_analyzer.py에 이미 구현되어 있음
# 추가 강화 사항:
- KOSPI 수익률 모니터링 (일간, 주간, 월간)
- 변동성 지표 (VIX, 변동성 지수)
- 거래량 추이 분석
- 외국인/기관 매매 동향
```

### 1.2 시장 국면 분류
- **강세장 (Bull Market)**: 평균 수익률 > 3%, 승률 > 60%
- **중립장 (Neutral Market)**: 평균 수익률 -1% ~ 3%
- **약세장 (Bear Market)**: 평균 수익률 < -1%, 승률 < 40%
- **급락장 (Crash)**: 평균 수익률 < -3%, 급격한 하락

---

## 🎯 2. 동적 필터링 기준 조정

### 2.1 시장 상황별 파라미터 조정 (현재 구현됨)

#### 강세장 (Bull Market)
```python
{
    "rsi_threshold": 65,           # RSI 임계값 완화
    "min_signals": 2,              # 신호 요건 완화
    "vol_ma5_mult": 1.5,           # 거래량 조건 완화
    "gap_max": 0.15,               # 갭 허용 범위 확대
    "ext_from_tema20_max": 0.20,   # 추격 이격 확대
}
```

#### 중립장 (Neutral Market)
```python
{
    "rsi_threshold": 60,           # 기본값 유지
    "min_signals": 3,              # 기본값
    "vol_ma5_mult": 1.8,           # 기본값
    "gap_max": 0.10,               # 기본값
    "ext_from_tema20_max": 0.15,   # 기본값
}
```

#### 약세장 (Bear Market)
```python
{
    "rsi_threshold": 55,           # RSI 임계값 강화
    "min_signals": 4,              # 신호 요건 강화
    "vol_ma5_mult": 2.0,           # 거래량 조건 강화
    "gap_max": 0.08,               # 갭 허용 범위 축소
    "ext_from_tema20_max": 0.10,   # 추격 이격 축소
}
```

#### 급락장 (Crash)
```python
{
    "rsi_threshold": 50,           # 매우 보수적
    "min_signals": 4,              # 최대 강화
    "vol_ma5_mult": 2.5,           # 매우 강한 거래량 필요
    "gap_max": 0.05,               # 최소 갭만 허용
    "ext_from_tema20_max": 0.08,   # 매우 보수적
    "min_score": 8,                # 점수 기준 강화
}
```

---

## 📈 3. 성과 기반 자동 조정

### 3.1 롤링 성과 분석
```python
# 최근 4주간 성과 추적
recent_4weeks_performance = {
    "avg_return": calculate_avg_return(last_4_weeks),
    "win_rate": calculate_win_rate(last_4_weeks),
    "max_drawdown": calculate_max_drawdown(last_4_weeks),
}

# 성과 저하 감지
if recent_4weeks_performance["avg_return"] < threshold:
    # 필터링 기준 강화
    adjust_parameters_to_conservative()
```

### 3.2 월간 성과 리뷰
- **7월**: 57.10% (완벽) → 기준 유지
- **8월**: 57.83% (완벽) → 기준 유지  
- **9월**: 33.81% (양호) → 경계
- **10월**: 20.22% (저하) → **조정 필요** ⚠️

**10월 조정 사항:**
```python
if current_month_avg_return < 30.0:  # 10월 20.22%
    # 1. 신호 요건 강화
    config.min_signals = 4  # 3 → 4
    
    # 2. RSI 상한선 강화
    config.rsi_upper_limit = 65  # 70 → 65
    
    # 3. 거래량 조건 강화
    config.vol_ma5_mult = 2.0  # 1.8 → 2.0
    
    # 4. 최소 점수 상향
    config.min_score = 6  # 4 → 6
```

---

## 🎨 4. 섹터/테마 로테이션 대응

### 4.1 섹터 성과 추적
```python
sector_performance = {
    "반도체": calculate_sector_return(["005930", "000660", ...]),
    "2차전지": calculate_sector_return(["006400", "373220", ...]),
    "조선": calculate_sector_return(["009540", "042660", ...]),
    # ...
}

# 하위 성과 섹터 필터링
underperforming_sectors = [
    sector for sector, perf in sector_performance.items() 
    if perf < market_avg_return * 0.7
]
```

### 4.2 테마별 가중치 조정
- **상승 테마**: 가중치 1.2배
- **중립 테마**: 가중치 1.0배
- **하락 테마**: 가중치 0.8배 (또는 제외)

---

## 🛡️ 5. 리스크 관리 강화

### 5.1 위험도 기반 필터링
```python
# backend/scanner.py의 calculate_risk_score 활용
risk_score, risk_flags = calculate_risk_score(df)

# 위험도가 높은 종목 제외
if risk_score >= 3:
    return None  # 제외
```

### 5.2 최대 손실 제한
```python
# 최근 추천 종목들의 최악 성과 추적
worst_performers = get_worst_performers(period=30)

if worst_performers["avg_loss"] < -10.0:  # 평균 손실 10% 이상
    # 더 보수적인 필터링 적용
    config.require_dema_slope = "required"  # DEMA 슬로프 필수
```

---

## 📊 6. 실시간 성과 모니터링

### 6.1 일일 성과 추적
```python
# 매일 스캔 후 성과 체크
daily_scan_results = execute_scan()
daily_performance = calculate_performance(daily_scan_results)

# 3일 연속 저성과 시 경고
if consecutive_low_performance_days >= 3:
    send_alert("⚠️ 3일 연속 저성과 감지")
    adjust_parameters_conservative()
```

### 6.2 주간 성과 리뷰
```python
# 매주 주간 보고서 생성 후 자동 분석
weekly_report = generate_weekly_report(year, month, week)

if weekly_report["statistics"]["avg_return"] < 25.0:
    # 파라미터 조정
    adjust_for_low_performance()
```

---

## 🔧 7. 자동 파라미터 튜닝

### 7.1 A/B 테스트
```python
# 두 가지 설정으로 병렬 테스트
config_a = get_current_config()
config_b = get_conservative_config()

# 1주일간 A/B 테스트
results_a = test_config(config_a, days=7)
results_b = test_config(config_b, days=7)

# 더 나은 성과의 설정 채택
if results_b["avg_return"] > results_a["avg_return"] * 1.2:
    apply_config(config_b)
```

### 7.2 역동적 임계값 조정
```python
# 최근 성과에 따라 자동 조정
def auto_adjust_thresholds(recent_performance):
    if recent_performance["avg_return"] < 20.0:
        # 성과 저하 → 기준 강화
        config.min_signals += 1
        config.rsi_upper_limit -= 5
        config.vol_ma5_mult += 0.2
    elif recent_performance["avg_return"] > 50.0:
        # 성과 과열 → 기준 완화
        config.min_signals = max(2, config.min_signals - 1)
        config.rsi_upper_limit = min(70, config.rsi_upper_limit + 5)
```

---

## 📋 8. 구현 우선순위

### Phase 1: 즉시 적용 (1주일 내)
1. ✅ **월간 성과 기반 자동 조정** 구현
2. ✅ **10월 대응: 파라미터 강화 적용**
3. ✅ **일일 성과 모니터링 알림** 설정

### Phase 2: 단기 개선 (1개월 내)
4. **롤링 성과 분석** 자동화
5. **섹터 성과 추적** 시스템 구축
6. **위험도 기반 필터링** 강화

### Phase 3: 중장기 개선 (3개월 내)
7. **A/B 테스트 시스템** 구축
8. **머신러닝 기반 파라미터 최적화**
9. **실시간 시장 상황 대시보드**

---

## 🎯 9. 구체적인 10월 대응 조치

### 9.1 즉시 적용 가능한 조정
```python
# config.py 또는 런타임 설정
config_october_adjustment = {
    "min_signals": 4,              # 3 → 4 (신호 요건 강화)
    "rsi_upper_limit": 65,         # 70 → 65 (과열 방지)
    "vol_ma5_mult": 2.0,           # 1.8 → 2.0 (거래량 강화)
    "min_score": 6,                # 4 → 6 (점수 기준 상향)
    "require_dema_slope": "required",  # DEMA 슬로프 필수
    "gap_max": 0.08,               # 0.10 → 0.08 (갭 축소)
}
```

### 9.2 모니터링 지표
- **목표 평균 수익률**: 30% 이상 (현재 20.22%)
- **목표 승률**: 90% 이상 (현재 90.74% 유지)
- **최대 손실 종목 비율**: 10% 이하

---

## 📝 10. 체크리스트

### 매일 확인
- [ ] 전일 스캔 결과 성과 확인
- [ ] 시장 지수(KOSPI) 등락률 확인
- [ ] 이상 신호 감지 여부 확인

### 매주 확인
- [ ] 주간 평균 수익률 계산
- [ ] 승률 추이 확인
- [ ] 파라미터 조정 필요 여부 판단

### 매월 확인
- [ ] 월간 보고서 분석
- [ ] 성과 저하 원인 분석
- [ ] 파라미터 대폭 조정 (필요 시)

---

## 🔗 참고 파일

- `backend/scanner.py`: 메인 스캔 로직
- `backend/market_analyzer.py`: 시장 분석 및 동적 조정
- `backend/config.py`: 설정 파일
- `backend/services/report_generator.py`: 성과 분석

---

## 💡 결론

**핵심 전략:**
1. **시장 상황 인식**: 강세/중립/약세 구분
2. **동적 조정**: 성과에 따른 실시간 파라미터 변경
3. **리스크 관리**: 위험도 높은 종목 사전 필터링
4. **지속적 모니터링**: 성과 추적 및 자동 경고

**10월 대응:**
- 즉시 파라미터 강화 적용
- 더 보수적인 필터링 기준
- 일일 성과 모니터링 강화

이를 통해 시장 추세 변화에 능동적으로 대응하고, 일관된 성과를 유지할 수 있습니다.



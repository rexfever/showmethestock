# 스캔 알고리즘 개선 계획

## 📊 현재 상황 분석

### 성과 데이터 (2025.10.27~29)
- **8점 종목**: 5개, 성공률 60%, 평균 수익률 -0.13%
- **6점 종목**: 2개, 성공률 100%, 평균 수익률 +1.90%
- **4점 종목**: 2개, 성공률 0%, 평균 수익률 -6.61%

### 문제점
1. **8점의 불안정성**: 최고 등급임에도 평균 마이너스 수익
2. **6점의 우수성**: 오히려 8점보다 안정적이고 수익성 높음
3. **점수 체계 왜곡**: 현재 가중치가 실제 성과와 불일치
4. **과매수 구간 진입**: RSI 필터링 부족으로 위험 종목 포함

## 🎯 개선 목표

### 핵심 목표
- **8점 성공률**: 60% → 75% 이상
- **8점 평균 수익률**: -0.13% → +2% 이상
- **전체 안정성**: 큰 손실(-5% 이하) 빈도 감소
- **선별성**: 일평균 추천 종목 4.8개 → 3개 이하

## 🔧 개선 방안

### 1단계: 즉시 개선 (이번 주)

#### 1.1 RSI 필터링 강화
```python
# 현재: 단순 모멘텀 체크
rsi_momentum = (cur.RSI_TEMA > cur.RSI_DEMA) or (abs(cur.RSI_TEMA - cur.RSI_DEMA) < 3 and cur.RSI_TEMA > 35)

# 개선: 과매수 구간 제외 + 상승 추세 확인
def improved_rsi_filter(cur, prev):
    # 과매수 구간 제외 (70 이상)
    if cur.RSI_TEMA > 70:
        return False
    
    # 기존 모멘텀 조건
    momentum = (cur.RSI_TEMA > cur.RSI_DEMA) or (abs(cur.RSI_TEMA - cur.RSI_DEMA) < 3 and cur.RSI_TEMA > 35)
    
    # RSI 상승 추세 확인
    rsi_trend_up = cur.RSI_TEMA > prev.RSI_TEMA
    
    return momentum and rsi_trend_up
```

#### 1.2 점수 가중치 재조정
```python
# 현재 가중치 (총 15점)
current_weights = {
    'cross': 3,      # 골든크로스
    'volume': 2,     # 거래량 급증
    'macd': 1,       # MACD 신호
    'rsi': 1,        # RSI 모멘텀
    'tema_slope': 2, # TEMA 기울기
    'dema_slope': 2, # DEMA 기울기
    'obv_slope': 2,  # OBV 기울기
    'above_cnt5': 2, # 연속 상승
}

# 개선 가중치 (총 12점)
improved_weights = {
    'cross': 2,      # 3→2 (과대평가 수정)
    'volume': 2,     # 유지
    'macd': 1,       # 유지
    'rsi': 2,        # 1→2 (중요도 증가)
    'tema_slope': 2, # 유지
    'dema_slope': 1, # 2→1 (중복성 감소)
    'obv_slope': 2,  # 유지
    'above_cnt5': 2, # 유지 (안정성 지표)
}
```

#### 1.3 등급 기준 조정
```python
# 현재: 8점=강한매수, 6점=매수후보, 4점=관심
# 개선: 10점=강한매수, 8점=매수후보, 6점=관심, 4점=관망

if score >= 10:
    label = "강한 매수"    # 새로운 최고 등급
elif score >= 8:
    label = "매수 후보"    # 기존 8점 → 매수후보로 격하
elif score >= 6:
    label = "관심"
elif score >= 4:
    label = "관망"
else:
    label = "제외"
```

### 2단계: 중기 개선 (다음 주)

#### 2.1 시장 상황 적응형 알고리즘
```python
def get_market_condition():
    # 코스피 최근 5일 변화율로 시장 상황 판단
    kospi_change = get_kospi_5day_change()
    
    if kospi_change > 2:
        return "BULL"      # 강세장
    elif kospi_change < -2:
        return "BEAR"      # 약세장
    else:
        return "NEUTRAL"   # 중립

def adjust_thresholds_by_market(market_condition):
    if market_condition == "BULL":
        return {
            'min_signals': 2,     # 완화 (기회 확대)
            'rsi_upper_limit': 75, # 완화
            'vol_mult': 1.5       # 완화
        }
    elif market_condition == "BEAR":
        return {
            'min_signals': 4,     # 강화 (선별 강화)
            'rsi_upper_limit': 65, # 강화
            'vol_mult': 2.0       # 강화
        }
    else:  # NEUTRAL
        return config.default_thresholds
```

#### 2.2 연속 손실 방지 필터
```python
def prevent_consecutive_losses(df):
    # 최근 3일 연속 하락 종목 제외
    recent_changes = df['close'].pct_change().tail(3)
    consecutive_declines = (recent_changes < 0).sum()
    
    if consecutive_declines >= 3:
        return False
    
    # 일일 변동률 10% 초과 종목 제외 (과도한 변동성)
    daily_volatility = abs(df.iloc[-1]['change_rate'])
    if daily_volatility > 10:
        return False
    
    return True
```

### 3단계: 장기 개선 (다음 달)

#### 3.1 백테스팅 시스템 구축
```python
def backtest_algorithm(start_date, end_date):
    results = []
    
    for date in date_range(start_date, end_date):
        # 해당 날짜 스캔 실행
        scan_results = run_scan(date)
        
        # 다음날 성과 계산
        next_day_performance = calculate_performance(scan_results, date + 1)
        
        results.append({
            'date': date,
            'recommendations': len(scan_results),
            'success_rate': next_day_performance['success_rate'],
            'avg_return': next_day_performance['avg_return']
        })
    
    return analyze_backtest_results(results)
```

#### 3.2 성과 기반 자동 최적화
```python
def auto_optimize_weights():
    # 최근 30일 성과 분석
    performance = analyze_recent_performance(days=30)
    
    # 성과가 좋은 지표의 가중치 증가
    for indicator, success_rate in performance.items():
        if success_rate > 0.75:
            increase_weight(indicator, 0.5)
        elif success_rate < 0.45:
            decrease_weight(indicator, 0.5)
    
    # 가중치 정규화 (총합 12점 유지)
    normalize_weights(target_sum=12)
```

## 📅 구현 일정

### Week 1 (2025.10.29 - 11.05)
- [x] 현재 알고리즘 분석 완료
- [ ] RSI 필터링 강화 구현
- [ ] 점수 가중치 재조정
- [ ] 등급 기준 조정
- [ ] 테스트 및 검증

### Week 2 (2025.11.06 - 11.12)
- [ ] 시장 상황 적응형 로직 구현
- [ ] 연속 손실 방지 필터 추가
- [ ] 실시간 모니터링 시스템 구축
- [ ] A/B 테스트 시작

### Week 3-4 (2025.11.13 - 11.26)
- [ ] 백테스팅 시스템 구축
- [ ] 성과 기반 최적화 시스템 개발
- [ ] 머신러닝 모델 연구
- [ ] 최종 검증 및 배포

## 🎯 성공 지표

### 단기 목표 (1개월)
- **8점 성공률**: 75% 이상
- **8점 평균 수익률**: +2% 이상
- **큰 손실 빈도**: 월 1회 이하 (-5% 이상 손실)
- **일평균 추천**: 3개 이하

### 중기 목표 (3개월)
- **전체 성공률**: 70% 이상
- **평균 수익률**: +3% 이상
- **샤프 비율**: 1.5 이상
- **최대 낙폭**: -3% 이하

## 🔍 모니터링 계획

### 일일 모니터링
- 추천 종목 수 및 점수 분포
- 당일 성과 (수익률, 성공률)
- 알고리즘 오류 및 예외 상황

### 주간 리뷰
- 주간 성과 분석
- 알고리즘 파라미터 조정 필요성 검토
- 시장 상황 변화 대응

### 월간 평가
- 월간 성과 종합 분석
- 백테스팅 결과와 실제 성과 비교
- 알고리즘 개선 방향 수립

## 🚨 리스크 관리

### 기술적 리스크
- **알고리즘 오류**: 단계별 테스트 및 검증
- **데이터 품질**: 실시간 데이터 검증 시스템
- **시스템 장애**: 백업 시스템 및 롤백 계획

### 투자 리스크
- **과최적화**: 백테스팅 기간 다양화
- **시장 변화**: 적응형 알고리즘으로 대응
- **블랙스완**: 비상 상황 대응 매뉴얼

## 📋 체크리스트

### 개발 완료 체크
- [ ] RSI 필터링 강화 코드 구현
- [ ] 점수 가중치 재조정 적용
- [ ] 등급 기준 변경 반영
- [ ] 시장 상황 적응형 로직 구현
- [ ] 백테스팅 시스템 구축
- [ ] 모니터링 대시보드 구축

### 테스트 완료 체크
- [ ] 단위 테스트 통과
- [ ] 통합 테스트 통과
- [ ] 성능 테스트 통과
- [ ] 백테스팅 검증 완료
- [ ] A/B 테스트 결과 분석

### 배포 준비 체크
- [ ] 프로덕션 환경 테스트
- [ ] 롤백 계획 수립
- [ ] 모니터링 알림 설정
- [ ] 문서화 완료
- [ ] 팀 교육 완료

---

**작성일**: 2025.10.29  
**작성자**: AI Assistant  
**버전**: 1.0  
**다음 리뷰**: 2025.11.05
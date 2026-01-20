# 당일 급락 감지 문제 해결 방법

**작성일**: 2025-11-29  
**문제**: pykrx는 실시간이 아니어서 당일 급락을 캐치하지 못함

---

## 🔍 문제 상황

### 시나리오

**장중 14:00에 KOSPI가 -3% 급락 발생**

현재 시스템:
- 레짐 분석: pykrx/FinanceDataReader 사용
- pykrx: 장 마감 후(15:30)에만 데이터 제공
- 결과: 14:00 급락을 15:30 이후에야 감지
- 문제: ❌ 실시간 급락 감지 불가능

### 영향

1. **Risk Score 계산 지연**
   - `intraday_drop` 계산이 장 마감 후에만 가능
   - 장중 급락을 즉시 반영하지 못함

2. **crash 레짐 판단 지연**
   - 급락장 판단이 장 마감 후에만 가능
   - 사용자에게 위험 상황 알림 지연

3. **스캐너 추천 종목 수 조정 지연**
   - 급락장에서는 추천 종목 수를 줄여야 함
   - 조정이 지연됨

---

## 💡 해결 방법

### 방법 1: 하이브리드 접근 (권장) ⭐

**원칙**:
- **Trend Score (R20/R60)**: pykrx 일봉 데이터 사용 (정확도 우선)
- **Risk Score (intraday_drop)**: 키움 API 실시간 데이터 사용 (실시간성 우선)

**구현**:

```python
def analyze_regime_v4_enhanced(date: str) -> Dict[str, Any]:
    """레짐 v4 분석 (실시간 데이터 보강)"""
    
    # 1. 기본 레짐 분석 (일봉 데이터)
    v4_result = analyze_regime_v4(date)  # pykrx 사용
    
    # 2. 실시간 데이터로 intraday_drop 보정
    if is_market_hours():  # 장중인 경우
        realtime_df = get_realtime_kospi_data(date)  # 키움 API ETF
        if realtime_df is not None:
            realtime_intraday_drop = compute_intraday_drop_realtime(realtime_df)
            
            # 기존 값보다 낮으면 업데이트 (더 보수적)
            existing_drop = v4_result["kr_risk_features"]["intraday_drop"]
            if realtime_intraday_drop < existing_drop:
                v4_result["kr_risk_features"]["intraday_drop"] = realtime_intraday_drop
                
                # Risk Score 재계산
                kr_risk_score, _ = compute_kr_risk_score(v4_result["kr_risk_features"])
                v4_result["kr_risk_score"] = kr_risk_score
                
                # 급락장 재판단
                if realtime_intraday_drop <= -0.025:
                    v4_result["final_regime"] = "crash"
    
    return v4_result
```

**장점**:
- ✅ Trend Score는 정확한 지수 데이터 사용
- ✅ Risk Score는 실시간 데이터 사용
- ✅ 당일 급락 즉시 감지

**단점**:
- ⚠️ ETF 데이터 사용 (지수 대신)
- ⚠️ ETF와 지수의 intraday_drop 차이 가능

### 방법 2: 키움 API 우선 사용 (장중)

**원칙**:
- 장중: 키움 API ETF 사용 (실시간)
- 장 마감 후: pykrx 일봉 데이터 사용 (정확도)

**구현**:

```python
def load_full_data_hybrid(date: str) -> Dict[str, pd.DataFrame]:
    """하이브리드 데이터 로드"""
    from datetime import datetime
    import pytz
    
    KST = pytz.timezone('Asia/Seoul')
    now = datetime.now(KST)
    hour = now.hour
    
    target_date = pd.to_datetime(date, format='%Y%m%d')
    
    # 장중 (09:00 ~ 15:30): 키움 API 사용
    if 9 <= hour < 15.5:
        from kiwoom_api import api
        kospi_df = api.get_ohlcv("069500", 365, date)  # 실시간 데이터
        logger.info("장중: 키움 API ETF 데이터 사용 (실시간)")
    else:
        # 장 마감 후: pykrx 일봉 데이터 사용
        from pykrx import stock
        kospi_df = stock.get_index_ohlcv_by_date(
            (target_date - pd.Timedelta(days=365)).strftime('%Y%m%d'),
            target_date.strftime('%Y%m%d'),
            "1001"
        )
        logger.info("장 마감 후: pykrx 지수 데이터 사용 (정확도)")
    
    return {"KOSPI": kospi_df, ...}
```

**장점**:
- ✅ 장중 실시간 감지
- ✅ 장 마감 후 정확한 데이터

**단점**:
- ⚠️ 데이터 소스 전환 시 일관성 문제
- ⚠️ ETF와 지수의 차이

### 방법 3: 실시간 모니터링 서비스 추가

**원칙**:
- 레짐 분석은 일봉 데이터 사용 (기존 유지)
- 별도 실시간 모니터링 서비스 추가
- 급락 감지 시 알림 및 레짐 업데이트

**구현**:

```python
class RealtimeCrashMonitor:
    """실시간 급락 모니터링"""
    
    def monitor(self):
        """장중 실시간 모니터링"""
        while is_market_hours():
            df = get_realtime_kospi_data()
            intraday_drop = compute_intraday_drop_realtime(df)
            
            if intraday_drop <= -0.025:
                logger.warning(f"🔴 급락 감지: {intraday_drop*100:.2f}%")
                # 레짐 업데이트
                update_regime_to_crash()
                # 알림 발송
                send_alert()
            
            time.sleep(60)  # 1분마다 체크
```

---

## 🎯 권장 해결 방법

### 하이브리드 접근 (방법 1) ⭐

**이유**:
1. Trend Score는 중장기 추세이므로 일봉 데이터로 충분
2. Risk Score는 단기 리스크이므로 실시간 데이터 필요
3. 기존 시스템과 호환성 유지

**구현 위치**:
- `scanner_v2/regime_v4.py`의 `analyze_regime_v4()` 함수 수정
- `load_full_data()` 함수에 실시간 데이터 옵션 추가

**수정 사항**:
1. `compute_kr_risk_features()` 함수 수정
   - 일봉 데이터로 기본 계산
   - 장중인 경우 키움 API로 보정

2. `analyze_regime_v4()` 함수 수정
   - 실시간 데이터 확인
   - intraday_drop 보정
   - Risk Score 재계산

---

## 📝 구현 예시

```python
def compute_kr_risk_features_enhanced(df: pd.DataFrame, date: str = None) -> Dict[str, float]:
    """한국 Risk Feature 계산 (실시간 데이터 보강)"""
    
    # 기본 계산 (일봉 데이터)
    features = compute_kr_risk_features(df)
    
    # 장중인 경우 실시간 데이터로 보정
    if date and is_market_hours():
        realtime_df = get_realtime_kospi_data(date)
        if realtime_df is not None:
            realtime_intraday_drop = compute_intraday_drop_realtime(realtime_df)
            
            # 더 낮은 값 사용 (더 보수적)
            if realtime_intraday_drop < features["intraday_drop"]:
                features["intraday_drop"] = realtime_intraday_drop
                logger.info(f"실시간 intraday_drop 보정: {realtime_intraday_drop*100:.2f}%")
    
    return features
```

---

## ✅ 결론

**문제**: pykrx는 실시간이 아니어서 당일 급락을 캐치하지 못함

**해결**: 하이브리드 접근
- Trend Score: pykrx 일봉 데이터 (정확도)
- Risk Score: 키움 API 실시간 데이터 (실시간성)

**효과**:
- ✅ 당일 급락 즉시 감지
- ✅ crash 레짐 즉시 판단
- ✅ 사용자에게 위험 상황 즉시 알림


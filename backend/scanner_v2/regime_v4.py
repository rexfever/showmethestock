"""
Global Regime Analyzer v4
풀 히스토리 기반 중기(20·60·120일) 레짐 분석기
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

def compute_kr_trend_features(kospi_df: pd.DataFrame, kosdaq_df: pd.DataFrame = None) -> Dict[str, float]:
    """한국 Trend Feature 계산 (KOSPI + KOSDAQ)"""
    # KOSPI 기본 feature 계산
    kospi_features = _compute_single_market_features(kospi_df)
    
    # KOSDAQ feature 계산
    kosdaq_features = _compute_single_market_features(kosdaq_df if kosdaq_df is not None else pd.DataFrame())
    
    # 통합 feature (KOSPI 우선, 없으면 KOSDAQ)
    if not kospi_df.empty:
        base_features = kospi_features
    elif kosdaq_df is not None and not kosdaq_df.empty:
        base_features = kosdaq_features
    else:
        base_features = {
            "R5": 0.0, "R20": 0.0, "R60": 0.0,
            "DD20": 0.0, "DD60": 0.0,
            "MA20_SLOPE": 0.0, "MA60_SLOPE": 0.0
        }
    
    # KOSPI와 KOSDAQ 개별 feature 추가
    return {
        **base_features,
        "KOSPI_R20": kospi_features.get("R20", 0.0),
        "KOSPI_R60": kospi_features.get("R60", 0.0),
        "KOSDAQ_R20": kosdaq_features.get("R20", 0.0),
        "KOSDAQ_R60": kosdaq_features.get("R60", 0.0),
    }

def _compute_single_market_features(df: pd.DataFrame) -> Dict[str, float]:
    """단일 시장(KOSPI 또는 KOSDAQ)의 Feature 계산"""
    if df.empty or len(df) < 65:
        return {
            "R5": 0.0, "R20": 0.0, "R60": 0.0,
            "DD20": 0.0, "DD60": 0.0,
            "MA20_SLOPE": 0.0, "MA60_SLOPE": 0.0
        }
    
    close = df['close'].values
    
    # 수익률 계산 (원본 데이터 그대로 사용, 보정 없음)
    R5 = (close[-1] / close[-6] - 1) if len(close) >= 6 else 0.0
    R20 = (close[-1] / close[-21] - 1) if len(close) >= 21 else 0.0
    R60 = (close[-1] / close[-61] - 1) if len(close) >= 61 else 0.0
    
    # 드로우다운 계산
    if len(close) >= 21:
        peak_20 = np.max(close[-21:])
        DD20 = (close[-1] / peak_20 - 1) if peak_20 > 0 else 0.0
    else:
        DD20 = 0.0
    
    if len(close) >= 61:
        peak_60 = np.max(close[-61:])
        DD60 = (close[-1] / peak_60 - 1) if peak_60 > 0 else 0.0
    else:
        DD60 = 0.0
    
    # 이동평균 기울기 (최근 5일 기준)
    if len(close) >= 25:
        ma20 = pd.Series(close).rolling(20).mean().values
        MA20_SLOPE = (ma20[-1] - ma20[-6]) / ma20[-6] if ma20[-6] > 0 else 0.0
    else:
        MA20_SLOPE = 0.0
    
    if len(close) >= 65:
        ma60 = pd.Series(close).rolling(60).mean().values
        MA60_SLOPE = (ma60[-1] - ma60[-6]) / ma60[-6] if ma60[-6] > 0 else 0.0
    else:
        MA60_SLOPE = 0.0
    
    return {
        "R5": R5, "R20": R20, "R60": R60,
        "DD20": DD20, "DD60": DD60,
        "MA20_SLOPE": MA20_SLOPE, "MA60_SLOPE": MA60_SLOPE
    }

def compute_kr_risk_features(df: pd.DataFrame, date: str = None) -> Dict[str, float]:
    """한국 Risk Feature 계산 (실시간 데이터 보강)"""
    if df.empty:
        return {"intraday_drop": 0.0, "r3": 0.0, "day_range": 0.0}
    
    last_row = df.iloc[-1]
    
    # intraday drop (일봉 데이터)
    intraday_drop = (last_row['low'] / last_row['open'] - 1) if last_row['open'] > 0 else 0.0
    
    # 장중인 경우 실시간 데이터로 보정
    if date:
        try:
            from datetime import datetime
            import pytz
            from kiwoom_api import api
            from main import is_trading_day
            
            KST = pytz.timezone('Asia/Seoul')
            now = datetime.now(KST)
            hour = now.hour
            minute = now.minute
            
            # 장중 (09:00 ~ 15:30)이고 거래일인 경우
            if (9 <= hour < 15 or (hour == 15 and minute <= 30)) and is_trading_day(date):
                # 키움 API로 실시간 ETF 데이터 가져오기
                realtime_df = api.get_ohlcv("069500", 2, date)
                if realtime_df is not None and not realtime_df.empty and len(realtime_df) >= 1:
                    realtime_row = realtime_df.iloc[-1]
                    if 'open' in realtime_row and 'low' in realtime_row and realtime_row['open'] > 0:
                        realtime_intraday_drop = (realtime_row['low'] / realtime_row['open'] - 1)
                        
                        # 더 낮은 값 사용 (더 보수적, 급락 우선 감지)
                        if realtime_intraday_drop < intraday_drop:
                            logger.info(f"⚠️ 실시간 급락 감지: intraday_drop {realtime_intraday_drop*100:.2f}% (일봉: {intraday_drop*100:.2f}%)")
                            intraday_drop = realtime_intraday_drop
        except Exception as e:
            logger.debug(f"실시간 데이터 보정 실패 (무시): {e}")
    
    # 3일 수익률
    r3 = (last_row['close'] / df.iloc[-4]['close'] - 1) if len(df) >= 4 and df.iloc[-4]['close'] > 0 else 0.0
    
    # 일중 변동폭
    day_range = (last_row['high'] / last_row['low'] - 1) if last_row['low'] > 0 else 0.0
    
    return {
        "intraday_drop": intraday_drop,
        "r3": r3,
        "day_range": day_range
    }

def compute_us_trend_features(spy_df: pd.DataFrame, qqq_df: pd.DataFrame) -> Dict[str, float]:
    """미국 Trend Feature 계산"""
    features = {"SPY_R20": 0.0, "SPY_R60": 0.0, "QQQ_R20": 0.0, "QQQ_R60": 0.0, "SPY_MA50_ABOVE_200": 0, "QQQ_MA50_ABOVE_200": 0}
    
    # SPY
    if not spy_df.empty and len(spy_df) >= 61:
        spy_close = spy_df['close'].values
        features["SPY_R20"] = (spy_close[-1] / spy_close[-21] - 1) if len(spy_close) >= 21 else 0.0
        features["SPY_R60"] = (spy_close[-1] / spy_close[-61] - 1) if len(spy_close) >= 61 else 0.0
        
        if len(spy_close) >= 200:
            ma50 = pd.Series(spy_close).rolling(50).mean().iloc[-1]
            ma200 = pd.Series(spy_close).rolling(200).mean().iloc[-1]
            features["SPY_MA50_ABOVE_200"] = 1 if ma50 > ma200 else 0
    
    # QQQ
    if not qqq_df.empty and len(qqq_df) >= 61:
        qqq_close = qqq_df['close'].values
        features["QQQ_R20"] = (qqq_close[-1] / qqq_close[-21] - 1) if len(qqq_close) >= 21 else 0.0
        features["QQQ_R60"] = (qqq_close[-1] / qqq_close[-61] - 1) if len(qqq_close) >= 61 else 0.0
        
        if len(qqq_close) >= 200:
            ma50 = pd.Series(qqq_close).rolling(50).mean().iloc[-1]
            ma200 = pd.Series(qqq_close).rolling(200).mean().iloc[-1]
            features["QQQ_MA50_ABOVE_200"] = 1 if ma50 > ma200 else 0
    
    return features

def compute_us_risk_features(vix_df: pd.DataFrame) -> Dict[str, float]:
    """미국 Risk Feature 계산"""
    if vix_df.empty:
        return {"VIX_LEVEL": 20.0, "VIX_MA5": 20.0, "VIX_MA20": 20.0, "VIX_CHG_3D": 0.0}
    
    vix_close = vix_df['close'].values
    
    VIX_LEVEL = vix_close[-1]
    VIX_MA5 = pd.Series(vix_close).rolling(5).mean().iloc[-1] if len(vix_close) >= 5 else VIX_LEVEL
    VIX_MA20 = pd.Series(vix_close).rolling(20).mean().iloc[-1] if len(vix_close) >= 20 else VIX_LEVEL
    VIX_CHG_3D = (vix_close[-1] / vix_close[-4] - 1) if len(vix_close) >= 4 and vix_close[-4] > 0 else 0.0
    
    return {
        "VIX_LEVEL": VIX_LEVEL,
        "VIX_MA5": VIX_MA5,
        "VIX_MA20": VIX_MA20,
        "VIX_CHG_3D": VIX_CHG_3D
    }

def compute_kr_trend_score(feat: Dict[str, float]) -> float:
    """한국 Trend Score 계산 (KOSPI + KOSDAQ)"""
    score = 0.0
    
    # 기본 R20, R60 (KOSPI 우선 또는 KOSDAQ)
    if feat["R20"] > 0.04:
        score += 1.0
    elif feat["R20"] < -0.04:
        score -= 1.0
    
    if feat["R60"] > 0.08:
        score += 1.0
    elif feat["R60"] < -0.08:
        score -= 1.0
    
    # KOSDAQ 추가 고려 (KOSPI와 다를 수 있음)
    kosdaq_r20 = feat.get("KOSDAQ_R20", 0.0)
    kosdaq_r60 = feat.get("KOSDAQ_R60", 0.0)
    
    # KOSDAQ이 KOSPI와 반대 방향이면 가중치 조정
    if abs(kosdaq_r20) > 0.04:
        if kosdaq_r20 > 0.04:
            score += 0.5  # KOSDAQ도 상승
        elif kosdaq_r20 < -0.04:
            score -= 0.5  # KOSDAQ도 하락
    
    if abs(kosdaq_r60) > 0.08:
        if kosdaq_r60 > 0.08:
            score += 0.5
        elif kosdaq_r60 < -0.08:
            score -= 0.5
    
    # DD20 기준
    if feat["DD20"] < -0.05:
        score -= 1.0
    if feat["DD20"] < -0.10:
        score -= 1.0
    
    # DD60 기준
    if feat["DD60"] < -0.15:
        score -= 1.0
    
    # MA20_SLOPE 기준
    if feat["MA20_SLOPE"] > 0:
        score += 1.0
    
    # MA60_SLOPE 기준
    if feat["MA60_SLOPE"] > 0:
        score += 1.0
    elif feat["MA60_SLOPE"] < 0:
        score -= 0.5
    
    # 레짐 결정
    if score >= 2:
        regime = "bull"
    elif score <= -2:
        regime = "bear"
    else:
        regime = "neutral"
    
    return score, regime

def compute_us_trend_score(feat: Dict[str, float]) -> float:
    """미국 Trend Score 계산"""
    score = 0.0
    
    # SPY_R60 기준
    if feat["SPY_R60"] > 0.08:
        score += 1.0
    elif feat["SPY_R60"] < -0.08:
        score -= 1.0
    
    # QQQ_R60 기준
    if feat["QQQ_R60"] > 0.10:
        score += 1.0
    elif feat["QQQ_R60"] < -0.10:
        score -= 1.0
    
    # MA50_ABOVE_200 기준
    if feat["SPY_MA50_ABOVE_200"]:
        score += 0.5
    if feat["QQQ_MA50_ABOVE_200"]:
        score += 0.5
    
    # 레짐 결정
    if score >= 2:
        regime = "bull"
    elif score <= -2:
        regime = "bear"
    else:
        regime = "neutral"
    
    return score, regime

def compute_kr_risk_score(feat: Dict[str, float]) -> float:
    """한국 Risk Score 계산"""
    score = 0.0
    
    # intraday_drop 기준
    if feat["intraday_drop"] < -0.03:
        score -= 2.0
    
    # day_range 기준
    if feat["day_range"] > 0.04:
        score -= 1.0
    
    # r3 기준
    if feat["r3"] < -0.04:
        score -= 1.0
    
    # 레이블 결정
    if score <= -3:
        label = "stressed"
    elif score <= -1:
        label = "elevated"
    else:
        label = "normal"
    
    return score, label

def compute_us_risk_score(feat: Dict[str, float]) -> float:
    """미국 Risk Score 계산"""
    score = 0.0
    
    # VIX_CHG_3D 기준
    if feat["VIX_CHG_3D"] > 0.20:
        score -= 2.0
    
    # VIX_LEVEL 기준
    if feat["VIX_LEVEL"] > 25:
        score -= 1.0
    
    # 극단적 상황
    if feat["VIX_LEVEL"] > 35 or feat["VIX_CHG_3D"] > 0.30:
        score -= 3.0
    
    # 레이블 결정
    if score <= -3:
        label = "stressed"
    elif score <= -1:
        label = "elevated"
    else:
        label = "normal"
    
    return score, label

def combine_global_regime_v4(kr_trend: str, us_trend: str, kr_risk: str, us_risk: str, 
                           kr_trend_score: float, us_trend_score: float, 
                           kr_risk_score: float, us_risk_score: float) -> Dict[str, Any]:
    """Global Regime v4 결합 규칙"""
    
    # 가중 점수 계산
    global_trend_score = 0.4 * kr_trend_score + 0.6 * us_trend_score
    global_risk_score = 0.4 * kr_risk_score + 0.6 * us_risk_score
    
    # 글로벌 추세 결정
    if global_trend_score >= 2:
        global_trend = "bull"
    elif global_trend_score <= -2:
        global_trend = "bear"
    else:
        global_trend = "neutral"
    
    # 글로벌 리스크 결정
    if global_risk_score <= -3:
        global_risk = "stressed"
    elif global_risk_score <= -1:
        global_risk = "elevated"
    else:
        global_risk = "normal"
    
    # 최종 레짐 매핑
    if global_trend == "bull" and global_risk == "normal":
        final_regime = "bull"
    elif global_trend == "bear" and global_risk == "stressed":
        final_regime = "crash"
    elif global_trend == "neutral" and global_risk == "stressed":
        final_regime = "crash"
    elif global_trend == "bull" and global_risk == "elevated":
        final_regime = "neutral"
    else:
        final_regime = global_trend
    
    return {
        "global_trend_score": global_trend_score,
        "global_risk_score": global_risk_score,
        "global_trend": global_trend,
        "global_risk": global_risk,
        "final_regime": final_regime
    }

def load_full_data(date: str) -> Dict[str, pd.DataFrame]:
    """데이터 로드 (Chart API 사용 - us_futures_data_v8) - 날짜 필터링 포함"""
    import os
    
    # 날짜 파싱
    target_date = pd.to_datetime(date, format='%Y%m%d')
    
    # 한국 데이터 - 실제 KOSPI 지수 사용 (FinanceDataReader)
    kospi_df = pd.DataFrame()
    kosdaq_df = pd.DataFrame()
    try:
        # 실제 KOSPI 지수 데이터 (pykrx 우선, FinanceDataReader fallback)
        # pykrx는 한국거래소 공식 데이터로 정확도 높고 당일 데이터 제공 가능
        try:
            from utils.kospi_data_loader import get_kospi_data
            
            # 충분한 기간의 데이터 가져오기 (약 1년)
            date_str = target_date.strftime('%Y%m%d')
            kospi_df = get_kospi_data(date=date_str, days=365)
            
            if not kospi_df.empty:
                # 컬럼명 소문자로 통일
                kospi_df.columns = kospi_df.columns.str.lower()
                # 날짜 필터링: 해당 날짜까지의 데이터만 사용
                kospi_df = kospi_df[kospi_df.index <= target_date]
                
                # 데이터 검증: KOSPI 지수 범위 확인 (ETF 대체 사용 시에는 생략)
                try:
                    if not kospi_df.empty and kospi_df.attrs.get("source") != "etf":
                        kospi_recent = kospi_df.iloc[-1]['close']
                        # KOSPI 지수는 보통 2000~4000 범위
                        if not (2000 <= kospi_recent <= 4000):
                            logger.warning(f"KOSPI 지수 값이 비정상적: {kospi_recent:.2f} (예상 범위: 2000~4000)")
                        
                        # R20 계산하여 비정상적인 변동 확인 (20일 수익률)
                        if len(kospi_df) >= 21:
                            close_20d_ago = kospi_df.iloc[-21]['close']
                            latest_close = kospi_df.iloc[-1]['close']
                            r20 = (latest_close / close_20d_ago - 1) * 100
                            
                            # R20이 20% 이상이면 경고 (10%는 실제 시장에서도 흔함)
                            if abs(r20) > 20:
                                validation_date = target_date.strftime('%Y%m%d')
                                logger.warning(f"KOSPI R20이 비정상적으로 큼: {r20:.2f}% (날짜: {validation_date})")
                except Exception as e:
                    logger.debug(f"KOSPI 데이터 검증 실패 (무시): {e}")
                
                logger.debug(f"KOSPI 지수 데이터 로드: {len(kospi_df)}개 행")
        except Exception as e:
            logger.warning(f"KOSPI 지수 데이터 로드 실패: {e}")
            kospi_df = pd.DataFrame()
        
        # KOSDAQ 데이터 (CSV 캐시)
        kosdaq_csv = os.path.join(os.path.dirname(__file__), '..', '..', 'backend', 'data_cache', 'ohlcv', '229200.csv')
        if os.path.exists(kosdaq_csv):
            kosdaq_df = pd.read_csv(kosdaq_csv, index_col=0, parse_dates=True)
            # 컬럼명이 이미 소문자이므로 그대로 사용
            if 'date' in kosdaq_df.columns:
                kosdaq_df = kosdaq_df.drop(columns=['date'])
            # 날짜 필터링: 해당 날짜까지의 데이터만 사용
            if not kosdaq_df.empty:
                kosdaq_df = kosdaq_df[kosdaq_df.index <= target_date]
    except Exception:
        pass
    
    # KOSPI와 KOSDAQ을 합쳐서 KR 데이터로 사용
    kr_df = kospi_df if not kospi_df.empty else kosdaq_df
    
    # 미국 데이터 (Chart API 사용 - us_futures_data_v8)
    spy_df = pd.DataFrame()
    qqq_df = pd.DataFrame()
    vix_df = pd.DataFrame()
    
    try:
        from services.us_futures_data_v8 import us_futures_data_v8
        
        # SPY (Chart API로 데이터 가져오기)
        spy_df = us_futures_data_v8.fetch_data("SPY", period='1y')
        if not spy_df.empty:
            # 컬럼명 소문자로 통일 (기존 CSV와 동일한 형식)
            # 존재하는 컬럼만 변환 (KeyError 방지)
            rename_map = {}
            if 'Open' in spy_df.columns:
                rename_map['Open'] = 'open'
            if 'High' in spy_df.columns:
                rename_map['High'] = 'high'
            if 'Low' in spy_df.columns:
                rename_map['Low'] = 'low'
            if 'Close' in spy_df.columns:
                rename_map['Close'] = 'close'
            if 'Volume' in spy_df.columns:
                rename_map['Volume'] = 'volume'
            if rename_map:
                spy_df = spy_df.rename(columns=rename_map)
            # 날짜 필터링 (DatetimeIndex 확인)
            if isinstance(spy_df.index, pd.DatetimeIndex):
                spy_df = spy_df[spy_df.index <= target_date]
        
        # QQQ (Chart API로 데이터 가져오기)
        qqq_df = us_futures_data_v8.fetch_data("QQQ", period='1y')
        if not qqq_df.empty:
            # 컬럼명 소문자로 통일
            rename_map = {}
            if 'Open' in qqq_df.columns:
                rename_map['Open'] = 'open'
            if 'High' in qqq_df.columns:
                rename_map['High'] = 'high'
            if 'Low' in qqq_df.columns:
                rename_map['Low'] = 'low'
            if 'Close' in qqq_df.columns:
                rename_map['Close'] = 'close'
            if 'Volume' in qqq_df.columns:
                rename_map['Volume'] = 'volume'
            if rename_map:
                qqq_df = qqq_df.rename(columns=rename_map)
            # 날짜 필터링
            if isinstance(qqq_df.index, pd.DatetimeIndex):
                qqq_df = qqq_df[qqq_df.index <= target_date]
        
        # VIX (Chart API로 데이터 가져오기)
        vix_df = us_futures_data_v8.fetch_data("^VIX", period='1y')
        if not vix_df.empty:
            # 컬럼명 소문자로 통일
            rename_map = {}
            if 'Open' in vix_df.columns:
                rename_map['Open'] = 'open'
            if 'High' in vix_df.columns:
                rename_map['High'] = 'high'
            if 'Low' in vix_df.columns:
                rename_map['Low'] = 'low'
            if 'Close' in vix_df.columns:
                rename_map['Close'] = 'close'
            if 'Volume' in vix_df.columns:
                rename_map['Volume'] = 'volume'
            if rename_map:
                vix_df = vix_df.rename(columns=rename_map)
            # 날짜 필터링
            if isinstance(vix_df.index, pd.DatetimeIndex):
                vix_df = vix_df[vix_df.index <= target_date]
    except Exception as e:
        logger.warning(f"미국 데이터 로드 실패 (Chart API): {e}, CSV 캐시로 fallback")
        # Fallback: CSV 캐시 직접 읽기
        try:
            cache_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'cache', 'us_futures')
            
            # SPY
            spy_path = os.path.join(cache_dir, 'SPY.csv')
            if os.path.exists(spy_path):
                spy_df = pd.read_csv(spy_path, index_col=0, parse_dates=True)
                spy_df = spy_df.rename(columns={'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'})
                if not spy_df.empty:
                    spy_df = spy_df[spy_df.index <= target_date]
            
            # QQQ
            qqq_path = os.path.join(cache_dir, 'QQQ.csv')
            if os.path.exists(qqq_path):
                qqq_df = pd.read_csv(qqq_path, index_col=0, parse_dates=True)
                qqq_df = qqq_df.rename(columns={'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'})
                if not qqq_df.empty:
                    qqq_df = qqq_df[qqq_df.index <= target_date]
            
            # VIX
            vix_path = os.path.join(cache_dir, '^VIX.csv')
            if os.path.exists(vix_path):
                vix_df = pd.read_csv(vix_path, index_col=0, parse_dates=True)
                vix_df = vix_df.rename(columns={'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'})
                if not vix_df.empty:
                    vix_df = vix_df[vix_df.index <= target_date]
        except Exception:
            pass
    
    return {
        "KR": kr_df,
        "KOSPI": kospi_df,
        "KOSDAQ": kosdaq_df,
        "SPY": spy_df,
        "QQQ": qqq_df,
        "VIX": vix_df
    }

def analyze_regime_v4(date: str) -> Dict[str, Any]:
    """Regime Analyzer v4 메인 함수"""
    try:
        # 1. 데이터 로딩
        data = load_full_data(date)
        
        # 2. Feature 계산
        kr_trend_feat = compute_kr_trend_features(data["KOSPI"], data["KOSDAQ"])
        # KR 데이터는 KOSPI 우선, 없으면 KOSDAQ
        kr_data = data["KOSPI"] if not data["KOSPI"].empty else data["KOSDAQ"]
        kr_risk_feat = compute_kr_risk_features(kr_data, date)  # date 전달하여 실시간 보정
        us_trend_feat = compute_us_trend_features(data["SPY"], data["QQQ"])
        us_risk_feat = compute_us_risk_features(data["VIX"])
        
        # 3. Score 계산
        kr_trend_score, kr_trend_regime = compute_kr_trend_score(kr_trend_feat)
        us_trend_score, us_trend_regime = compute_us_trend_score(us_trend_feat)
        kr_risk_score, kr_risk_label = compute_kr_risk_score(kr_risk_feat)
        us_risk_score, us_risk_label = compute_us_risk_score(us_risk_feat)
        
        # 4. Global Regime 계산
        global_result = combine_global_regime_v4(
            kr_trend_regime, us_trend_regime, kr_risk_label, us_risk_label,
            kr_trend_score, us_trend_score, kr_risk_score, us_risk_score
        )
        
        # 5. 결과 조합
        result = {
            "date": date,
            "final_regime": global_result["final_regime"],
            "final_score": global_result["global_trend_score"],
            "global_trend_score": global_result["global_trend_score"],
            "global_risk_score": global_result["global_risk_score"],
            "kr_trend_score": kr_trend_score,
            "us_trend_score": us_trend_score,
            "kr_risk_score": kr_risk_score,
            "us_risk_score": us_risk_score,
            "kr_regime": kr_trend_regime,
            "us_prev_regime": us_trend_regime,
            "kr_risk_label": kr_risk_label,
            "us_risk_label": us_risk_label,
            "kr_trend_features": kr_trend_feat,
            "kr_risk_features": kr_risk_feat,
            "us_trend_features": us_trend_feat,
            "us_risk_features": us_risk_feat
        }
        
        # logger.info(f"Regime v4 분석 완료: {date} -> {result['final_regime']} (trend: {result['global_trend_score']:.2f}, risk: {result['global_risk_score']:.2f})")
        
        return result
        
    except Exception as e:
        # logger.error(f"Regime v4 분석 실패: {e}")
        return {
            "date": date,
            "final_regime": "neutral",
            "final_score": 0.0,
            "global_trend_score": 0.0,
            "global_risk_score": 0.0,
            "kr_trend_score": 0.0,
            "us_trend_score": 0.0,
            "kr_risk_score": 0.0,
            "us_risk_score": 0.0,
            "kr_regime": "neutral",
            "us_prev_regime": "neutral",
            "kr_risk_label": "normal",
            "us_risk_label": "normal"
        }

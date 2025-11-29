#!/usr/bin/env python3
"""
당일 급락 감지 개선 스크립트
- Trend Score (R20/R60): pykrx 일봉 데이터 사용
- Risk Score (intraday_drop): 키움 API 실시간 데이터 사용
"""
import pandas as pd
from datetime import datetime
import logging
from typing import Dict, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_realtime_kospi_data(date: str = None) -> Optional[pd.DataFrame]:
    """실시간 KOSPI 데이터 가져오기 (키움 API ETF 사용)"""
    try:
        from kiwoom_api import api
        from main import is_trading_day
        
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
        
        # 거래일 체크
        if not is_trading_day(date):
            return None
        
        # 키움 API로 ETF 데이터 가져오기 (실시간 가능)
        # 주의: ETF는 지수가 아니지만, 실시간 모니터링용으로 사용
        df = api.get_ohlcv("069500", 5, date)
        
        if df.empty or len(df) < 2:
            return None
        
        return df
    except Exception as e:
        logger.warning(f"실시간 KOSPI 데이터 가져오기 실패: {e}")
        return None

def compute_intraday_drop_realtime(df: pd.DataFrame) -> float:
    """실시간 intraday_drop 계산"""
    if df.empty or len(df) < 1:
        return 0.0
    
    last_row = df.iloc[-1]
    
    # intraday_drop = (저가 / 시가 - 1)
    if 'open' in last_row and 'low' in last_row:
        if last_row['open'] > 0:
            return (last_row['low'] / last_row['open'] - 1)
    
    return 0.0

def enhance_regime_v4_with_realtime(date: str = None) -> Dict[str, Any]:
    """레짐 v4 분석에 실시간 데이터 추가"""
    try:
        from scanner_v2.regime_v4 import analyze_regime_v4
        
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
        
        # 기본 레짐 분석 (일봉 데이터 사용)
        v4_result = analyze_regime_v4(date)
        
        # 실시간 데이터로 intraday_drop 보정
        realtime_df = get_realtime_kospi_data(date)
        
        if realtime_df is not None and not realtime_df.empty:
            # 실시간 intraday_drop 계산
            realtime_intraday_drop = compute_intraday_drop_realtime(realtime_df)
            
            # 기존 intraday_drop과 비교하여 더 낮은 값 사용 (더 보수적)
            existing_intraday_drop = v4_result.get("kr_risk_features", {}).get("intraday_drop", 0.0)
            
            if realtime_intraday_drop < existing_intraday_drop:
                logger.info(f"⚠️ 실시간 급락 감지: intraday_drop {realtime_intraday_drop*100:.2f}% (기존: {existing_intraday_drop*100:.2f}%)")
                
                # Risk Score 재계산
                from scanner_v2.regime_v4 import compute_kr_risk_score
                
                # Risk features 업데이트
                kr_risk_features = v4_result.get("kr_risk_features", {})
                kr_risk_features["intraday_drop"] = realtime_intraday_drop
                
                # Risk Score 재계산
                kr_risk_score, kr_risk_label = compute_kr_risk_score(kr_risk_features)
                
                # 결과 업데이트
                v4_result["kr_risk_score"] = kr_risk_score
                v4_result["kr_risk_features"]["intraday_drop"] = realtime_intraday_drop
                
                # 급락장 재판단
                if realtime_intraday_drop <= -0.025:
                    logger.warning(f"🔴 급락장 감지: intraday_drop {realtime_intraday_drop*100:.2f}%")
                    # crash 레짐으로 변경 가능
                    if v4_result.get("final_regime") != "crash":
                        logger.warning(f"레짐 변경: {v4_result.get('final_regime')} → crash")
                        v4_result["final_regime"] = "crash"
        
        return v4_result
        
    except Exception as e:
        logger.error(f"실시간 레짐 분석 실패: {e}")
        return {}

if __name__ == "__main__":
    date = datetime.now().strftime('%Y%m%d')
    result = enhance_regime_v4_with_realtime(date)
    print(f"레짐 분석 결과: {result.get('final_regime')}")
    print(f"intraday_drop: {result.get('kr_risk_features', {}).get('intraday_drop', 0)*100:.2f}%")


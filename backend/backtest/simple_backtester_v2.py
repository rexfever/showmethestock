"""
Simple Backtester v2

Scanner v2 + Regime v4 기반 백테스트
- 종가 매수 → 다음날 시초가 매도
- 동일 비중
- 거래비용 0.05% 반영
- horizon별 성과 계산 (swing/position/longterm)
- crash 구간에서는 longterm만 테스트

사용법:
    from backtest.simple_backtester_v2 import run_simple_backtest
    result = run_simple_backtest('20250701', '20250930')
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import logging
import pandas as pd
import numpy as np

from db_manager import db_manager
from main import is_trading_day
from market_analyzer import market_analyzer
from scanner_factory import scan_with_scanner
from kiwoom_api import api
from config import config

logger = logging.getLogger(__name__)

# 거래비용
TRADING_COST = 0.0005  # 0.05%


def _get_trading_days(start_date: str, end_date: str) -> List[str]:
    """거래일 목록 생성"""
    start = datetime.strptime(start_date, '%Y%m%d')
    end = datetime.strptime(end_date, '%Y%m%d')
    trading_days = []
    current = start
    while current <= end:
        date_str = current.strftime('%Y%m%d')
        if is_trading_day(date_str):
            trading_days.append(date_str)
        current += timedelta(days=1)
    return trading_days


def _get_next_trading_day(date: str) -> Optional[str]:
    """다음 거래일 반환"""
    current = datetime.strptime(date, '%Y%m%d')
    for i in range(1, 10):  # 최대 10일 후까지
        next_date = current + timedelta(days=i)
        date_str = next_date.strftime('%Y%m%d')
        if is_trading_day(date_str):
            return date_str
    return None


def _get_price_data(ticker: str, date: str, price_type: str = 'close') -> Optional[float]:
    """
    가격 데이터 조회
    
    Args:
        ticker: 종목 코드
        date: 날짜 (YYYYMMDD)
        price_type: 'close' (종가) 또는 'open' (시가)
    
    Returns:
        가격 또는 None
    """
    try:
        # 충분한 데이터 가져오기 (최근 데이터 포함)
        df = api.get_ohlcv(ticker, 5, date)
        if df.empty:
            return None
        
        # 날짜 기준으로 정렬 (오름차순)
        if 'date' in df.columns:
            df = df.sort_values('date')
        
        # date에 해당하는 행 찾기
        date_str = date.replace('-', '')
        
        # date 컬럼 처리
        if 'date' in df.columns:
            # date를 문자열로 변환하여 비교
            df['date_str'] = df['date'].astype(str).str.replace('-', '')
            df_filtered = df[df['date_str'] == date_str]
            
            if not df_filtered.empty:
                row = df_filtered.iloc[0]
            else:
                # 정확히 일치하는 날짜가 없으면 마지막 행 사용
                row = df.iloc[-1]
        else:
            # date 컬럼이 없으면 마지막 행 사용
            row = df.iloc[-1]
        
        if price_type == 'close':
            price = row.get('close') if hasattr(row, 'get') else row['close']
            return float(price) if price is not None else None
        elif price_type == 'open':
            price = row.get('open') if hasattr(row, 'get') else row['open']
            return float(price) if price is not None else None
        else:
            return None
    except Exception as e:
        logger.debug(f"가격 데이터 조회 실패 ({ticker}, {date}, {price_type}): {e}")
        return None


def _classify_horizon(result: Dict, market_condition, cutoffs: Dict) -> List[str]:
    """
    종목의 horizon 분류
    
    Returns:
        horizon 리스트 (['swing', 'position', 'longterm'] 중 하나 이상)
    """
    horizons = []
    score = result.get('score', 0)
    flags = result.get('flags', {})
    
    if isinstance(flags, dict):
        risk_score = flags.get('risk_score', 0)
    else:
        risk_score = 0
    
    # short_term_risk_score 가중 적용
    if market_condition:
        short_term_risk = getattr(market_condition, 'short_term_risk_score', None)
        if short_term_risk is not None:
            risk_score = (risk_score or 0) + short_term_risk
    
    effective_score = (score or 0) - (risk_score or 0)
    
    if effective_score >= cutoffs['swing']:
        horizons.append('swing')
    if effective_score >= cutoffs['position']:
        horizons.append('position')
    if effective_score >= cutoffs['longterm']:
        horizons.append('longterm')
    
    return horizons


def run_simple_backtest(start_date: str, end_date: str) -> Dict[str, Any]:
    """
    간단한 백테스트 실행
    
    Args:
        start_date: 시작일 (YYYYMMDD)
        end_date: 종료일 (YYYYMMDD)
    
    Returns:
        백테스트 결과 딕셔너리
    """
    logger.info(f"\n{'='*80}")
    logger.info(f"백테스트 시작: {start_date} ~ {end_date}")
    logger.info(f"{'='*80}")
    
    # 1. 거래일 목록
    trading_days = _get_trading_days(start_date, end_date)
    logger.info(f"📅 거래일: {len(trading_days)}일")
    
    # 2. 유니버스 구성
    try:
        kospi_universe = api.get_top_codes('KOSPI', 200)
        kosdaq_universe = api.get_top_codes('KOSDAQ', 200)
        universe = list(set(kospi_universe + kosdaq_universe))
        logger.info(f"📋 유니버스: {len(universe)}개")
    except Exception as e:
        logger.error(f"유니버스 구성 실패: {e}")
        return {'error': f'Universe construction failed: {e}'}
    
    # 3. horizon별 트레이드 수집
    trades = {'swing': [], 'position': [], 'longterm': []}
    
    from scanner_v2.config_regime import REGIME_CUTOFFS
    
    for i, date_str in enumerate(trading_days, 1):
        try:
            if i % 10 == 0:
                logger.info(f"  진행: {i}/{len(trading_days)} ({date_str})")
            
            # 시장 분석
            market_condition = market_analyzer.analyze_market_condition(date_str, regime_version='v4')
            
            # 레짐 확인
            midterm_regime = getattr(market_condition, 'midterm_regime', None) or \
                           getattr(market_condition, 'final_regime', 'neutral')
            
            # crash 구간에서는 longterm만 테스트
            if midterm_regime == 'crash':
                test_horizons = ['longterm']
            else:
                test_horizons = ['swing', 'position', 'longterm']
            
            # 스캔 실행
            scan_results = scan_with_scanner(
                universe_codes=universe,
                preset_overrides=None,
                base_date=date_str,
                market_condition=market_condition,
                version="v2"
            )
            
            if not scan_results:
                continue
            
            # cutoff 가져오기
            cutoffs = REGIME_CUTOFFS.get(midterm_regime, REGIME_CUTOFFS['neutral'])
            
            # 다음 거래일
            next_date = _get_next_trading_day(date_str)
            if not next_date:
                continue
            
            # 각 종목별 트레이드 생성
            for result in scan_results:
                ticker = result.get('ticker')
                if not ticker:
                    continue
                
                # horizon 분류
                horizons = _classify_horizon(result, market_condition, cutoffs)
                
                # 테스트할 horizon만 처리
                horizons = [h for h in horizons if h in test_horizons]
                
                if not horizons:
                    continue
                
                # 매수가 (종가)
                buy_price = _get_price_data(ticker, date_str, 'close')
                if not buy_price or buy_price <= 0:
                    continue
                
                # 매도가 (다음날 시가)
                sell_price = _get_price_data(ticker, next_date, 'open')
                if not sell_price or sell_price <= 0:
                    continue
                
                # 수익률 계산 (거래비용 반영)
                return_pct = (sell_price / buy_price - 1) - (TRADING_COST * 2)  # 매수/매도 각각
                
                # 각 horizon별로 트레이드 추가
                for horizon in horizons:
                    trades[horizon].append({
                        'date': date_str,
                        'ticker': ticker,
                        'name': result.get('name', ''),
                        'score': result.get('score', 0),
                        'buy_price': buy_price,
                        'sell_price': sell_price,
                        'return_pct': return_pct,
                    })
        
        except Exception as e:
            logger.warning(f"백테스트 오류 ({date_str}): {e}")
            continue
    
    # 4. horizon별 성과 계산
    horizon_results = {}
    
    for horizon in ['swing', 'position', 'longterm']:
        horizon_trades = trades[horizon]
        
        if not horizon_trades:
            horizon_results[horizon] = {
                'total_trades': 0,
                'win_rate': 0.0,
                'avg_return': 0.0,
                'total_return': 0.0,
                'cagr': 0.0,
                'mdd': 0.0,
            }
            continue
        
        returns = [t['return_pct'] for t in horizon_trades]
        returns_array = np.array(returns)
        
        # 승률
        win_count = sum(1 for r in returns if r > 0)
        win_rate = win_count / len(returns) if returns else 0.0
        
        # 평균 수익률
        avg_return = np.mean(returns_array)
        
        # 누적 수익률 (동일 비중)
        total_return = np.sum(returns_array) / len(returns_array)  # 일일 평균 수익률의 합
        
        # CAGR (연환산)
        days = len(trading_days)
        if days > 0:
            cagr = (1 + total_return) ** (252 / days) - 1  # 연간 거래일 252일 가정
        else:
            cagr = 0.0
        
        # MDD (최대 낙폭)
        cumulative = np.cumsum(returns_array)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = cumulative - running_max
        mdd = abs(np.min(drawdown)) if len(drawdown) > 0 else 0.0
        
        horizon_results[horizon] = {
            'total_trades': len(horizon_trades),
            'win_rate': float(win_rate),
            'avg_return': float(avg_return),
            'total_return': float(total_return),
            'cagr': float(cagr),
            'mdd': float(mdd),
        }
    
    # 5. 결과 출력
    logger.info(f"\n{'='*80}")
    logger.info("백테스트 결과")
    logger.info(f"{'='*80}")
    
    for horizon, stats in horizon_results.items():
        logger.info(f"\n📊 {horizon.upper()}:")
        logger.info(f"   - 총 트레이드: {stats['total_trades']}건")
        logger.info(f"   - 승률: {stats['win_rate']*100:.1f}%")
        logger.info(f"   - 평균 수익률: {stats['avg_return']*100:.2f}%")
        logger.info(f"   - 누적 수익률: {stats['total_return']*100:.2f}%")
        logger.info(f"   - CAGR: {stats['cagr']*100:.2f}%")
        logger.info(f"   - MDD: {stats['mdd']*100:.2f}%")
    
    return {
        'start_date': start_date,
        'end_date': end_date,
        'total_days': len(trading_days),
        'horizon_results': horizon_results,
        'trades': trades,
    }


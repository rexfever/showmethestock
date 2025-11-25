"""
Global Regime Model v3 백테스트 유틸리티
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import pandas as pd

logger = logging.getLogger(__name__)

def run_regime_backtest(start_date: str, end_date: str) -> dict:
    """
    Global Regime v3 백테스트 실행
    
    Args:
        start_date: 시작 날짜 (YYYYMMDD)
        end_date: 종료 날짜 (YYYYMMDD)
    
    Returns:
        백테스트 결과 딕셔너리
    """
    try:
        from services.regime_storage import load_regime, upsert_regime
        from market_analyzer import market_analyzer
        from kiwoom_api import api
        from main import is_trading_day
        
        # 날짜 범위 생성
        start_dt = datetime.strptime(start_date, '%Y%m%d')
        end_dt = datetime.strptime(end_date, '%Y%m%d')
        
        regime_data = []
        kospi_data = []
        
        current_dt = start_dt
        while current_dt <= end_dt:
            date_str = current_dt.strftime('%Y%m%d')
            
            # 거래일 체크
            try:
                if not is_trading_day(date_str):
                    current_dt += timedelta(days=1)
                    continue
            except Exception:
                # 거래일 체크 실패 시 주말 건너뛰기
                if current_dt.weekday() >= 5:  # 토요일(5), 일요일(6)
                    current_dt += timedelta(days=1)
                    continue
            
            # 장세 데이터 로드 또는 계산
            regime_result = load_regime(date_str)
            if regime_result is None:
                try:
                    # v3 분석 실행 후 저장
                    condition = market_analyzer.analyze_market_condition_v3(date_str, mode="backtest")
                    if condition.version == "regime_v3":
                        regime_result = {
                            'final_regime': condition.final_regime,
                            'kr_regime': condition.kr_regime,
                            'us_prev_regime': condition.us_prev_regime,
                            'final_score': condition.final_score,
                            'kr_score': condition.kr_score,
                            'us_prev_score': condition.us_prev_score
                        }
                        logger.info(f"장세 계산 완료: {date_str} -> {condition.final_regime}")
                    else:
                        logger.warning(f"v3 분석 실패, 건너뛰기: {date_str}")
                        current_dt += timedelta(days=1)
                        continue
                except Exception as e:
                    logger.error(f"장세 분석 실패 ({date_str}): {e}")
                    current_dt += timedelta(days=1)
                    continue
            
            # KOSPI200 수익률 가져오기
            try:
                df = api.get_ohlcv("069500", 2, date_str)  # KOSPI200 ETF
                if not df.empty and len(df) >= 2:
                    current_close = df.iloc[-1]['close']
                    prev_close = df.iloc[-2]['close']
                    kospi_return = (current_close / prev_close - 1) if prev_close > 0 else 0.0
                else:
                    kospi_return = 0.0
            except Exception:
                kospi_return = 0.0
            
            # 데이터 수집
            regime_data.append({
                'date': date_str,
                'final_regime': regime_result.get('final_regime', 'neutral'),
                'kr_regime': regime_result.get('kr_regime', 'neutral'),
                'us_prev_regime': regime_result.get('us_prev_regime', 'neutral'),
                'final_score': regime_result.get('final_score', 0.0),
                'kr_score': regime_result.get('kr_score', 0.0),
                'us_prev_score': regime_result.get('us_prev_score', 0.0)
            })
            
            kospi_data.append({
                'date': date_str,
                'return': kospi_return
            })
            
            current_dt += timedelta(days=1)
        
        # 분석 결과 계산
        if not regime_data:
            return {'error': '분석할 데이터가 없습니다'}
        
        df_regime = pd.DataFrame(regime_data)
        df_kospi = pd.DataFrame(kospi_data)
        
        # 레짐별 통계
        regime_stats = {}
        for regime in ['bull', 'neutral', 'bear', 'crash']:
            regime_mask = df_regime['final_regime'] == regime
            regime_days = regime_mask.sum()
            
            if regime_days > 0:
                # 해당 레짐 날짜들의 KOSPI 수익률
                regime_dates = df_regime[regime_mask]['date'].tolist()
                regime_returns = [df_kospi[df_kospi['date'] == d]['return'].iloc[0] 
                                for d in regime_dates if len(df_kospi[df_kospi['date'] == d]) > 0]
                
                if regime_returns:
                    regime_stats[regime] = {
                        'days': int(regime_days),
                        'avg_return': float(pd.Series(regime_returns).mean()),
                        'std_return': float(pd.Series(regime_returns).std()),
                        'total_return': float(pd.Series(regime_returns).sum()),
                        'win_rate': float((pd.Series(regime_returns) > 0).mean())
                    }
        
        # 전체 통계
        total_days = len(df_regime)
        total_returns = df_kospi['return'].tolist()
        
        result = {
            'period': f"{start_date} ~ {end_date}",
            'total_days': total_days,
            'regime_distribution': {
                regime: int((df_regime['final_regime'] == regime).sum()) 
                for regime in ['bull', 'neutral', 'bear', 'crash']
            },
            'regime_stats': regime_stats,
            'overall_stats': {
                'avg_return': float(pd.Series(total_returns).mean()) if total_returns else 0.0,
                'std_return': float(pd.Series(total_returns).std()) if total_returns else 0.0,
                'total_return': float(pd.Series(total_returns).sum()) if total_returns else 0.0,
                'win_rate': float((pd.Series(total_returns) > 0).mean()) if total_returns else 0.0
            }
        }
        
        # 콘솔 출력
        print(f"\n📊 Global Regime v3 백테스트 결과")
        print(f"기간: {start_date} ~ {end_date} ({total_days}일)")
        print(f"\n🎯 레짐 분포:")
        for regime, days in result['regime_distribution'].items():
            pct = (days / total_days * 100) if total_days > 0 else 0
            print(f"  {regime}: {days}일 ({pct:.1f}%)")
        
        print(f"\n📈 레짐별 성과:")
        for regime, stats in regime_stats.items():
            print(f"  {regime}: 평균 {stats['avg_return']*100:.2f}%, "
                  f"승률 {stats['win_rate']*100:.1f}%, "
                  f"누적 {stats['total_return']*100:.2f}%")
        
        overall = result['overall_stats']
        print(f"\n🏆 전체 성과: 평균 {overall['avg_return']*100:.2f}%, "
              f"승률 {overall['win_rate']*100:.1f}%, "
              f"누적 {overall['total_return']*100:.2f}%")
        
        return result
        
    except Exception as e:
        logger.error(f"백테스트 실행 실패: {e}")
        return {'error': str(e)}

def analyze_regime_transitions(start_date: str, end_date: str) -> dict:
    """
    레짐 전환 패턴 분석
    """
    try:
        from services.regime_storage import load_regime
        from main import is_trading_day
        
        start_dt = datetime.strptime(start_date, '%Y%m%d')
        end_dt = datetime.strptime(end_date, '%Y%m%d')
        
        regime_sequence = []
        current_dt = start_dt
        
        while current_dt <= end_dt:
            date_str = current_dt.strftime('%Y%m%d')
            
            try:
                if is_trading_day(date_str):
                    regime_result = load_regime(date_str)
                    if regime_result:
                        regime_sequence.append({
                            'date': date_str,
                            'regime': regime_result.get('final_regime', 'neutral')
                        })
            except Exception:
                pass
            
            current_dt += timedelta(days=1)
        
        if len(regime_sequence) < 2:
            return {'error': '분석할 데이터가 부족합니다'}
        
        # 전환 패턴 분석
        transitions = {}
        for i in range(len(regime_sequence) - 1):
            from_regime = regime_sequence[i]['regime']
            to_regime = regime_sequence[i + 1]['regime']
            
            if from_regime not in transitions:
                transitions[from_regime] = {}
            if to_regime not in transitions[from_regime]:
                transitions[from_regime][to_regime] = 0
            
            transitions[from_regime][to_regime] += 1
        
        print(f"\n🔄 레짐 전환 패턴 분석 ({len(regime_sequence)}일)")
        for from_regime, to_regimes in transitions.items():
            total = sum(to_regimes.values())
            print(f"\n{from_regime}에서:")
            for to_regime, count in to_regimes.items():
                pct = (count / total * 100) if total > 0 else 0
                print(f"  → {to_regime}: {count}회 ({pct:.1f}%)")
        
        return {
            'sequence_length': len(regime_sequence),
            'transitions': transitions
        }
        
    except Exception as e:
        logger.error(f"전환 패턴 분석 실패: {e}")
        return {'error': str(e)}
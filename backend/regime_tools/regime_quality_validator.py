"""
Regime Quality Validator

레짐 품질 검증 도구
- midterm_regime과 실제 시장의 5~20일 수익률 상관관계 검증
- 각 날짜별 KOSPI 5/10/20일 수익률과 midterm_regime의 매칭률 분석
- crash/bear/bull/neutral별 성과 분포 출력

사용법:
    from regime_tools.regime_quality_validator import analyze_regime_quality
    result = analyze_regime_quality('20250701', '20250930')
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import json
import logging
import pandas as pd
import numpy as np

from db_manager import db_manager
from main import is_trading_day

logger = logging.getLogger(__name__)


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


def _get_kospi_returns(date: str, days: int) -> Optional[float]:
    """KOSPI N일 수익률 계산"""
    try:
        from kiwoom_api import api
        
        # 필요한 데이터 개수 (days + 여유분)
        lookback = days + 5
        df = api.get_ohlcv("069500", lookback, date)
        
        if df.empty or len(df) < days + 1:
            return None
        
        # 날짜 기준으로 정렬 (오름차순)
        df = df.sort_values('date')
        
        # 마지막 날짜가 date와 일치하는지 확인
        last_date = df.iloc[-1]['date']
        if isinstance(last_date, str):
            last_date_str = last_date.replace('-', '')
        else:
            last_date_str = last_date.strftime('%Y%m%d')
        
        if last_date_str != date:
            # date에 해당하는 행 찾기
            df_filtered = df[df['date'].astype(str).str.replace('-', '') == date]
            if df_filtered.empty:
                return None
            idx = df_filtered.index[0]
        else:
            idx = df.index[-1]
        
        # N일 전 종가
        if idx < days:
            return None
        
        prev_close = df.iloc[idx - days]['close']
        curr_close = df.iloc[idx]['close']
        
        if prev_close > 0:
            return (curr_close / prev_close - 1)
        return None
    except Exception as e:
        logger.debug(f"KOSPI {days}일 수익률 계산 실패 ({date}): {e}")
        return None


def _load_regime_data(start_date: str, end_date: str) -> pd.DataFrame:
    """레짐 데이터 로드"""
    try:
        start_obj = datetime.strptime(start_date, '%Y%m%d').date()
        end_obj = datetime.strptime(end_date, '%Y%m%d').date()
        
        with db_manager.get_cursor(commit=False) as cur:
            cur.execute("""
                SELECT date, final_regime, kr_metrics, version
                FROM market_regime_daily
                WHERE date BETWEEN %s AND %s
                AND version = 'regime_v4'
                ORDER BY date
            """, (start_obj, end_obj))
            
            rows = cur.fetchall()
        
        if not rows:
            return pd.DataFrame()
        
        data = []
        for row in rows:
            # 날짜 처리
            date_val = row[0]
            if hasattr(date_val, 'strftime'):
                date_str = date_val.strftime('%Y%m%d')
            elif isinstance(date_val, str):
                date_str = date_val.replace('-', '')
            else:
                date_str = str(date_val).replace('-', '')
            
            kr_metrics = row[2] if row[2] else {}
            
            # JSONB 필드 파싱
            if isinstance(kr_metrics, str):
                try:
                    kr_metrics = json.loads(kr_metrics)
                except:
                    kr_metrics = {}
            elif hasattr(kr_metrics, '__dict__'):
                # dict-like object
                kr_metrics = dict(kr_metrics)
            
            midterm_regime = kr_metrics.get('midterm_regime') if isinstance(kr_metrics, dict) else None
            final_regime = row[1] if row[1] else None
            
            data.append({
                'date': date_str,
                'midterm_regime': midterm_regime,
                'final_regime': final_regime,
            })
        
        return pd.DataFrame(data)
    except Exception as e:
        logger.error(f"레짐 데이터 로드 실패: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return pd.DataFrame()


def analyze_regime_quality(start_date: str, end_date: str) -> Dict[str, Any]:
    """
    레짐 품질 검증
    
    Args:
        start_date: 시작일 (YYYYMMDD)
        end_date: 종료일 (YYYYMMDD)
    
    Returns:
        검증 결과 딕셔너리
    """
    logger.info(f"\n{'='*80}")
    logger.info(f"레짐 품질 검증 시작: {start_date} ~ {end_date}")
    logger.info(f"{'='*80}")
    
    # 1. 레짐 데이터 로드
    regime_df = _load_regime_data(start_date, end_date)
    if regime_df.empty:
        logger.warning("레짐 데이터가 없습니다.")
        return {'error': 'No regime data'}
    
    logger.info(f"📊 레짐 데이터 로드: {len(regime_df)}일")
    
    # 2. 거래일 목록
    trading_days = _get_trading_days(start_date, end_date)
    
    # 3. 각 날짜별 KOSPI 수익률 계산
    results = []
    for date_str in trading_days:
        if date_str not in regime_df['date'].values:
            continue
        
        regime_row = regime_df[regime_df['date'] == date_str].iloc[0]
        midterm_regime = regime_row['midterm_regime'] if 'midterm_regime' in regime_row else None
        
        if not midterm_regime:
            continue
        
        # KOSPI 5/10/20일 수익률 계산
        r5 = _get_kospi_returns(date_str, 5)
        r10 = _get_kospi_returns(date_str, 10)
        r20 = _get_kospi_returns(date_str, 20)
        
        if r5 is not None and r10 is not None and r20 is not None:
            results.append({
                'date': date_str,
                'midterm_regime': midterm_regime,
                'r5': r5,
                'r10': r10,
                'r20': r20,
            })
    
    if not results:
        logger.warning("수익률 데이터가 없습니다.")
        return {'error': 'No return data'}
    
    results_df = pd.DataFrame(results)
    logger.info(f"📈 수익률 데이터 계산: {len(results_df)}일")
    
    # 4. 레짐별 통계
    regime_stats = {}
    for regime in ['bull', 'neutral', 'bear', 'crash']:
        regime_data = results_df[results_df['midterm_regime'] == regime]
        if len(regime_data) > 0:
            regime_stats[regime] = {
                'count': len(regime_data),
                'r5_mean': regime_data['r5'].mean(),
                'r5_std': regime_data['r5'].std(),
                'r10_mean': regime_data['r10'].mean(),
                'r10_std': regime_data['r10'].std(),
                'r20_mean': regime_data['r20'].mean(),
                'r20_std': regime_data['r20'].std(),
                'r5_median': regime_data['r5'].median(),
                'r10_median': regime_data['r10'].median(),
                'r20_median': regime_data['r20'].median(),
            }
    
    # 5. 매칭률 분석
    # bull: r20 > 0.04, neutral: -0.04 <= r20 <= 0.04, bear: r20 < -0.04, crash: r20 < -0.10
    matching_analysis = {
        'bull': {'correct': 0, 'total': 0},
        'neutral': {'correct': 0, 'total': 0},
        'bear': {'correct': 0, 'total': 0},
        'crash': {'correct': 0, 'total': 0},
    }
    
    for _, row in results_df.iterrows():
        regime = row['midterm_regime']
        r20 = row['r20']
        
        if regime == 'bull':
            expected = r20 > 0.04
        elif regime == 'neutral':
            expected = -0.04 <= r20 <= 0.04
        elif regime == 'bear':
            expected = -0.10 < r20 < -0.04
        elif regime == 'crash':
            expected = r20 < -0.10
        else:
            continue
        
        matching_analysis[regime]['total'] += 1
        if expected:
            matching_analysis[regime]['correct'] += 1
    
    # 매칭률 계산
    matching_rates = {}
    for regime, stats in matching_analysis.items():
        if stats['total'] > 0:
            matching_rates[regime] = stats['correct'] / stats['total']
        else:
            matching_rates[regime] = 0.0
    
    # 6. 결과 출력
    logger.info(f"\n{'='*80}")
    logger.info("레짐별 통계")
    logger.info(f"{'='*80}")
    
    for regime, stats in regime_stats.items():
        logger.info(f"\n📊 {regime.upper()}:")
        logger.info(f"   - 일수: {stats['count']}일")
        logger.info(f"   - R5: 평균 {stats['r5_mean']*100:.2f}%, 표준편차 {stats['r5_std']*100:.2f}%, 중앙값 {stats['r5_median']*100:.2f}%")
        logger.info(f"   - R10: 평균 {stats['r10_mean']*100:.2f}%, 표준편차 {stats['r10_std']*100:.2f}%, 중앙값 {stats['r10_median']*100:.2f}%")
        logger.info(f"   - R20: 평균 {stats['r20_mean']*100:.2f}%, 표준편차 {stats['r20_std']*100:.2f}%, 중앙값 {stats['r20_median']*100:.2f}%")
    
    logger.info(f"\n{'='*80}")
    logger.info("매칭률 분석")
    logger.info(f"{'='*80}")
    
    for regime, rate in matching_rates.items():
        total = matching_analysis[regime]['total']
        correct = matching_analysis[regime]['correct']
        logger.info(f"   - {regime.upper()}: {rate*100:.1f}% ({correct}/{total})")
    
    # 7. 반환값 구성
    return {
        'start_date': start_date,
        'end_date': end_date,
        'total_days': len(results_df),
        'regime_stats': {k: {kk: float(vv) if isinstance(vv, (np.float64, np.float32)) else vv 
                            for kk, vv in v.items()} 
                        for k, v in regime_stats.items()},
        'matching_rates': {k: float(v) for k, v in matching_rates.items()},
        'matching_analysis': matching_analysis,
    }


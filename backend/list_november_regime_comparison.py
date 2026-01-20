#!/usr/bin/env python3
"""
11월 레짐 분석 결과를 KOSPI, KOSDAQ 지수와 비교하여 리스팅
"""
import os
import sys
import pandas as pd
from datetime import datetime
import logging

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import get_cursor

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_regime_data_november() -> pd.DataFrame:
    """11월 레짐 데이터 로드"""
    try:
        with get_cursor() as cur:
            cur.execute("""
                SELECT 
                    date,
                    final_regime,
                    kr_sentiment as kr_regime,
                    us_prev_sentiment as us_prev_regime,
                    kr_metrics,
                    us_metrics,
                    version
                FROM market_regime_daily
                WHERE date >= '2025-11-01' AND date <= '2025-11-30'
                ORDER BY date
            """)
            
            rows = cur.fetchall()
            if not rows:
                logger.warning("11월 레짐 데이터가 없습니다")
                return pd.DataFrame()
            
            # 컬럼명 가져오기
            columns = [desc[0] for desc in cur.description]
            
            # DataFrame 생성
            data = []
            for row in rows:
                row_dict = dict(zip(columns, row))
                # JSON 필드 파싱
                import json
                if row_dict.get('kr_metrics'):
                    if isinstance(row_dict['kr_metrics'], str):
                        row_dict['kr_metrics'] = json.loads(row_dict['kr_metrics'])
                if row_dict.get('us_metrics'):
                    if isinstance(row_dict['us_metrics'], str):
                        row_dict['us_metrics'] = json.loads(row_dict['us_metrics'])
                data.append(row_dict)
            
            df = pd.DataFrame(data)
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')
            
            return df
            
    except Exception as e:
        logger.error(f"레짐 데이터 로드 실패: {e}", exc_info=True)
        return pd.DataFrame()

def load_kospi_data_november() -> pd.DataFrame:
    """11월 KOSPI 데이터 로드"""
    try:
        cache_path = "data_cache/kospi200_ohlcv.pkl"
        if not os.path.exists(cache_path):
            logger.warning("KOSPI 캐시 파일이 없습니다")
            return pd.DataFrame()
        
        df = pd.read_pickle(cache_path)
        
        # 11월 데이터만 필터링
        nov_df = df[(df.index >= '2025-11-01') & (df.index <= '2025-11-30')]
        
        # 일별 등락률 계산
        if len(nov_df) >= 2:
            nov_df = nov_df.copy()
            nov_df['daily_return'] = nov_df['close'].pct_change() * 100
        
        return nov_df
        
    except Exception as e:
        logger.error(f"KOSPI 데이터 로드 실패: {e}", exc_info=True)
        return pd.DataFrame()

def load_kosdaq_data_november() -> pd.DataFrame:
    """11월 KOSDAQ 데이터 로드"""
    try:
        cache_path = "data_cache/ohlcv/229200.csv"
        if not os.path.exists(cache_path):
            logger.warning("KOSDAQ 캐시 파일이 없습니다")
            return pd.DataFrame()
        
        df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
        
        # 11월 데이터만 필터링
        nov_df = df[(df.index >= '2025-11-01') & (df.index <= '2025-11-30')]
        
        # 일별 등락률 계산
        if len(nov_df) >= 2:
            nov_df = nov_df.copy()
            nov_df['daily_return'] = nov_df['close'].pct_change() * 100
        
        return nov_df
        
    except Exception as e:
        logger.error(f"KOSDAQ 데이터 로드 실패: {e}", exc_info=True)
        return pd.DataFrame()

def main():
    """메인 함수"""
    logger.info("=" * 100)
    logger.info("11월 레짐 분석 결과 vs KOSPI/KOSDAQ 지수 비교")
    logger.info("=" * 100)
    
    # 데이터 로드
    logger.info("\n데이터 로드 중...")
    regime_df = load_regime_data_november()
    kospi_df = load_kospi_data_november()
    kosdaq_df = load_kosdaq_data_november()
    
    if regime_df.empty:
        logger.error("레짐 데이터가 없습니다")
        return
    
    logger.info(f"레짐 데이터: {len(regime_df)}개")
    logger.info(f"KOSPI 데이터: {len(kospi_df)}개")
    logger.info(f"KOSDAQ 데이터: {len(kosdaq_df)}개")
    
    # 날짜별 비교 리스팅
    print("\n" + "=" * 100)
    print(f"{'날짜':<12} {'레짐':<10} {'KR':<8} {'US':<8} {'KOSPI':<10} {'KOSPI%':<10} {'KOSDAQ':<10} {'KOSDAQ%':<10}")
    print("=" * 100)
    
    # 모든 날짜 통합
    all_dates = set()
    if not regime_df.empty:
        all_dates.update(regime_df.index)
    if not kospi_df.empty:
        all_dates.update(kospi_df.index)
    if not kosdaq_df.empty:
        all_dates.update(kosdaq_df.index)
    
    all_dates = sorted(all_dates)
    
    for date in all_dates:
        date_str = date.strftime('%Y-%m-%d')
        
        # 레짐 데이터
        regime_row = regime_df.loc[date] if date in regime_df.index else None
        final_regime = regime_row['final_regime'] if regime_row is not None else 'N/A'
        kr_regime = regime_row['kr_regime'] if regime_row is not None else 'N/A'
        us_regime = regime_row['us_prev_regime'] if regime_row is not None else 'N/A'
        
        # KOSPI 데이터
        kospi_row = kospi_df.loc[date] if date in kospi_df.index else None
        kospi_close = f"{kospi_row['close']:.2f}" if kospi_row is not None else 'N/A'
        kospi_return = f"{kospi_row['daily_return']:+.2f}%" if kospi_row is not None and 'daily_return' in kospi_row and pd.notna(kospi_row['daily_return']) else 'N/A'
        
        # KOSDAQ 데이터
        kosdaq_row = kosdaq_df.loc[date] if date in kosdaq_df.index else None
        kosdaq_close = f"{kosdaq_row['close']:.2f}" if kosdaq_row is not None else 'N/A'
        kosdaq_return = f"{kosdaq_row['daily_return']:+.2f}%" if kosdaq_row is not None and 'daily_return' in kosdaq_row and pd.notna(kosdaq_row['daily_return']) else 'N/A'
        
        print(f"{date_str:<12} {final_regime:<10} {kr_regime:<8} {us_regime:<8} {kospi_close:<10} {kospi_return:<10} {kosdaq_close:<10} {kosdaq_return:<10}")
    
    # 통계 요약
    print("\n" + "=" * 100)
    print("통계 요약")
    print("=" * 100)
    
    if not regime_df.empty:
        regime_counts = regime_df['final_regime'].value_counts()
        print("\n레짐 분포:")
        for regime, count in regime_counts.items():
            print(f"  {regime}: {count}일")
    
    if not kospi_df.empty and 'daily_return' in kospi_df.columns:
        kospi_returns = kospi_df['daily_return'].dropna()
        if len(kospi_returns) > 0:
            print(f"\nKOSPI 등락률 통계:")
            print(f"  평균: {kospi_returns.mean():+.2f}%")
            print(f"  최대: {kospi_returns.max():+.2f}%")
            print(f"  최소: {kospi_returns.min():+.2f}%")
            print(f"  상승일: {(kospi_returns > 0).sum()}일")
            print(f"  하락일: {(kospi_returns < 0).sum()}일")
    
    if not kosdaq_df.empty and 'daily_return' in kosdaq_df.columns:
        kosdaq_returns = kosdaq_df['daily_return'].dropna()
        if len(kosdaq_returns) > 0:
            print(f"\nKOSDAQ 등락률 통계:")
            print(f"  평균: {kosdaq_returns.mean():+.2f}%")
            print(f"  최대: {kosdaq_returns.max():+.2f}%")
            print(f"  최소: {kosdaq_returns.min():+.2f}%")
            print(f"  상승일: {(kosdaq_returns > 0).sum()}일")
            print(f"  하락일: {(kosdaq_returns < 0).sum()}일")
    
    # 레짐별 평균 등락률
    print("\n" + "=" * 100)
    print("레짐별 평균 등락률")
    print("=" * 100)
    
    if not regime_df.empty and not kospi_df.empty and 'daily_return' in kospi_df.columns:
        merged = pd.merge(
            regime_df[['final_regime']],
            kospi_df[['daily_return']],
            left_index=True,
            right_index=True,
            how='inner'
        )
        
        regime_returns = merged.groupby('final_regime')['daily_return'].agg(['mean', 'count'])
        print("\nKOSPI 평균 등락률:")
        for regime, row in regime_returns.iterrows():
            print(f"  {regime}: {row['mean']:+.2f}% (n={int(row['count'])})")
    
    if not regime_df.empty and not kosdaq_df.empty and 'daily_return' in kosdaq_df.columns:
        merged = pd.merge(
            regime_df[['final_regime']],
            kosdaq_df[['daily_return']],
            left_index=True,
            right_index=True,
            how='inner'
        )
        
        regime_returns = merged.groupby('final_regime')['daily_return'].agg(['mean', 'count'])
        print("\nKOSDAQ 평균 등락률:")
        for regime, row in regime_returns.iterrows():
            print(f"  {regime}: {row['mean']:+.2f}% (n={int(row['count'])})")

if __name__ == "__main__":
    main()


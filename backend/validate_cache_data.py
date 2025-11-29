#!/usr/bin/env python3
"""
캐시 데이터 검증 스크립트
- KOSPI, KOSDAQ, SPY, QQQ, VIX 캐시 데이터 검증
- 데이터 정합성, 이상치, 누락 확인
"""
import os
import sys
import pandas as pd
import pickle
from pathlib import Path
from datetime import datetime, timedelta
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import get_cursor

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def validate_kospi_cache() -> dict:
    """KOSPI 캐시 검증"""
    result = {
        'name': 'KOSPI',
        'exists': False,
        'row_count': 0,
        'date_range': None,
        'issues': [],
        'warnings': []
    }
    
    try:
        cache_path = Path("data_cache/kospi200_ohlcv.pkl")
        if not cache_path.exists():
            result['issues'].append("캐시 파일이 없습니다")
            return result
        
        result['exists'] = True
        df = pd.read_pickle(cache_path)
        
        if df.empty:
            result['issues'].append("데이터가 비어있습니다")
            return result
        
        result['row_count'] = len(df)
        
        # 날짜 범위
        if isinstance(df.index, pd.DatetimeIndex):
            result['date_range'] = (df.index.min(), df.index.max())
        else:
            result['warnings'].append("날짜 인덱스가 DatetimeIndex가 아닙니다")
        
        # 데이터 검증
        if 'close' in df.columns:
            close_values = df['close'].dropna()
            
            # 값 범위 검증 (KOSPI는 보통 2000~4000)
            if len(close_values) > 0:
                min_close = close_values.min()
                max_close = close_values.max()
                
                if min_close < 1000 or max_close > 5000:
                    result['warnings'].append(f"종가 범위가 비정상적: {min_close:.2f} ~ {max_close:.2f}")
                
                # 일별 등락률 검증
                if len(df) >= 2:
                    daily_returns = df['close'].pct_change().dropna() * 100
                    extreme_returns = daily_returns[abs(daily_returns) > 10]
                    if len(extreme_returns) > 0:
                        result['warnings'].append(f"일별 등락률 ±10% 이상: {len(extreme_returns)}개 (최대: {daily_returns.max():.2f}%, 최소: {daily_returns.min():.2f}%)")
        else:
            result['issues'].append("'close' 컬럼이 없습니다")
        
        # 최신 날짜 확인
        if isinstance(df.index, pd.DatetimeIndex):
            latest_date = df.index.max()
            days_ago = (datetime.now() - latest_date).days
            if days_ago > 7:
                result['warnings'].append(f"최신 데이터가 {days_ago}일 전입니다")
        
    except Exception as e:
        result['issues'].append(f"검증 실패: {e}")
    
    return result

def validate_kosdaq_cache() -> dict:
    """KOSDAQ 캐시 검증"""
    result = {
        'name': 'KOSDAQ',
        'exists': False,
        'row_count': 0,
        'date_range': None,
        'issues': [],
        'warnings': []
    }
    
    try:
        cache_path = Path("data_cache/ohlcv/229200.csv")
        if not cache_path.exists():
            result['issues'].append("캐시 파일이 없습니다")
            return result
        
        result['exists'] = True
        df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
        
        if df.empty:
            result['issues'].append("데이터가 비어있습니다")
            return result
        
        result['row_count'] = len(df)
        
        # 날짜 범위
        if isinstance(df.index, pd.DatetimeIndex):
            result['date_range'] = (df.index.min(), df.index.max())
        
        # 데이터 검증
        if 'close' in df.columns:
            close_values = df['close'].dropna()
            
            if len(close_values) > 0:
                min_close = close_values.min()
                max_close = close_values.max()
                
                # KOSDAQ은 보통 10000~20000 범위
                if min_close < 5000 or max_close > 30000:
                    result['warnings'].append(f"종가 범위가 비정상적: {min_close:.2f} ~ {max_close:.2f}")
                
                # 일별 등락률 검증
                if len(df) >= 2:
                    daily_returns = df['close'].pct_change().dropna() * 100
                    extreme_returns = daily_returns[abs(daily_returns) > 10]
                    if len(extreme_returns) > 0:
                        result['warnings'].append(f"일별 등락률 ±10% 이상: {len(extreme_returns)}개")
        else:
            result['issues'].append("'close' 컬럼이 없습니다")
        
        # 최신 날짜 확인
        if isinstance(df.index, pd.DatetimeIndex):
            latest_date = df.index.max()
            days_ago = (datetime.now() - latest_date).days
            if days_ago > 7:
                result['warnings'].append(f"최신 데이터가 {days_ago}일 전입니다")
        
    except Exception as e:
        result['issues'].append(f"검증 실패: {e}")
    
    return result

def validate_us_market_cache(symbol: str, filename: str) -> dict:
    """미국 시장 캐시 검증"""
    result = {
        'name': symbol,
        'exists': False,
        'row_count': 0,
        'date_range': None,
        'issues': [],
        'warnings': []
    }
    
    try:
        cache_path = Path(f"cache/us_futures/{filename}")
        if not cache_path.exists():
            result['issues'].append("캐시 파일이 없습니다")
            return result
        
        result['exists'] = True
        df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
        
        if df.empty:
            result['issues'].append("데이터가 비어있습니다")
            return result
        
        result['row_count'] = len(df)
        
        # 날짜 범위
        if isinstance(df.index, pd.DatetimeIndex):
            result['date_range'] = (df.index.min(), df.index.max())
        
        # 컬럼명 확인 (대문자/소문자)
        close_col = None
        for col in ['Close', 'close', 'CLOSE']:
            if col in df.columns:
                close_col = col
                break
        
        if close_col is None:
            result['issues'].append("종가 컬럼을 찾을 수 없습니다")
            return result
        
        # 데이터 검증
        close_values = df[close_col].dropna()
        
        if len(close_values) > 0:
            min_close = close_values.min()
            max_close = close_values.max()
            
            # VIX는 보통 10~50 범위
            if symbol == '^VIX':
                if min_close < 5 or max_close > 100:
                    result['warnings'].append(f"VIX 값 범위가 비정상적: {min_close:.2f} ~ {max_close:.2f}")
            # SPY/QQQ는 보통 100~1000 범위
            else:
                if min_close < 50 or max_close > 2000:
                    result['warnings'].append(f"종가 범위가 비정상적: {min_close:.2f} ~ {max_close:.2f}")
            
            # 일별 등락률 검증
            if len(df) >= 2:
                daily_returns = df[close_col].pct_change().dropna() * 100
                extreme_returns = daily_returns[abs(daily_returns) > 15]
                if len(extreme_returns) > 0:
                    result['warnings'].append(f"일별 등락률 ±15% 이상: {len(extreme_returns)}개")
        
        # 최신 날짜 확인
        if isinstance(df.index, pd.DatetimeIndex):
            latest_date = df.index.max()
            days_ago = (datetime.now() - latest_date).days
            if days_ago > 7:
                result['warnings'].append(f"최신 데이터가 {days_ago}일 전입니다")
        
    except Exception as e:
        result['issues'].append(f"검증 실패: {e}")
    
    return result

def validate_db_vs_cache() -> dict:
    """DB 저장 데이터와 캐시 데이터 일치 여부 검증"""
    result = {
        'name': 'DB vs Cache',
        'issues': [],
        'warnings': []
    }
    
    try:
        # 11월 데이터 비교
        with get_cursor() as cur:
            # DB에서 KOSPI 등락률 가져오기
            cur.execute("""
                SELECT date, kospi_return
                FROM market_conditions
                WHERE date >= '2025-11-01' AND date <= '2025-11-30'
                AND kospi_return IS NOT NULL
                ORDER BY date
            """)
            db_rows = cur.fetchall()
            
            # 캐시에서 KOSPI 데이터 가져오기
            cache_path = Path("data_cache/kospi200_ohlcv.pkl")
            if cache_path.exists():
                kospi_df = pd.read_pickle(cache_path)
                
                if not kospi_df.empty and 'close' in kospi_df.columns:
                    # 11월 데이터만 필터링
                    nov_df = kospi_df[(kospi_df.index >= '2025-11-01') & (kospi_df.index <= '2025-11-30')]
                    
                    if len(nov_df) >= 2:
                        # 일별 등락률 계산
                        nov_df = nov_df.sort_index()
                        daily_returns = nov_df['close'].pct_change()
                        
                        # DB와 비교
                        db_dates = {row[0] for row in db_rows}
                        cache_dates = set(nov_df.index.date)
                        
                        common_dates = db_dates & cache_dates
                        
                        mismatches = []
                        for date in common_dates:
                            # DB 값 찾기
                            db_return = None
                            for row in db_rows:
                                if row[0] == date or (hasattr(row[0], 'date') and row[0].date() == date):
                                    db_return = row[1]
                                    break
                            
                            # 캐시 값 찾기
                            cache_return = None
                            if date in cache_dates:
                                date_idx = nov_df.index.get_loc(pd.Timestamp(date))
                                if date_idx > 0:
                                    prev_close = nov_df.iloc[date_idx - 1]['close']
                                    curr_close = nov_df.iloc[date_idx]['close']
                                    if prev_close > 0:
                                        cache_return = (curr_close / prev_close - 1)
                            
                            # 비교 (0.1% 오차 허용)
                            if db_return is not None and cache_return is not None:
                                diff = abs(db_return - cache_return)
                                if diff > 0.001:  # 0.1% 이상 차이
                                    mismatches.append({
                                        'date': date,
                                        'db': db_return * 100,
                                        'cache': cache_return * 100,
                                        'diff': diff * 100
                                    })
                        
                        if mismatches:
                            result['warnings'].append(f"DB와 캐시 데이터 불일치: {len(mismatches)}개")
                            for mm in mismatches[:5]:  # 처음 5개만
                                result['warnings'].append(f"  {mm['date']}: DB={mm['db']:+.2f}%, Cache={mm['cache']:+.2f}%, 차이={mm['diff']:.2f}%")
                        else:
                            result['warnings'].append("✅ DB와 캐시 데이터 일치")
        
    except Exception as e:
        result['issues'].append(f"검증 실패: {e}")
    
    return result

def validate_november_coverage() -> dict:
    """11월 데이터 커버리지 검증"""
    result = {
        'name': 'November Coverage',
        'issues': [],
        'warnings': []
    }
    
    try:
        # 거래일 생성
        start_date = pd.to_datetime('2025-11-01')
        end_date = pd.to_datetime('2025-11-30')
        trading_days = pd.bdate_range(start=start_date, end=end_date, freq='B')
        trading_days_set = set(trading_days.date)
        
        # 각 캐시에서 11월 데이터 확인
        caches = {
            'KOSPI': Path("data_cache/kospi200_ohlcv.pkl"),
            'KOSDAQ': Path("data_cache/ohlcv/229200.csv"),
            'SPY': Path("cache/us_futures/SPY.csv"),
            'QQQ': Path("cache/us_futures/QQQ.csv"),
            'VIX': Path("cache/us_futures/^VIX.csv")
        }
        
        for name, cache_path in caches.items():
            if not cache_path.exists():
                result['warnings'].append(f"{name}: 캐시 파일 없음")
                continue
            
            try:
                if cache_path.suffix == '.pkl':
                    df = pd.read_pickle(cache_path)
                else:
                    df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
                
                if df.empty:
                    result['warnings'].append(f"{name}: 데이터 없음")
                    continue
                
                # 11월 데이터 필터링
                nov_df = df[(df.index >= start_date) & (df.index <= end_date)]
                cache_dates = set(nov_df.index.date) if isinstance(nov_df.index, pd.DatetimeIndex) else set()
                
                missing = trading_days_set - cache_dates
                if missing:
                    result['warnings'].append(f"{name}: 누락된 날짜 {len(missing)}개")
                    for date in sorted(missing)[:5]:
                        result['warnings'].append(f"  {date}")
                else:
                    result['warnings'].append(f"✅ {name}: 11월 데이터 완전")
                    
            except Exception as e:
                result['warnings'].append(f"{name}: 검증 실패 - {e}")
        
    except Exception as e:
        result['issues'].append(f"검증 실패: {e}")
    
    return result

def main():
    """메인 함수"""
    print("=" * 100)
    print("캐시 데이터 검증")
    print("=" * 100)
    
    results = []
    
    # 1. KOSPI 캐시 검증
    print("\n[1/6] KOSPI 캐시 검증")
    print("-" * 100)
    kospi_result = validate_kospi_cache()
    results.append(kospi_result)
    print_result(kospi_result)
    
    # 2. KOSDAQ 캐시 검증
    print("\n[2/6] KOSDAQ 캐시 검증")
    print("-" * 100)
    kosdaq_result = validate_kosdaq_cache()
    results.append(kosdaq_result)
    print_result(kosdaq_result)
    
    # 3. SPY 캐시 검증
    print("\n[3/6] SPY 캐시 검증")
    print("-" * 100)
    spy_result = validate_us_market_cache('SPY', 'SPY.csv')
    results.append(spy_result)
    print_result(spy_result)
    
    # 4. QQQ 캐시 검증
    print("\n[4/6] QQQ 캐시 검증")
    print("-" * 100)
    qqq_result = validate_us_market_cache('QQQ', 'QQQ.csv')
    results.append(qqq_result)
    print_result(qqq_result)
    
    # 5. VIX 캐시 검증
    print("\n[5/6] VIX 캐시 검증")
    print("-" * 100)
    vix_result = validate_us_market_cache('^VIX', '^VIX.csv')
    results.append(vix_result)
    print_result(vix_result)
    
    # 6. DB vs Cache 검증
    print("\n[6/6] DB vs Cache 일치 여부 검증")
    print("-" * 100)
    db_cache_result = validate_db_vs_cache()
    results.append(db_cache_result)
    print_result(db_cache_result)
    
    # 7. 11월 커버리지 검증
    print("\n[7/7] 11월 데이터 커버리지 검증")
    print("-" * 100)
    coverage_result = validate_november_coverage()
    results.append(coverage_result)
    print_result(coverage_result)
    
    # 최종 요약
    print("\n" + "=" * 100)
    print("검증 결과 요약")
    print("=" * 100)
    
    total_issues = sum(len(r.get('issues', [])) for r in results)
    total_warnings = sum(len(r.get('warnings', [])) for r in results)
    
    print(f"총 이슈: {total_issues}개")
    print(f"총 경고: {total_warnings}개")
    
    if total_issues == 0:
        print("\n✅ 심각한 문제 없음")
    else:
        print("\n⚠️ 심각한 문제 발견")
    
    for result in results:
        if result.get('issues'):
            print(f"\n❌ {result['name']}:")
            for issue in result['issues']:
                print(f"   - {issue}")

def print_result(result: dict):
    """검증 결과 출력"""
    if result.get('exists'):
        print(f"✅ 파일 존재: {result['row_count']}개 행")
        
        if result.get('date_range'):
            start, end = result['date_range']
            print(f"   날짜 범위: {start.strftime('%Y-%m-%d')} ~ {end.strftime('%Y-%m-%d')}")
    else:
        print("❌ 파일 없음")
    
    if result.get('warnings'):
        for warning in result['warnings']:
            print(f"⚠️ {warning}")
    
    if result.get('issues'):
        for issue in result['issues']:
            print(f"❌ {issue}")

if __name__ == "__main__":
    main()


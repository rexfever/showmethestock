#!/usr/bin/env python3
"""
레짐 분석 캐시 전체 재생성
- KOSPI: FinanceDataReader/pykrx (실제 지수)
- KOSDAQ: 키움 API (229200)
- SPY/QQQ/VIX: yfinance
"""
import os
import sys
import pandas as pd
import pickle
from pathlib import Path
from datetime import datetime, timedelta
import logging
import time
import shutil

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kiwoom_api import api
from date_helper import normalize_date

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def regenerate_kospi_cache(start_date: str = '20200101', end_date: str = None) -> bool:
    """KOSPI 캐시 재생성 (실제 지수 데이터)"""
    try:
        cache_path = Path("data_cache/kospi200_ohlcv.pkl")
        cache_dir = cache_path.parent
        cache_dir.mkdir(exist_ok=True)
        
        # 기존 캐시 백업
        if cache_path.exists():
            backup_path = cache_path.with_suffix('.pkl.backup')
            shutil.copy2(cache_path, backup_path)
            logger.info(f"기존 KOSPI 캐시 백업: {backup_path}")
        
        if end_date is None:
            end_date = datetime.now().strftime('%Y%m%d')
        
        logger.info(f"KOSPI 지수 데이터 재생성 시작: {start_date} ~ {end_date}")
        
        # pykrx 우선 시도
        try:
            from pykrx import stock
            
            start_dt = pd.to_datetime(start_date, format='%Y%m%d')
            end_dt = pd.to_datetime(end_date, format='%Y%m%d')
            
            # KOSPI 지수 코드: 1001
            df = stock.get_index_ohlcv_by_date(
                start_date,
                end_date,
                "1001"
            )
            
            if not df.empty:
                # 컬럼명 변환 (한국어 → 영어)
                column_mapping = {
                    '시가': 'open',
                    '고가': 'high',
                    '저가': 'low',
                    '종가': 'close',
                    '거래량': 'volume'
                }
                df = df.rename(columns=column_mapping)
                
                # 필요한 컬럼만 선택
                df = df[['open', 'high', 'low', 'close', 'volume']]
                
                # 인덱스를 날짜로 설정
                if not isinstance(df.index, pd.DatetimeIndex):
                    df = df.reset_index()
                    if '날짜' in df.columns:
                        df['날짜'] = pd.to_datetime(df['날짜'])
                        df = df.set_index('날짜')
                
                # 데이터 검증
                if not df.empty:
                    latest_close = df.iloc[-1]['close']
                    if not (2000 <= latest_close <= 4000):
                        logger.warning(f"KOSPI 지수 값이 비정상적: {latest_close:.2f}")
                
                df.to_pickle(cache_path)
                logger.info(f"✅ KOSPI 캐시 재생성 완료 (pykrx): {len(df)}개 행")
                return True
            else:
                raise Exception("pykrx 데이터가 비어있음")
                
        except ImportError:
            logger.warning("pykrx가 설치되지 않음. FinanceDataReader 사용")
        except Exception as e:
            logger.warning(f"pykrx 사용 실패: {e}, FinanceDataReader 사용")
        
        # FinanceDataReader fallback
        try:
            import FinanceDataReader as fdr
            
            start_dt = pd.to_datetime(start_date, format='%Y%m%d')
            end_dt = pd.to_datetime(end_date, format='%Y%m%d')
            
            df = fdr.DataReader('KS11', start_dt.strftime('%Y-%m-%d'), end_dt.strftime('%Y-%m-%d'))
            
            if not df.empty:
                # 컬럼명 소문자로 통일
                df.columns = df.columns.str.lower()
                
                # 필요한 컬럼만 선택
                required_cols = ['open', 'high', 'low', 'close', 'volume']
                df = df[[col for col in required_cols if col in df.columns]]
                
                # 데이터 검증
                if not df.empty:
                    latest_close = df.iloc[-1]['close']
                    if not (2000 <= latest_close <= 4000):
                        logger.warning(f"KOSPI 지수 값이 비정상적: {latest_close:.2f}")
                
                df.to_pickle(cache_path)
                logger.info(f"✅ KOSPI 캐시 재생성 완료 (FinanceDataReader): {len(df)}개 행")
                return True
            else:
                raise Exception("FinanceDataReader 데이터가 비어있음")
                
        except ImportError:
            logger.error("FinanceDataReader가 설치되지 않음")
            return False
        except Exception as e:
            logger.error(f"FinanceDataReader 사용 실패: {e}")
            return False
        
    except Exception as e:
        logger.error(f"KOSPI 캐시 재생성 실패: {e}", exc_info=True)
        return False

def regenerate_kosdaq_cache(start_date: str = '20200101', end_date: str = None) -> bool:
    """KOSDAQ 캐시 재생성"""
    try:
        cache_path = Path("data_cache/ohlcv/229200.csv")
        cache_dir = cache_path.parent
        cache_dir.mkdir(exist_ok=True)
        
        # 기존 캐시 백업
        if cache_path.exists():
            backup_path = cache_path.with_suffix('.csv.backup')
            shutil.copy2(cache_path, backup_path)
            logger.info(f"기존 KOSDAQ 캐시 백업: {backup_path}")
        
        if end_date is None:
            end_date = datetime.now().strftime('%Y%m%d')
        
        logger.info(f"KOSDAQ 지수 데이터 재생성 시작: {start_date} ~ {end_date}")
        
        # 키움 API로 데이터 수집
        # 충분한 기간의 데이터 가져오기
        days_diff = (pd.to_datetime(end_date, format='%Y%m%d') - pd.to_datetime(start_date, format='%Y%m%d')).days
        count = min(days_diff + 100, 1000)  # 여유분 포함
        
        df = api.get_ohlcv("229200", count, end_date)
        
        if df.empty:
            logger.error("KOSDAQ 데이터 수집 실패")
            return False
        
        # 날짜 인덱스 설정
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], format='%Y%m%d', errors='coerce')
            df = df.set_index('date')
        elif not isinstance(df.index, pd.DatetimeIndex):
            logger.warning("KOSDAQ 데이터 날짜 인덱스 변환 실패")
            return False
        
        # 컬럼명 소문자로 통일
        df.columns = df.columns.str.lower()
        
        # 날짜 필터링
        start_dt = pd.to_datetime(start_date, format='%Y%m%d')
        end_dt = pd.to_datetime(end_date, format='%Y%m%d')
        df = df[(df.index >= start_dt) & (df.index <= end_dt)]
        
        # CSV로 저장
        df.to_csv(cache_path)
        logger.info(f"✅ KOSDAQ 캐시 재생성 완료: {len(df)}개 행")
        return True
        
    except Exception as e:
        logger.error(f"KOSDAQ 캐시 재생성 실패: {e}", exc_info=True)
        return False

def regenerate_us_market_cache(start_date: str = '20200101', end_date: str = None) -> bool:
    """미국 시장 캐시 재생성 (SPY, QQQ, VIX)"""
    try:
        cache_dir = Path("cache/us_futures")
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        if end_date is None:
            end_date = datetime.now().strftime('%Y%m%d')
        
        symbols = ['SPY', 'QQQ', '^VIX']
        success_count = 0
        
        for symbol in symbols:
            try:
                # 파일명 매핑
                filename_map = {
                    '^VIX': '^VIX.csv',
                }
                filename = filename_map.get(symbol, f"{symbol}.csv")
                cache_path = cache_dir / filename
                
                # 기존 캐시 백업
                if cache_path.exists():
                    backup_path = cache_path.with_suffix('.csv.backup')
                    shutil.copy2(cache_path, backup_path)
                    logger.info(f"기존 {symbol} 캐시 백업: {backup_path}")
                
                logger.info(f"{symbol} 데이터 재생성 중...")
                
                # yfinance 사용
                try:
                    import yfinance as yf
                    
                    ticker = yf.Ticker(symbol)
                    start_dt = pd.to_datetime(start_date, format='%Y%m%d')
                    end_dt = pd.to_datetime(end_date, format='%Y%m%d')
                    
                    # 다음 거래일까지 포함
                    end_dt_extended = end_dt + timedelta(days=1)
                    
                    df = ticker.history(start=start_dt, end=end_dt_extended)
                    
                    if df.empty:
                        logger.warning(f"{symbol} 데이터 수집 실패")
                        continue
                    
                    # 컬럼명 대문자로 통일
                    df.columns = [col.capitalize() for col in df.columns]
                    
                    # 타임존 제거 (날짜 비교를 위해)
                    if df.index.tz is not None:
                        df.index = df.index.tz_localize(None)
                    
                    # 날짜 필터링
                    df = df[(df.index >= start_dt) & (df.index <= end_dt)]
                    
                    # VIX 단위 보정 확인
                    if symbol == '^VIX':
                        latest_close = df.iloc[-1]['Close']
                        if latest_close > 100:  # 비정상적으로 높으면 10배 오류 가능
                            logger.warning(f"VIX 값이 비정상적으로 높음: {latest_close:.2f}, 10으로 나누기")
                            df['Open'] = df['Open'] / 10
                            df['High'] = df['High'] / 10
                            df['Low'] = df['Low'] / 10
                            df['Close'] = df['Close'] / 10
                    
                    # CSV로 저장
                    df.to_csv(cache_path)
                    logger.info(f"✅ {symbol} 캐시 재생성 완료: {len(df)}개 행")
                    success_count += 1
                    
                    # API 호출 제한 방지
                    time.sleep(1)
                    
                except ImportError:
                    logger.error(f"yfinance가 설치되지 않음")
                    continue
                except Exception as e:
                    logger.error(f"{symbol} 데이터 수집 실패: {e}")
                    continue
                    
            except Exception as e:
                logger.error(f"{symbol} 캐시 재생성 실패: {e}")
                continue
        
        logger.info(f"미국 시장 캐시 재생성 완료: {success_count}/{len(symbols)}개 성공")
        return success_count > 0
        
    except Exception as e:
        logger.error(f"미국 시장 캐시 재생성 실패: {e}", exc_info=True)
        return False

def main():
    """메인 함수"""
    logger.info("=" * 70)
    logger.info("레짐 분석 캐시 전체 재생성")
    logger.info("=" * 70)
    
    # 시작일: 2020년 1월 1일부터
    start_date = '20200101'
    end_date = datetime.now().strftime('%Y%m%d')
    
    logger.info(f"대상 기간: {start_date} ~ {end_date}")
    
    results = {}
    
    # 1. KOSPI 캐시 재생성
    logger.info("\n[1/3] KOSPI 캐시 재생성")
    results['kospi'] = regenerate_kospi_cache(start_date, end_date)
    
    # 2. KOSDAQ 캐시 재생성
    logger.info("\n[2/3] KOSDAQ 캐시 재생성")
    results['kosdaq'] = regenerate_kosdaq_cache(start_date, end_date)
    
    # 3. 미국 시장 캐시 재생성
    logger.info("\n[3/3] 미국 시장 캐시 재생성")
    results['us_market'] = regenerate_us_market_cache(start_date, end_date)
    
    # 최종 결과
    logger.info("\n" + "=" * 70)
    logger.info("레짐 캐시 재생성 결과")
    logger.info("=" * 70)
    
    for key, success in results.items():
        status = "✅ 성공" if success else "❌ 실패"
        logger.info(f"  {key}: {status}")
    
    if all(results.values()):
        logger.info("\n✅ 모든 레짐 캐시 재생성 완료")
    else:
        logger.warning("\n⚠️ 일부 캐시 재생성 실패")
    
    # 최종 확인
    logger.info("\n최종 캐시 상태:")
    try:
        kospi_path = Path("data_cache/kospi200_ohlcv.pkl")
        if kospi_path.exists():
            df = pd.read_pickle(kospi_path)
            logger.info(f"  KOSPI: {len(df)}개 행 (기간: {df.index.min()} ~ {df.index.max()})")
        
        kosdaq_path = Path("data_cache/ohlcv/229200.csv")
        if kosdaq_path.exists():
            df = pd.read_csv(kosdaq_path, index_col=0, parse_dates=True)
            logger.info(f"  KOSDAQ: {len(df)}개 행 (기간: {df.index.min()} ~ {df.index.max()})")
        
        us_dir = Path("cache/us_futures")
        if us_dir.exists():
            for symbol in ['SPY', 'QQQ', '^VIX']:
                filename = '^VIX.csv' if symbol == '^VIX' else f"{symbol}.csv"
                file_path = us_dir / filename
                if file_path.exists():
                    df = pd.read_csv(file_path, index_col=0, parse_dates=True)
                    logger.info(f"  {symbol}: {len(df)}개 행 (기간: {df.index.min()} ~ {df.index.max()})")
    except Exception as e:
        logger.warning(f"최종 확인 실패: {e}")

if __name__ == "__main__":
    main()


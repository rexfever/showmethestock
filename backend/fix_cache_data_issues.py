#!/usr/bin/env python3
"""
캐시 데이터 문제 해결 스크립트
- KOSPI: ETF 데이터를 실제 지수 데이터로 교체
- VIX: 단위 오류 수정 (10배 → 1배)
"""
import os
import sys
import pandas as pd
import pickle
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_kospi_cache() -> bool:
    """KOSPI 캐시를 실제 지수 데이터로 교체"""
    try:
        cache_path = Path("data_cache/kospi200_ohlcv.pkl")
        
        # 기존 캐시 백업
        if cache_path.exists():
            backup_path = cache_path.with_suffix('.pkl.backup_etf')
            shutil.copy2(cache_path, backup_path)
            logger.info(f"기존 ETF 캐시 백업: {backup_path}")
        
        logger.info("=" * 70)
        logger.info("KOSPI 지수 데이터 수집 시작")
        logger.info("=" * 70)
        
        # 방법 1: pykrx 시도
        kospi_df = pd.DataFrame()
        try:
            from pykrx import stock
            logger.info("pykrx 사용하여 KOSPI 지수 데이터 수집...")
            
            # 충분한 기간의 데이터 수집 (2020-01-01 ~ 현재)
            start_date = pd.to_datetime("2020-01-01")
            end_date = pd.to_datetime(datetime.now())
            
            # 배치로 나누어 수집 (1년씩)
            all_data = []
            current = start_date
            
            while current <= end_date:
                batch_end = min(current + pd.Timedelta(days=365), end_date)
                start_str = current.strftime('%Y%m%d')
                end_str = batch_end.strftime('%Y%m%d')
                
                logger.info(f"  수집 중: {start_str} ~ {end_str}")
                
                try:
                    df_batch = stock.get_index_ohlcv_by_date(start_str, end_str, "1001")
                    
                    if not df_batch.empty:
                        # 컬럼명 한글 → 영어 매핑
                        column_mapping = {
                            '시가': 'open',
                            '고가': 'high',
                            '저가': 'low',
                            '종가': 'close',
                            '거래량': 'volume',
                            '거래대금': 'amount',
                            '상장시가총액': 'market_cap'
                        }
                        df_batch = df_batch.rename(columns=column_mapping)
                        # 필요한 컬럼만 선택
                        df_batch = df_batch[['open', 'high', 'low', 'close', 'volume']]
                        df_batch = df_batch.reset_index().rename(columns={'날짜': 'date'})
                        df_batch['date'] = pd.to_datetime(df_batch['date'])
                        df_batch = df_batch.set_index('date')
                        all_data.append(df_batch)
                        logger.info(f"    수집 완료: {len(df_batch)}개 행")
                    
                    # API 호출 제한 방지
                    import time
                    time.sleep(0.5)
                    
                except Exception as e:
                    logger.warning(f"    배치 수집 실패: {e}")
                
                current = batch_end + pd.Timedelta(days=1)
            
            if all_data:
                kospi_df = pd.concat(all_data)
                kospi_df = kospi_df[~kospi_df.index.duplicated(keep='last')]
                kospi_df = kospi_df.sort_index()
                logger.info(f"✅ pykrx로 KOSPI 지수 데이터 수집 완료: {len(kospi_df)}개 행")
        
        except ImportError:
            logger.warning("pykrx가 설치되지 않음. FinanceDataReader 사용...")
            
            # 방법 2: FinanceDataReader 시도
            try:
                import FinanceDataReader as fdr
                logger.info("FinanceDataReader 사용하여 KOSPI 지수 데이터 수집...")
                
                start_date_str = "2020-01-01"
                end_date_str = datetime.now().strftime('%Y-%m-%d')
                
                kospi_df = fdr.DataReader('KS11', start_date_str, end_date_str)
                
                if not kospi_df.empty:
                    kospi_df.columns = kospi_df.columns.str.lower()
                    logger.info(f"✅ FinanceDataReader로 KOSPI 지수 데이터 수집 완료: {len(kospi_df)}개 행")
                else:
                    raise Exception("FinanceDataReader 데이터 없음")
            
            except ImportError:
                logger.error("FinanceDataReader도 설치되지 않음")
                return False
            except Exception as e:
                logger.error(f"FinanceDataReader 사용 실패: {e}")
                return False
        
        except Exception as e:
            logger.error(f"pykrx 사용 실패: {e}")
            return False
        
        if kospi_df.empty:
            logger.error("KOSPI 지수 데이터 수집 실패")
            return False
        
        # 데이터 검증
        logger.info("\n데이터 검증:")
        logger.info(f"  기간: {kospi_df.index[0].strftime('%Y-%m-%d')} ~ {kospi_df.index[-1].strftime('%Y-%m-%d')}")
        logger.info(f"  최근 종가: {kospi_df.iloc[-1]['close']:.2f}")
        
        # KOSPI 지수 범위 확인 (2000~4000)
        latest_close = kospi_df.iloc[-1]['close']
        if not (2000 <= latest_close <= 4000):
            logger.warning(f"  ⚠️ 경고: KOSPI 지수 값이 예상 범위를 벗어남 ({latest_close:.2f})")
        else:
            logger.info(f"  ✅ KOSPI 지수 범위 정상")
        
        # R20 계산 테스트
        if len(kospi_df) >= 21:
            close = kospi_df['close'].values
            r20 = (close[-1] / close[-21] - 1) * 100
            logger.info(f"  R20 (최근 20일): {r20:.2f}%")
            if abs(r20) > 10:
                logger.warning(f"  ⚠️ 경고: R20이 높음 ({r20:.2f}%)")
        
        # 캐시 저장
        kospi_df.to_pickle(cache_path)
        logger.info(f"\n✅ KOSPI 지수 캐시 저장 완료: {cache_path.absolute()}")
        
        return True
        
    except Exception as e:
        logger.error(f"KOSPI 캐시 수정 실패: {e}", exc_info=True)
        return False

def fix_vix_cache() -> bool:
    """VIX 캐시 단위 오류 수정 (10배 → 1배)"""
    try:
        cache_path = Path("data_cache/vix_ohlcv.pkl")
        
        if not cache_path.exists():
            logger.warning(f"VIX 캐시 파일 없음: {cache_path}")
            return False
        
        # 기존 캐시 백업
        backup_path = cache_path.with_suffix('.pkl.backup_10x')
        shutil.copy2(cache_path, backup_path)
        logger.info(f"기존 VIX 캐시 백업: {backup_path}")
        
        logger.info("=" * 70)
        logger.info("VIX 캐시 단위 오류 수정 시작")
        logger.info("=" * 70)
        
        # 캐시 로드
        with open(cache_path, 'rb') as f:
            vix_df = pickle.load(f)
        
        logger.info(f"기존 데이터: {len(vix_df)}개 행")
        logger.info(f"  최근 종가: {vix_df.iloc[-1]['close']:.2f}")
        
        # 단위 오류 확인
        latest_close = vix_df.iloc[-1]['close']
        
        # 이미 수정되었는지 확인 (10~50 범위면 이미 수정됨)
        if 10 <= latest_close <= 50:
            logger.info(f"  ✅ VIX 값이 이미 정상 범위입니다 ({latest_close:.2f})")
            logger.info(f"  수정 불필요")
            return True
        
        if latest_close > 50:
            logger.info(f"  ⚠️ 단위 오류 확인: {latest_close:.2f} (정상 범위: 10~50)")
            
            # 실제 VIX 값과 비교
            try:
                import yfinance as yf
                ticker = yf.Ticker("^VIX")
                df_yf = ticker.history(period="1mo")
                if not df_yf.empty:
                    real_vix = df_yf.iloc[-1]['Close']
                    logger.info(f"  실제 VIX 값: {real_vix:.2f}")
                    ratio = latest_close / real_vix
                    logger.info(f"  비율: {ratio:.2f}배")
                    
                    if 8 <= ratio <= 12:
                        logger.info(f"  ✅ 10배 단위 오류 확인됨")
                    else:
                        logger.warning(f"  ⚠️ 비율이 예상과 다름 (10배가 아님)")
            except Exception as e:
                logger.warning(f"  실제 VIX 값 확인 실패: {e}")
            
            # 단위 수정 (10으로 나누기)
            logger.info("\n단위 수정 중...")
            vix_df['close'] = vix_df['close'] / 10
            vix_df['open'] = vix_df['open'] / 10
            vix_df['high'] = vix_df['high'] / 10
            vix_df['low'] = vix_df['low'] / 10
        elif latest_close < 10:
            # 이미 수정되었거나 다른 문제
            logger.warning(f"  ⚠️ VIX 값이 너무 낮음: {latest_close:.2f}")
            logger.warning(f"  이미 수정되었거나 다른 문제가 있을 수 있습니다")
            
            # 실제 VIX 값과 비교하여 수정 필요 여부 확인
            try:
                import yfinance as yf
                ticker = yf.Ticker("^VIX")
                df_yf = ticker.history(period="1mo")
                if not df_yf.empty:
                    real_vix = df_yf.iloc[-1]['Close']
                    logger.info(f"  실제 VIX 값: {real_vix:.2f}")
                    ratio = real_vix / latest_close
                    logger.info(f"  비율: {ratio:.2f}배")
                    
                    if 8 <= ratio <= 12:
                        logger.info(f"  ✅ 10배로 곱해야 함 (이미 한 번 나눔)")
                        vix_df['close'] = vix_df['close'] * 10
                        vix_df['open'] = vix_df['open'] * 10
                        vix_df['high'] = vix_df['high'] * 10
                        vix_df['low'] = vix_df['low'] * 10
                    else:
                        logger.warning(f"  ⚠️ 비율이 예상과 다름")
                        return False
            except Exception as e:
                logger.warning(f"  실제 VIX 값 확인 실패: {e}")
                return False
        
        logger.info(f"수정 후 최근 종가: {vix_df.iloc[-1]['close']:.2f}")
        
        # 검증
        latest_close_fixed = vix_df.iloc[-1]['close']
        if 10 <= latest_close_fixed <= 50:
            logger.info(f"  ✅ VIX 값이 정상 범위로 수정됨")
        else:
            logger.warning(f"  ⚠️ 경고: VIX 값이 여전히 비정상적 ({latest_close_fixed:.2f})")
        
        # 통계
        logger.info(f"\n수정 후 통계:")
        logger.info(f"  평균: {vix_df['close'].mean():.2f}")
        logger.info(f"  최소: {vix_df['close'].min():.2f}")
        logger.info(f"  최대: {vix_df['close'].max():.2f}")
        
        # 캐시 저장
        vix_df.to_pickle(cache_path)
        logger.info(f"\n✅ VIX 캐시 수정 완료: {cache_path.absolute()}")
        
        return True
        
    except Exception as e:
        logger.error(f"VIX 캐시 수정 실패: {e}", exc_info=True)
        return False

def verify_fixes() -> bool:
    """수정 사항 검증"""
    logger.info("\n" + "=" * 70)
    logger.info("수정 사항 검증")
    logger.info("=" * 70)
    
    all_ok = True
    
    # KOSPI 검증
    kospi_path = Path("data_cache/kospi200_ohlcv.pkl")
    if kospi_path.exists():
        with open(kospi_path, 'rb') as f:
            kospi_df = pickle.load(f)
        
        latest_close = kospi_df.iloc[-1]['close']
        logger.info(f"\nKOSPI 검증:")
        logger.info(f"  최근 종가: {latest_close:.2f}")
        
        if 2000 <= latest_close <= 4000:
            logger.info(f"  ✅ KOSPI 지수 범위 정상")
        else:
            logger.error(f"  ❌ KOSPI 지수 범위 비정상")
            all_ok = False
        
        # R20 계산
        if len(kospi_df) >= 21:
            close = kospi_df['close'].values
            r20 = (close[-1] / close[-21] - 1) * 100
            logger.info(f"  R20: {r20:.2f}%")
            if abs(r20) > 15:
                logger.warning(f"  ⚠️ R20이 높음 (비정상적일 수 있음)")
    
    # VIX 검증
    vix_path = Path("data_cache/vix_ohlcv.pkl")
    if vix_path.exists():
        with open(vix_path, 'rb') as f:
            vix_df = pickle.load(f)
        
        latest_close = vix_df.iloc[-1]['close']
        logger.info(f"\nVIX 검증:")
        logger.info(f"  최근 종가: {latest_close:.2f}")
        
        if 10 <= latest_close <= 50:
            logger.info(f"  ✅ VIX 범위 정상")
        else:
            logger.error(f"  ❌ VIX 범위 비정상")
            all_ok = False
    
    return all_ok

def main():
    """메인 함수"""
    logger.info("=" * 70)
    logger.info("캐시 데이터 문제 해결 스크립트")
    logger.info("=" * 70)
    
    # 1. KOSPI 수정
    logger.info("\n[1/2] KOSPI 캐시 수정")
    kospi_success = fix_kospi_cache()
    
    # 2. VIX 수정
    logger.info("\n[2/2] VIX 캐시 수정")
    vix_success = fix_vix_cache()
    
    # 3. 검증
    verify_success = verify_fixes()
    
    # 최종 결과
    logger.info("\n" + "=" * 70)
    logger.info("최종 결과")
    logger.info("=" * 70)
    logger.info(f"KOSPI 수정: {'✅ 성공' if kospi_success else '❌ 실패'}")
    logger.info(f"VIX 수정: {'✅ 성공' if vix_success else '❌ 실패'}")
    logger.info(f"검증: {'✅ 통과' if verify_success else '❌ 실패'}")
    
    if kospi_success and vix_success and verify_success:
        logger.info("\n✅ 모든 수정 완료!")
        return 0
    else:
        logger.error("\n❌ 일부 수정 실패")
        return 1

if __name__ == "__main__":
    sys.exit(main())


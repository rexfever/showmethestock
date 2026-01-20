#!/usr/bin/env python3
"""
KOSPI 데이터 캐시 전체 재생성
- 기존 캐시 백업
- 처음부터 전체 데이터 수집
- 이상치 검증 및 필터링
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

def validate_data(df: pd.DataFrame) -> pd.DataFrame:
    """데이터 검증 및 이상치 필터링"""
    if df.empty:
        return df
    
    validated_df = df.copy()
    
    # 1. 가격 범위 검증 (KOSPI200 지수는 보통 2000~60000 범위)
    price_mask = (validated_df['close'] >= 1000) & (validated_df['close'] <= 100000)
    invalid_count = (~price_mask).sum()
    if invalid_count > 0:
        logger.warning(f"가격 범위를 벗어난 데이터: {invalid_count}개 행 제거")
        validated_df = validated_df[price_mask]
    
    # 2. 일일 수익률 검증 (일일 변동폭 ±20% 이상은 이상치)
    validated_df = validated_df.sort_index()
    daily_returns = validated_df['close'].pct_change()
    extreme_return_mask = daily_returns.abs() > 0.20
    
    if extreme_return_mask.any():
        extreme_count = extreme_return_mask.sum()
        logger.warning(f"일일 수익률 ±20% 이상: {extreme_count}개 행 발견")
        
        # 이상치를 전후 값의 선형 보간으로 대체
        for idx in validated_df[extreme_return_mask].index:
            date_idx = validated_df.index.get_loc(idx)
            if date_idx > 0 and date_idx < len(validated_df) - 1:
                prev_val = validated_df.iloc[date_idx - 1]['close']
                next_val = validated_df.iloc[date_idx + 1]['close']
                interpolated = (prev_val + next_val) / 2
                validated_df.loc[idx, 'close'] = interpolated
                validated_df.loc[idx, 'open'] = interpolated
                validated_df.loc[idx, 'high'] = interpolated
                validated_df.loc[idx, 'low'] = interpolated
                logger.debug(f"  {idx.strftime('%Y-%m-%d')}: {validated_df.loc[idx, 'close']:.2f} → {interpolated:.2f} (보간)")
    
    return validated_df

def regenerate_kospi_cache(start_date: str = '20200101', end_date: str = None, batch_size: int = 500) -> bool:
    """KOSPI 캐시 전체 재생성"""
    try:
        cache_path = Path("data_cache/kospi200_ohlcv.pkl")
        cache_dir = cache_path.parent
        cache_dir.mkdir(exist_ok=True)
        
        # 기존 캐시 백업
        if cache_path.exists():
            backup_path = cache_path.with_suffix('.pkl.backup')
            shutil.copy2(cache_path, backup_path)
            logger.info(f"기존 캐시 백업: {backup_path}")
        
        if end_date is None:
            end_date = datetime.now().strftime('%Y%m%d')
        
        logger.info(f"KOSPI 데이터 전체 재생성 시작: {start_date} ~ {end_date}")
        logger.info(f"배치 크기: {batch_size}일")
        
        all_data = []
        
        # 날짜 범위를 배치로 나누어 수집
        start = pd.to_datetime(start_date, format='%Y%m%d')
        end = pd.to_datetime(end_date, format='%Y%m%d')
        current = start
        
        batch_num = 0
        while current <= end:
            batch_num += 1
            batch_end = min(current + timedelta(days=batch_size), end)
            batch_end_str = batch_end.strftime('%Y%m%d')
            current_str = current.strftime('%Y%m%d')
            
            logger.info(f"\n배치 {batch_num}: {current_str} ~ {batch_end_str}")
            
            # 해당 기간의 데이터 수집
            # base_dt를 배치 종료일로 설정하고 충분한 count로 수집
            days_diff = (batch_end - current).days
            count = min(days_diff * 2, 500)  # 충분한 데이터 확보
            
            try:
                df_batch = api.get_ohlcv("069500", count=count, base_dt=batch_end_str)
                
                if df_batch.empty:
                    logger.warning(f"배치 {batch_num} 데이터 수집 실패")
                    current = batch_end + timedelta(days=1)
                    continue
                
                # 날짜 컬럼을 인덱스로 변환
                if 'date' in df_batch.columns:
                    df_batch['date'] = pd.to_datetime(df_batch['date'], format='%Y%m%d', errors='coerce')
                    df_batch = df_batch.set_index('date')
                elif not isinstance(df_batch.index, pd.DatetimeIndex):
                    logger.warning(f"배치 {batch_num} 날짜 인덱스 변환 실패")
                    current = batch_end + timedelta(days=1)
                    continue
                
                # 해당 기간의 데이터만 필터링
                df_batch = df_batch[(df_batch.index >= current) & (df_batch.index <= batch_end)]
                
                if not df_batch.empty:
                    all_data.append(df_batch)
                    logger.info(f"  수집: {len(df_batch)}개 행")
                
                # API 호출 제한 방지
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"배치 {batch_num} 수집 실패: {e}")
            
            current = batch_end + timedelta(days=1)
        
        if not all_data:
            logger.error("수집된 데이터가 없습니다")
            return False
        
        # 모든 데이터 병합
        logger.info("\n데이터 병합 중...")
        combined = pd.concat(all_data)
        combined = combined[~combined.index.duplicated(keep='last')]
        combined = combined.sort_index()
        
        logger.info(f"병합 완료: {len(combined)}개 행")
        logger.info(f"  시작일: {combined.index[0].strftime('%Y-%m-%d')}")
        logger.info(f"  종료일: {combined.index[-1].strftime('%Y-%m-%d')}")
        
        # 원본 데이터 그대로 저장 (검증/보정 없음)
        logger.info("\n원본 데이터 저장 중...")
        
        # 캐시 저장
        combined.to_pickle(cache_path)
        logger.info(f"\n✅ KOSPI 캐시 재생성 완료: {len(combined)}개 행 (원본 데이터)")
        logger.info(f"  저장 경로: {cache_path.absolute()}")
        
        # 최종 검증: 샘플 데이터 확인
        logger.info("\n최종 검증:")
        logger.info(f"  샘플 데이터 (최근 5일):")
        for date in combined.index[-5:]:
            logger.info(f"    {date.strftime('%Y-%m-%d')}: {combined.loc[date, 'close']:.2f}")
        
        # R20 계산 테스트
        if len(combined) >= 21:
            close = combined['close'].values
            r20 = (close[-1] / close[-21] - 1) * 100
            logger.info(f"\n  R20 계산 테스트 (최근 20일): {r20:.2f}%")
        
        return True
        
    except Exception as e:
        logger.error(f"KOSPI 캐시 재생성 실패: {e}", exc_info=True)
        return False

def main():
    """메인 함수"""
    logger.info("=" * 70)
    logger.info("KOSPI 데이터 캐시 전체 재생성")
    logger.info("=" * 70)
    
    # 시작일: 2020년 1월 1일부터
    start_date = '20200101'
    end_date = datetime.now().strftime('%Y%m%d')
    
    logger.info(f"대상 기간: {start_date} ~ {end_date}")
    
    success = regenerate_kospi_cache(start_date, end_date)
    
    if success:
        logger.info("\n" + "=" * 70)
        logger.info("✅ KOSPI 캐시 재생성 완료")
        logger.info("=" * 70)
    else:
        logger.error("\n" + "=" * 70)
        logger.error("❌ KOSPI 캐시 재생성 실패")
        logger.error("=" * 70)
        sys.exit(1)

if __name__ == "__main__":
    main()


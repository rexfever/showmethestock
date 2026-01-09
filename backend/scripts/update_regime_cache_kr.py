#!/usr/bin/env python3
"""
한국 주식 레짐 분석용 캐시 증분 업데이트 스크립트
스케줄러의 preload_regime_cache_kr() 함수를 스크립트로 변환
"""
import os
import sys

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from utils.regime_cache_manager import (
    update_kospi_cache_incremental,
    update_kosdaq_cache_incremental,
    update_us_futures_cache_incremental
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """한국 주식 레짐 분석용 캐시 증분 업데이트"""
    try:
        logger.info("📊 레짐 분석용 캐시 증분 업데이트 시작 (한국)")
        
        # 1. KOSPI 캐시 증분 업데이트
        try:
            update_kospi_cache_incremental()
        except Exception as e:
            logger.warning(f"KOSPI 캐시 증분 업데이트 실패: {e}")
        
        # 2. KOSDAQ 캐시 증분 업데이트
        try:
            update_kosdaq_cache_incremental()
        except Exception as e:
            logger.warning(f"KOSDAQ 캐시 증분 업데이트 실패: {e}")
        
        # 3. 미국 선물 캐시 증분 업데이트 (SPY, QQQ, VIX)
        try:
            update_us_futures_cache_incremental()
        except Exception as e:
            logger.error(f"미국 선물 캐시 증분 업데이트 실패: {e}")
        
        logger.info("✅ 레짐 분석용 캐시 증분 업데이트 완료 (한국)")
        
    except Exception as e:
        logger.error(f"레짐 분석용 캐시 증분 업데이트 중 오류 발생: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()


#!/usr/bin/env python3
"""
Regime Quality Validator + Simple Backtester 통합 실행 스크립트

사용법:
    python backend/regime_tools/run_regime_and_backtest.py --start 20250701 --end 20250930

옵션:
    --start: 시작일 (YYYYMMDD)
    --end: 종료일 (YYYYMMDD)
"""
import os
import sys
import argparse
import logging

# backend 디렉토리를 경로에 추가
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from regime_tools.regime_quality_validator import analyze_regime_quality
from backtest.simple_backtester_v2 import run_simple_backtest

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description='Regime Quality Validator + Simple Backtester')
    parser.add_argument('--start', type=str, required=True, help='시작일 (YYYYMMDD)')
    parser.add_argument('--end', type=str, required=True, help='종료일 (YYYYMMDD)')
    
    args = parser.parse_args()
    
    start_date = args.start
    end_date = args.end
    
    # 날짜 형식 검증
    try:
        from datetime import datetime
        datetime.strptime(start_date, '%Y%m%d')
        datetime.strptime(end_date, '%Y%m%d')
    except ValueError:
        logger.error("날짜 형식이 올바르지 않습니다. YYYYMMDD 형식을 사용하세요.")
        sys.exit(1)
    
    logger.info(f"\n{'='*80}")
    logger.info("Regime Quality Validator + Simple Backtester")
    logger.info(f"기간: {start_date} ~ {end_date}")
    logger.info(f"{'='*80}\n")
    
    # 1. 레짐 품질 검증
    logger.info("=" * 80)
    logger.info("1단계: 레짐 품질 검증")
    logger.info("=" * 80)
    
    try:
        regime_result = analyze_regime_quality(start_date, end_date)
        
        if 'error' in regime_result:
            logger.error(f"레짐 품질 검증 실패: {regime_result['error']}")
        else:
            logger.info("\n✅ 레짐 품질 검증 완료")
    except Exception as e:
        logger.error(f"레짐 품질 검증 중 오류 발생: {e}", exc_info=True)
        regime_result = {'error': str(e)}
    
    # 2. 백테스트
    logger.info("\n" + "=" * 80)
    logger.info("2단계: 백테스트")
    logger.info("=" * 80)
    
    try:
        backtest_result = run_simple_backtest(start_date, end_date)
        
        if 'error' in backtest_result:
            logger.error(f"백테스트 실패: {backtest_result['error']}")
        else:
            logger.info("\n✅ 백테스트 완료")
    except Exception as e:
        logger.error(f"백테스트 중 오류 발생: {e}", exc_info=True)
        backtest_result = {'error': str(e)}
    
    # 3. 통합 결과 요약
    logger.info("\n" + "=" * 80)
    logger.info("통합 결과 요약")
    logger.info("=" * 80)
    
    if 'error' not in regime_result:
        logger.info("\n📊 레짐 품질 검증:")
        logger.info(f"   - 분석 일수: {regime_result.get('total_days', 0)}일")
        logger.info(f"   - 매칭률:")
        for regime, rate in regime_result.get('matching_rates', {}).items():
            logger.info(f"     * {regime.upper()}: {rate*100:.1f}%")
    
    if 'error' not in backtest_result:
        logger.info("\n📈 백테스트 결과:")
        for horizon, stats in backtest_result.get('horizon_results', {}).items():
            logger.info(f"   - {horizon.upper()}:")
            logger.info(f"     * 트레이드: {stats['total_trades']}건")
            logger.info(f"     * 승률: {stats['win_rate']*100:.1f}%")
            logger.info(f"     * CAGR: {stats['cagr']*100:.2f}%")
            logger.info(f"     * MDD: {stats['mdd']*100:.2f}%")
    
    logger.info("\n" + "=" * 80)
    logger.info("완료")
    logger.info("=" * 80)


if __name__ == '__main__':
    main()


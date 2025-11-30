"""
크래시 날짜만 재스캔 스크립트

DB에서 midterm_regime이 'crash'인 날짜들을 찾아서 재스캔 실행
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
import json
import logging
from db_manager import db_manager
from tools.rescan_date import rescan_date

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_crash_dates(include_bear: bool = True) -> list:
    """크래시 날짜 목록 조회 (bear 포함 옵션)"""
    crash_dates = []
    
    try:
        with db_manager.get_cursor(commit=False) as cur:
            # crash 또는 bear 날짜 조회
            if include_bear:
                cur.execute("""
                    SELECT date, final_regime, kr_metrics
                    FROM market_regime_daily
                    WHERE version = 'regime_v4'
                    AND (
                        final_regime = 'crash' OR 
                        kr_metrics->>'midterm_regime' = 'crash' OR
                        final_regime = 'bear' OR 
                        kr_metrics->>'midterm_regime' = 'bear'
                    )
                    ORDER BY date
                """)
            else:
                cur.execute("""
                    SELECT date, final_regime, kr_metrics
                    FROM market_regime_daily
                    WHERE version = 'regime_v4'
                    AND (
                        final_regime = 'crash' OR 
                        kr_metrics->>'midterm_regime' = 'crash'
                    )
                    ORDER BY date
                """)
            
            rows = cur.fetchall()
            
            for row in rows:
                date_val = row[0]
                if hasattr(date_val, 'strftime'):
                    date_str = date_val.strftime('%Y%m%d')
                else:
                    date_str = str(date_val).replace('-', '')
                
                final_regime = row[1]
                kr_metrics = row[2]
                
                # kr_metrics에서 midterm_regime 확인
                midterm_regime = None
                if kr_metrics:
                    if isinstance(kr_metrics, dict):
                        midterm_regime = kr_metrics.get('midterm_regime')
                    elif isinstance(kr_metrics, str):
                        try:
                            kr_metrics_dict = json.loads(kr_metrics)
                            midterm_regime = kr_metrics_dict.get('midterm_regime')
                        except:
                            pass
                
                # crash 또는 bear인 경우 추가
                is_crash = (final_regime == 'crash' or midterm_regime == 'crash')
                is_bear = (final_regime == 'bear' or midterm_regime == 'bear')
                
                if is_crash or (include_bear and is_bear):
                    crash_dates.append({
                        'date': date_str,
                        'final_regime': final_regime,
                        'midterm_regime': midterm_regime,
                        'type': 'crash' if is_crash else 'bear'
                    })
        
        return crash_dates
    except Exception as e:
        logger.error(f"크래시 날짜 조회 실패: {e}")
        return []


def main():
    """크래시 날짜 재스캔 실행"""
    logger.info(f"\n{'='*80}")
    logger.info("크래시/베어 날짜 재스캔 시작")
    logger.info(f"{'='*80}\n")
    
    # 1. 크래시 날짜 조회 (bear 포함)
    crash_dates = get_crash_dates(include_bear=True)
    
    if not crash_dates:
        logger.warning("크래시/베어 날짜가 없습니다.")
        logger.info("현재 DB에 crash 레짐이 없습니다. 레짐 분석을 다시 실행하거나,")
        logger.info("특정 날짜 범위를 지정하여 재스캔하세요.")
        return
    
    logger.info(f"📊 크래시/베어 날짜: {len(crash_dates)}일")
    for item in crash_dates:
        logger.info(f"   - {item['date']}: {item['type']} (final={item['final_regime']}, midterm={item['midterm_regime']})")
    
    logger.info(f"\n{'='*80}")
    logger.info(f"재스캔 시작: {len(crash_dates)}일")
    logger.info(f"{'='*80}\n")
    
    # 2. 각 날짜별 재스캔 실행
    success_count = 0
    error_count = 0
    
    for i, item in enumerate(crash_dates, 1):
        date_str = item['date']
        logger.info(f"\n[{i}/{len(crash_dates)}] {date_str} 재스캔 중...")
        
        try:
            # skip_existing=False로 강제 재스캔
            result = rescan_date(date_str, skip_existing=False)
            if result:
                success_count += 1
                logger.info(f"  ✅ {date_str} 재스캔 완료")
            else:
                error_count += 1
                logger.warning(f"  ⚠️ {date_str} 재스캔 실패")
        except Exception as e:
            error_count += 1
            logger.error(f"  ❌ {date_str} 재스캔 오류: {e}")
            continue
    
    # 3. 결과 요약
    logger.info(f"\n{'='*80}")
    logger.info("재스캔 완료")
    logger.info(f"{'='*80}")
    logger.info(f"✅ 성공: {success_count}일")
    logger.info(f"❌ 실패: {error_count}일")
    logger.info(f"📊 총 {len(crash_dates)}일 중 {success_count}일 완료")


if __name__ == '__main__':
    main()


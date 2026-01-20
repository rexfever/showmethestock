#!/usr/bin/env python3
"""
ARCHIVED 일괄 전이 배치 스크립트

목표:
- anchor_date 기준으로 20거래일 이상 경과한 ACTIVE 추천을 ARCHIVED로 전이
- stop_loss 미도달인 경우만 ARCHIVED로 전이 (BROKEN은 제외)

실행:
  python3 backend/scripts/batch_archive_old_recommendations.py [--dry-run]
"""

import sys
import os
import argparse
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from db_manager import db_manager
from services.state_transition_service import get_trading_days_since, transition_recommendation_status
from date_helper import get_kst_now, yyyymmdd_to_date
from kiwoom_api import api
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def batch_archive_old_recommendations(dry_run: bool = False) -> dict:
    """
    anchor_date 기준으로 20거래일 이상 경과한 ACTIVE 추천을 ARCHIVED로 전이
    
    Args:
        dry_run: True면 실제 전이하지 않고 로그만 출력
        
    Returns:
        통계 딕셔너리
    """
    today_str = get_kst_now().strftime('%Y%m%d')
    logger.info(f"[batch_archive_old_recommendations] 시작: today={today_str}, dry_run={dry_run}")
    
    stats = {
        'total_active': 0,
        'evaluated': 0,
        'archived_ttl': 0,
        'archived_no_performance': 0,
        'skipped_broken': 0,
        'skipped_no_anchor_date': 0,
        'skipped_insufficient_days': 0,
        'errors': 0
    }
    
    try:
        with db_manager.get_cursor(commit=False) as cur:
            # ACTIVE 상태인 추천 조회 (anchor_date 기준)
            cur.execute("""
                SELECT 
                    recommendation_id, ticker, status, anchor_date, anchor_close,
                    strategy, flags
                FROM recommendations
                WHERE status = 'ACTIVE'
                AND scanner_version = 'v3'
                ORDER BY anchor_date ASC, ticker
            """)
            
            rows = cur.fetchall()
            stats['total_active'] = len(rows)
            
            logger.info(f"[batch_archive_old_recommendations] ACTIVE 추천: {len(rows)}개")
            
            for row in rows:
                try:
                    if isinstance(row, dict):
                        rec_id = row.get('recommendation_id')
                        ticker = row.get('ticker')
                        anchor_date = row.get('anchor_date')
                        anchor_close = row.get('anchor_close')
                        strategy = row.get('strategy')
                        flags = row.get('flags')
                    else:
                        rec_id = row[0]
                        ticker = row[1]
                        anchor_date = row[3]
                        anchor_close = row[4]
                        strategy = row[5]
                        flags = row[6]
                    
                    if not ticker or ticker == 'NORESULT':
                        continue
                    
                    if not anchor_date:
                        stats['skipped_no_anchor_date'] += 1
                        logger.warning(f"[batch_archive_old_recommendations] anchor_date 없음: {ticker}, 건너뜀")
                        continue
                    
                    # anchor_date를 date 객체로 변환
                    anchor_date_obj = None
                    if isinstance(anchor_date, str):
                        anchor_date_obj = yyyymmdd_to_date(anchor_date.replace('-', '')[:8])
                    elif hasattr(anchor_date, 'year'):  # date 객체
                        anchor_date_obj = anchor_date
                    elif hasattr(anchor_date, 'date'):  # datetime 객체
                        anchor_date_obj = anchor_date.date()
                    
                    if not anchor_date_obj:
                        stats['skipped_no_anchor_date'] += 1
                        logger.warning(f"[batch_archive_old_recommendations] anchor_date 파싱 실패: {ticker}, 건너뜀")
                        continue
                    
                    # 거래일 수 계산 (anchor_date 기준)
                    trading_days = get_trading_days_since(anchor_date_obj)
                    
                    # 20거래일 미만이면 건너뛰기
                    if trading_days < 20:
                        stats['skipped_insufficient_days'] += 1
                        logger.debug(f"[batch_archive_old_recommendations] 거래일 부족: {ticker}, trading_days={trading_days}")
                        continue
                    
                    stats['evaluated'] += 1
                    
                    # flags 파싱
                    if isinstance(flags, str):
                        try:
                            flags_dict = json.loads(flags)
                        except:
                            flags_dict = {}
                    else:
                        flags_dict = flags or {}
                    
                    # 이미 BROKEN인지 확인 (flags에 broken 표시)
                    if flags_dict.get("assumption_broken") == True or flags_dict.get("flow_broken") == True:
                        stats['skipped_broken'] += 1
                        logger.debug(f"[batch_archive_old_recommendations] 이미 BROKEN: {ticker}, 건너뜀")
                        continue
                    
                    # anchor_close 확인
                    if not anchor_close or anchor_close <= 0:
                        logger.warning(f"[batch_archive_old_recommendations] anchor_close 없음: {ticker}, 건너뜀")
                        continue
                    
                    # 오늘 종가 조회
                    try:
                        df_today = api.get_ohlcv(ticker, 1, today_str)
                        if df_today.empty:
                            logger.warning(f"[batch_archive_old_recommendations] 오늘 종가 없음: {ticker}, 건너뜀")
                            continue
                        
                        today_close = float(df_today.iloc[-1]['close'])
                    except Exception as e:
                        logger.warning(f"[batch_archive_old_recommendations] 종가 조회 실패: {ticker}, {e}")
                        continue
                    
                    # current_return 계산
                    current_return = ((today_close - anchor_close) / anchor_close) * 100
                    
                    # stop_loss 확인
                    stop_loss = flags_dict.get("stop_loss")
                    if stop_loss is None:
                        if strategy == "v2_lite":
                            stop_loss = 0.02
                        elif strategy == "midterm":
                            stop_loss = 0.07
                        else:
                            stop_loss = 0.02
                    
                    stop_loss_pct = -abs(float(stop_loss) * 100)
                    
                    # BROKEN 조건 확인 (최우선)
                    if current_return <= stop_loss_pct:
                        # BROKEN으로 전이해야 함 (이 배치는 ARCHIVED만 처리)
                        logger.info(f"[batch_archive_old_recommendations] BROKEN 조건 만족: {ticker}, current_return={current_return:.2f}%, 건너뜀 (상태 전이 프로세스에서 처리)")
                        continue
                    
                    # ARCHIVED 전이 조건 확인
                    archived_reason = None
                    should_archive = False
                    
                    # A) TTL 종료 (20거래일 이상)
                    if trading_days >= 20:
                        archived_reason = f'TTL_20_DAYS: trading_days={trading_days}'
                        should_archive = True
                        stats['archived_ttl'] += 1
                    
                    # B) 무성과 종료 (10거래일 이상 + abs(return) < 2%)
                    elif trading_days >= 10 and abs(current_return) < 2.0:
                        archived_reason = f'NO_PERFORMANCE: trading_days={trading_days}, return={current_return:.2f}%'
                        should_archive = True
                        stats['archived_no_performance'] += 1
                    
                    if should_archive:
                        logger.info(f"[batch_archive_old_recommendations] ARCHIVED 전이: {ticker}, {archived_reason}")
                        
                        if not dry_run:
                            # 상태 전이 (v2 transaction 함수 사용)
                            # 스냅샷 정보를 metadata에 포함
                            success = transition_recommendation_status(
                                rec_id,
                                'ARCHIVED',
                                archived_reason,
                                {
                                    "trading_days": trading_days,
                                    "current_return": round(current_return, 2),
                                    "current_price": today_close,  # ARCHIVED 전환 시점 가격
                                    "anchor_close": anchor_close,  # 추천 기준 가격
                                    "reason": archived_reason,
                                    "anchor_date": str(anchor_date_obj)
                                }
                            )
                            
                            if not success:
                                logger.error(f"[batch_archive_old_recommendations] ARCHIVED 전이 실패: {ticker}")
                                stats['errors'] += 1
                        else:
                            logger.info(f"[batch_archive_old_recommendations] [DRY RUN] ARCHIVED 전이 예정: {ticker}, {archived_reason}")
                
                except Exception as e:
                    logger.error(f"[batch_archive_old_recommendations] 평가 오류 ({ticker}): {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    stats['errors'] += 1
        
        logger.info(f"[batch_archive_old_recommendations] 완료: {stats}")
        return stats
        
    except Exception as e:
        logger.error(f"[batch_archive_old_recommendations] 배치 실행 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())
        stats['errors'] += 1
        return stats


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='ARCHIVED 일괄 전이 배치')
    parser.add_argument('--dry-run', action='store_true', help='실제 전이하지 않고 로그만 출력')
    args = parser.parse_args()
    
    stats = batch_archive_old_recommendations(dry_run=args.dry_run)
    
    print("\n" + "=" * 80)
    print("배치 실행 결과")
    print("=" * 80)
    print(f"총 ACTIVE: {stats['total_active']}개")
    print(f"평가 완료: {stats['evaluated']}개")
    print(f"ARCHIVED 전이 (TTL): {stats['archived_ttl']}개")
    print(f"ARCHIVED 전이 (무성과): {stats['archived_no_performance']}개")
    print(f"건너뜀 (BROKEN): {stats['skipped_broken']}개")
    print(f"건너뜀 (anchor_date 없음): {stats['skipped_no_anchor_date']}개")
    print(f"건너뜀 (거래일 부족): {stats['skipped_insufficient_days']}개")
    print(f"오류: {stats['errors']}개")


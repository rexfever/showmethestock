#!/usr/bin/env python3
"""
기존 ARCHIVED 데이터 스냅샷 보정 마이그레이션

이미 ARCHIVED 상태인데 스냅샷이 없는 레코드를 보정합니다.
"""
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from db_manager import db_manager
from date_helper import get_kst_now
from kiwoom_api import api
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def migrate_existing_archived_snapshots(dry_run: bool = True) -> dict:
    """
    기존 ARCHIVED 데이터 스냅샷 보정
    
    Args:
        dry_run: True면 실제 업데이트하지 않고 로그만 출력
        
    Returns:
        통계 딕셔너리
    """
    stats = {
        'total_archived': 0,
        'needs_snapshot': 0,
        'updated': 0,
        'skipped': 0,
        'errors': 0
    }
    
    try:
        with db_manager.get_cursor(commit=False) as cur:
            # ARCHIVED 상태인 추천 조회 (스냅샷이 없는 것만)
            cur.execute("""
                SELECT 
                    recommendation_id, ticker, anchor_date, anchor_close,
                    status_changed_at, updated_at, archived_at
                FROM recommendations
                WHERE status = 'ARCHIVED'
                  AND scanner_version = 'v3'
                  AND (archive_at IS NULL OR archive_return_pct IS NULL OR archive_reason IS NULL)
                ORDER BY anchor_date DESC
            """)
            
            rows = cur.fetchall()
            stats['total_archived'] = len(rows)
            stats['needs_snapshot'] = len(rows)
            
            logger.info(f"[migrate_existing_archived_snapshots] 스냅샷 보정 필요: {len(rows)}개")
            
            for row in rows:
                try:
                    if isinstance(row, dict):
                        rec_id = row.get('recommendation_id')
                        ticker = row.get('ticker')
                        anchor_date = row.get('anchor_date')
                        anchor_close = row.get('anchor_close')
                        status_changed_at = row.get('status_changed_at')
                        updated_at = row.get('updated_at')
                        archived_at = row.get('archived_at')
                    else:
                        rec_id = row[0]
                        ticker = row[1]
                        anchor_date = row[2]
                        anchor_close = row[3]
                        status_changed_at = row[4]
                        updated_at = row[5]
                        archived_at = row[6]
                    
                    if not ticker or ticker == 'NORESULT':
                        stats['skipped'] += 1
                        continue
                    
                    # archive_at 결정 (우선순위: status_changed_at > archived_at > updated_at)
                    archive_at = status_changed_at or archived_at or updated_at
                    
                    # archive_reason 추정 (TTL 기준으로 간단히 판단)
                    # anchor_date로부터 경과일 계산
                    if anchor_date:
                        if isinstance(anchor_date, str):
                            anchor_date_obj = datetime.strptime(anchor_date[:10], '%Y-%m-%d').date()
                        else:
                            anchor_date_obj = anchor_date
                        
                        if archive_at:
                            if isinstance(archive_at, str):
                                archive_date_obj = datetime.fromisoformat(archive_at.replace('Z', '+00:00')).date()
                            else:
                                archive_date_obj = archive_at.date() if hasattr(archive_at, 'date') else archive_at
                            
                            days_diff = (archive_date_obj - anchor_date_obj).days
                            
                            # 20일 이상이면 TTL_EXPIRED로 추정
                            if days_diff >= 20:
                                archive_reason = 'TTL_EXPIRED'
                            else:
                                archive_reason = 'NO_MOMENTUM'
                        else:
                            archive_reason = 'MANUAL_ARCHIVE'
                    else:
                        archive_reason = 'MANUAL_ARCHIVE'
                    
                    # archive_price와 archive_return_pct 계산 시도
                    archive_price = None
                    archive_return_pct = None
                    archive_phase = None
                    
                    if anchor_close and anchor_close > 0:
                        # archive_at 시점의 가격 조회 시도
                        if archive_at:
                            try:
                                if isinstance(archive_at, str):
                                    archive_date_str = archive_at[:10].replace('-', '')
                                else:
                                    archive_date_str = archive_at.strftime('%Y%m%d') if hasattr(archive_at, 'strftime') else str(archive_at)[:8]
                                
                                # 과거 가격 조회 (최대 30일 전까지)
                                df_archive = api.get_ohlcv(ticker, 30, archive_date_str)
                                if not df_archive.empty:
                                    # archive_date_str에 가장 가까운 날짜의 종가 사용
                                    archive_price = float(df_archive.iloc[-1]['close'])
                                    archive_return_pct = round(((archive_price - float(anchor_close)) / float(anchor_close)) * 100, 2)
                                    
                                    # archive_phase 결정
                                    if archive_return_pct > 2:
                                        archive_phase = 'PROFIT'
                                    elif archive_return_pct < -2:
                                        archive_phase = 'LOSS'
                                    else:
                                        archive_phase = 'FLAT'
                            except Exception as e:
                                logger.debug(f"[migrate_existing_archived_snapshots] 가격 조회 실패 ({ticker}): {e}")
                    
                    if not dry_run:
                        # 스냅샷 업데이트
                        with db_manager.get_cursor(commit=True) as update_cur:
                            update_cur.execute("""
                                UPDATE recommendations
                                SET archive_at = COALESCE(%s, archive_at, updated_at),
                                    archive_reason = COALESCE(archive_reason, %s),
                                    archive_return_pct = COALESCE(archive_return_pct, %s),
                                    archive_price = COALESCE(archive_price, %s),
                                    archive_phase = COALESCE(archive_phase, %s)
                                WHERE recommendation_id = %s
                            """, (
                                archive_at,
                                archive_reason,
                                archive_return_pct,
                                archive_price,
                                archive_phase,
                                rec_id
                            ))
                            stats['updated'] += 1
                            logger.info(f"[migrate_existing_archived_snapshots] 스냅샷 보정 완료: {ticker} (reason={archive_reason}, return={archive_return_pct}%)")
                    else:
                        logger.info(f"[migrate_existing_archived_snapshots] [DRY RUN] 스냅샷 보정 예정: {ticker} (reason={archive_reason}, return={archive_return_pct}%)")
                        stats['updated'] += 1
                        
                except Exception as e:
                    logger.error(f"[migrate_existing_archived_snapshots] 보정 오류 ({ticker}): {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    stats['errors'] += 1
            
            return stats
            
    except Exception as e:
        logger.error(f"[migrate_existing_archived_snapshots] 마이그레이션 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return stats


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='기존 ARCHIVED 데이터 스냅샷 보정')
    parser.add_argument('--execute', action='store_true', help='실제 업데이트 실행 (기본값: dry-run)')
    args = parser.parse_args()
    
    dry_run = not args.execute
    logger.info(f"[migrate_existing_archived_snapshots] 시작: dry_run={dry_run}")
    
    stats = migrate_existing_archived_snapshots(dry_run=dry_run)
    
    logger.info(f"[migrate_existing_archived_snapshots] 완료:")
    logger.info(f"  - 총 ARCHIVED: {stats['total_archived']}개")
    logger.info(f"  - 스냅샷 보정 필요: {stats['needs_snapshot']}개")
    logger.info(f"  - 보정 완료: {stats['updated']}개")
    logger.info(f"  - 건너뜀: {stats['skipped']}개")
    logger.info(f"  - 오류: {stats['errors']}개")




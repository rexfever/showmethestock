"""
잘못된 스캔 데이터 수정 스크립트
실제 데이터와 비교하여 잘못된 종가/등락률을 수정
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from db_manager import db_manager
from kiwoom_api import api
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_incorrect_data(code: str = None, start_date: str = None, end_date: str = None, dry_run: bool = True):
    """
    잘못된 스캔 데이터 수정
    
    Args:
        code: 특정 종목 코드 (None이면 전체)
        start_date: 시작 날짜 (YYYYMMDD)
        end_date: 종료 날짜 (YYYYMMDD)
        dry_run: True면 수정하지 않고 확인만
    """
    logger.info("=" * 80)
    logger.info("잘못된 스캔 데이터 수정")
    logger.info("=" * 80)
    
    # 날짜 범위 설정
    if start_date:
        start = datetime.strptime(start_date, '%Y%m%d').date()
    else:
        start = datetime(2025, 7, 1).date()
    
    if end_date:
        end = datetime.strptime(end_date, '%Y%m%d').date()
    else:
        end = datetime.now().date()
    
    # 조회할 데이터
    with db_manager.get_cursor() as cur:
        if code:
            cur.execute("""
                SELECT date, code, name, close_price, change_rate, score, indicators
                FROM scan_rank
                WHERE code = %s 
                AND scanner_version = 'v2'
                AND date >= %s AND date <= %s
                AND code != 'NORESULT'
                ORDER BY date DESC
            """, (code, start, end))
        else:
            cur.execute("""
                SELECT date, code, name, close_price, change_rate, score, indicators
                FROM scan_rank
                WHERE scanner_version = 'v2'
                AND date >= %s AND date <= %s
                AND code != 'NORESULT'
                ORDER BY date DESC
            """, (start, end))
        
        all_data = cur.fetchall()
    
    logger.info(f"\n검증 대상: {len(all_data)}개")
    
    fixed_count = 0
    error_count = 0
    
    for date, code, name, db_close, db_change_rate, score, indicators in all_data:
        date_str = date.strftime('%Y%m%d') if hasattr(date, 'strftime') else str(date).replace('-', '')
        
        try:
            df = api.get_ohlcv(code, 2, date_str)
            if df.empty or len(df) < 2:
                continue
            
            prev_close = df.iloc[-2]['close']
            curr_close = df.iloc[-1]['close']
            actual_change_rate = (curr_close / prev_close - 1) * 100
            
            close_diff = abs(db_close - curr_close) if db_close else 999999
            rate_diff = abs(db_change_rate - actual_change_rate) if db_change_rate else 999999
            
            # 수정 필요 여부 확인
            needs_fix = False
            fix_reasons = []
            
            if close_diff > 0.01:
                needs_fix = True
                fix_reasons.append(f"종가 불일치 ({close_diff:.0f}원)")
            
            if rate_diff > 0.1:
                needs_fix = True
                fix_reasons.append(f"등락률 불일치 ({rate_diff:.2f}%)")
            
            if needs_fix:
                logger.info(f"\n{date_str} {code} ({name}):")
                logger.info(f"  문제: {', '.join(fix_reasons)}")
                logger.info(f"  DB: 종가={db_close:,.0f}원, 등락률={db_change_rate:.2f}%")
                logger.info(f"  실제: 종가={curr_close:,.0f}원, 등락률={actual_change_rate:.2f}%")
                
                if not dry_run:
                    # DB 업데이트
                    with db_manager.get_cursor(commit=True) as cur:
                        cur.execute("""
                            UPDATE scan_rank
                            SET close_price = %s,
                                change_rate = %s
                            WHERE date = %s AND code = %s AND scanner_version = 'v2'
                        """, (curr_close, round(actual_change_rate, 2), date, code))
                    
                    logger.info(f"  ✅ 수정 완료")
                    fixed_count += 1
                else:
                    logger.info(f"  [DRY RUN] 수정 예정")
                    fixed_count += 1
        except Exception as e:
            logger.error(f"  ❌ 오류 ({code} {date_str}): {e}")
            error_count += 1
    
    logger.info("\n" + "=" * 80)
    logger.info("수정 완료")
    logger.info("=" * 80)
    logger.info(f"  수정 대상: {fixed_count}개")
    logger.info(f"  오류: {error_count}개")
    
    if dry_run:
        logger.info(f"\n⚠️ DRY RUN 모드입니다. 실제 수정을 하려면 --no-dry-run 옵션을 사용하세요.")

def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='잘못된 스캔 데이터 수정')
    parser.add_argument('--code', type=str, help='특정 종목 코드')
    parser.add_argument('--start', type=str, help='시작 날짜 (YYYYMMDD)')
    parser.add_argument('--end', type=str, help='종료 날짜 (YYYYMMDD)')
    parser.add_argument('--no-dry-run', action='store_true', help='실제로 수정 (기본값: dry-run)')
    
    args = parser.parse_args()
    
    fix_incorrect_data(
        code=args.code,
        start_date=args.start,
        end_date=args.end,
        dry_run=not args.no_dry_run
    )

if __name__ == "__main__":
    main()





































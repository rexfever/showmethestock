#!/usr/bin/env python3
"""
백필 범위 실행 스크립트
- 여러 월/분기/연도를 한 번에 처리
- 진행 상황 모니터링
- 실패 시 재시도 기능
"""
import argparse
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_month_range(year: int, month: int) -> tuple:
    """월의 시작일과 종료일 반환"""
    start_date = datetime(year, month, 1)
    
    if month == 12:
        next_month = datetime(year + 1, 1, 1)
    else:
        next_month = datetime(year, month + 1, 1)
    
    end_date = next_month - timedelta(days=1)
    
    return start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')

def run_backfill(start_date: str, end_date: str, workers: int = 4) -> bool:
    """백필 실행"""
    script_dir = Path(__file__).parent
    backfill_script = script_dir / "run_backfill.sh"
    
    if not backfill_script.exists():
        logger.error(f"백필 스크립트를 찾을 수 없습니다: {backfill_script}")
        return False
    
    try:
        logger.info(f"백필 실행: {start_date} ~ {end_date} (워커: {workers})")
        
        result = subprocess.run([
            "bash", str(backfill_script), start_date, end_date, str(workers)
        ], check=True, capture_output=True, text=True)
        
        logger.info(f"백필 완료: {start_date} ~ {end_date}")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"백필 실패: {start_date} ~ {end_date}")
        logger.error(f"오류: {e.stderr}")
        return False

def run_monthly_range(start_year: int, start_month: int, 
                     end_year: int, end_month: int, workers: int = 4) -> None:
    """월별 범위 백필 실행"""
    current_year = start_year
    current_month = start_month
    
    total_months = (end_year - start_year) * 12 + (end_month - start_month) + 1
    completed_months = 0
    failed_months = []
    
    logger.info(f"월별 백필 시작: {start_year}-{start_month:02d} ~ {end_year}-{end_month:02d}")
    logger.info(f"총 {total_months}개월 처리 예정")
    
    while (current_year < end_year) or (current_year == end_year and current_month <= end_month):
        start_date, end_date = get_month_range(current_year, current_month)
        
        logger.info(f"진행률: {completed_months}/{total_months} ({completed_months/total_months*100:.1f}%)")
        
        if run_backfill(start_date, end_date, workers):
            completed_months += 1
        else:
            failed_months.append(f"{current_year}-{current_month:02d}")
        
        # 다음 달로 이동
        if current_month == 12:
            current_year += 1
            current_month = 1
        else:
            current_month += 1
    
    # 결과 요약
    logger.info(f"백필 완료: {completed_months}/{total_months}개월")
    
    if failed_months:
        logger.warning(f"실패한 월: {', '.join(failed_months)}")
        
        # 재시도 여부 확인
        retry = input("실패한 월을 재시도하시겠습니까? (y/N): ").strip().lower()
        if retry == 'y':
            logger.info("실패한 월 재시도 중...")
            for failed_month in failed_months:
                year, month = map(int, failed_month.split('-'))
                start_date, end_date = get_month_range(year, month)
                run_backfill(start_date, end_date, workers)
    else:
        logger.info("모든 월 백필 성공!")

def run_quarterly_range(start_year: int, start_quarter: int,
                       end_year: int, end_quarter: int, workers: int = 4) -> None:
    """분기별 범위 백필 실행"""
    quarter_months = {
        1: [1, 2, 3],
        2: [4, 5, 6], 
        3: [7, 8, 9],
        4: [10, 11, 12]
    }
    
    current_year = start_year
    current_quarter = start_quarter
    
    logger.info(f"분기별 백필 시작: {start_year}Q{start_quarter} ~ {end_year}Q{end_quarter}")
    
    while (current_year < end_year) or (current_year == end_year and current_quarter <= end_quarter):
        months = quarter_months[current_quarter]
        start_month = months[0]
        end_month = months[-1]
        
        logger.info(f"처리 중: {current_year}Q{current_quarter} ({start_month}월-{end_month}월)")
        
        # 분기의 시작일과 종료일 계산
        start_date = f"{current_year}-{start_month:02d}-01"
        end_date, _ = get_month_range(current_year, end_month)
        
        run_backfill(start_date, end_date, workers)
        
        # 다음 분기로 이동
        if current_quarter == 4:
            current_year += 1
            current_quarter = 1
        else:
            current_quarter += 1

def main():
    parser = argparse.ArgumentParser(description='백필 범위 실행 스크립트')
    parser.add_argument('--mode', choices=['monthly', 'quarterly'], required=True,
                       help='실행 모드')
    parser.add_argument('--start-year', type=int, required=True, help='시작 연도')
    parser.add_argument('--end-year', type=int, required=True, help='종료 연도')
    parser.add_argument('--workers', type=int, default=4, help='워커 수 (기본값: 4)')
    
    # 월별 모드 옵션
    parser.add_argument('--start-month', type=int, help='시작 월 (1-12)')
    parser.add_argument('--end-month', type=int, help='종료 월 (1-12)')
    
    # 분기별 모드 옵션
    parser.add_argument('--start-quarter', type=int, choices=[1,2,3,4], help='시작 분기 (1-4)')
    parser.add_argument('--end-quarter', type=int, choices=[1,2,3,4], help='종료 분기 (1-4)')
    
    args = parser.parse_args()
    
    try:
        if args.mode == 'monthly':
            if not args.start_month or not args.end_month:
                parser.error("월별 모드에서는 --start-month와 --end-month가 필요합니다")
            
            run_monthly_range(
                args.start_year, args.start_month,
                args.end_year, args.end_month,
                args.workers
            )
            
        elif args.mode == 'quarterly':
            if not args.start_quarter or not args.end_quarter:
                parser.error("분기별 모드에서는 --start-quarter와 --end-quarter가 필요합니다")
            
            run_quarterly_range(
                args.start_year, args.start_quarter,
                args.end_year, args.end_quarter,
                args.workers
            )
            
    except KeyboardInterrupt:
        logger.info("사용자에 의해 중단되었습니다")
        sys.exit(1)
    except Exception as e:
        logger.error(f"실행 중 오류 발생: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
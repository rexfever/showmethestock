#!/usr/bin/env python3
"""
7월 2,3,4,5주차 보고서 및 월간 보고서 생성 스크립트
"""
import sys
import os
import logging

# 프로젝트 루트 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.services.report_generator import ReportGenerator

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """7월 보고서 생성"""
    generator = ReportGenerator()
    
    year = 2025
    month = 7
    
    print(f"=== {year}년 {month}월 보고서 생성 시작 ===")
    
    # 2,3,4,5주차 보고서 생성
    weeks = [2, 3, 4, 5]
    success_count = 0
    
    for week in weeks:
        print(f"\n--- {week}주차 보고서 생성 중 ---")
        try:
            success = generator.generate_weekly_report(year, month, week)
            if success:
                print(f"✅ {week}주차 보고서 생성 완료")
                success_count += 1
            else:
                print(f"❌ {week}주차 보고서 생성 실패")
        except Exception as e:
            print(f"❌ {week}주차 보고서 생성 오류: {e}")
    
    print(f"\n주간 보고서 생성 결과: {success_count}/{len(weeks)}개 성공")
    
    # 월간 보고서 생성
    print(f"\n--- {month}월 월간 보고서 생성 중 ---")
    try:
        success = generator.generate_monthly_report(year, month)
        if success:
            print(f"✅ {month}월 월간 보고서 생성 완료")
        else:
            print(f"❌ {month}월 월간 보고서 생성 실패")
    except Exception as e:
        print(f"❌ {month}월 월간 보고서 생성 오류: {e}")
    
    print(f"\n=== {year}년 {month}월 보고서 생성 완료 ===")

if __name__ == "__main__":
    main()
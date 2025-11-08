#!/usr/bin/env python3
"""
10월 성과 보고서 업데이트 스크립트
서버에서 실행하여 10월 월간 보고서를 생성합니다.
"""
import sys
import os

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.report_generator import report_generator

def update_october_report():
    """10월 성과 보고서 업데이트"""
    year = 2025
    month = 10
    
    print("=" * 80)
    print(f"📊 {year}년 {month}월 성과 보고서 업데이트 시작")
    print("=" * 80)
    
    # 먼저 주간 보고서가 있는지 확인
    import calendar
    import os
    
    reports_dir = "backend/reports/weekly"
    weekly_files = []
    
    if os.path.exists(reports_dir):
        for filename in os.listdir(reports_dir):
            if filename.startswith(f"weekly_{year}_{month:02d}") and filename.endswith(".json"):
                weekly_files.append(filename)
    
    print(f"\n발견된 {month}월 주간 보고서: {len(weekly_files)}개")
    for filename in sorted(weekly_files):
        print(f"  - {filename}")
    
    # 주간 보고서가 없으면 생성 먼저 시도
    if len(weekly_files) == 0:
        print(f"\n⚠️  {month}월 주간 보고서가 없습니다. 주간 보고서를 먼저 생성합니다...")
        
        # 10월의 주차 계산
        last_day = calendar.monthrange(year, month)[1]
        weeks = (last_day + 6) // 7
        
        for week in range(1, weeks + 1):
            print(f"\n📅 {month}월 {week}주차 주간 보고서 생성 중...")
            success = report_generator.generate_weekly_report(year, month, week)
            if success:
                print(f"✅ {month}월 {week}주차 주간 보고서 생성 완료")
            else:
                print(f"⚠️  {month}월 {week}주차 주간 보고서 생성 실패 (데이터 없을 수 있음)")
    
    # 월간 보고서 생성
    print(f"\n📊 {year}년 {month}월 월간 보고서 생성 중...")
    success = report_generator.generate_monthly_report(year, month)
    
    if success:
        print(f"\n✅ {year}년 {month}월 월간 보고서 생성 완료!")
        
        # 생성된 보고서 확인
        report_file = f"backend/reports/monthly/monthly_{year}_{month:02d}.json"
        if os.path.exists(report_file):
            import json
            with open(report_file, 'r', encoding='utf-8') as f:
                report_data = json.load(f)
            
            print(f"\n📄 보고서 요약:")
            print(f"  - 파일: {report_file}")
            print(f"  - 추천 종목 수: {len(report_data.get('stocks', []))}")
            print(f"  - 평균 수익률: {report_data.get('summary', {}).get('average_return', 0):.2f}%")
        
        return True
    else:
        print(f"\n❌ {year}년 {month}월 월간 보고서 생성 실패")
        print("   주간 보고서가 필요한지 확인해주세요.")
        return False

if __name__ == "__main__":
    try:
        success = update_october_report()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

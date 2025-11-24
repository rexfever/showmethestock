#!/usr/bin/env python3
"""
매일 새벽에 기존 보고서를 삭제하고 재생성하는 배치 스크립트
매일 23시에 실행되어 모든 보고서를 최신 데이터로 재생성
"""

import os
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
sys.path.append(str(Path(__file__).parent))

from services.report_generator import report_generator

def delete_existing_reports():
    """기존 보고서 파일들을 모두 삭제"""
    
    report_dirs = [
        'backend/reports/weekly',
        'backend/reports/monthly', 
        'backend/reports/quarterly',
        'backend/reports/yearly'
    ]
    
    deleted_files = 0
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 기존 보고서 삭제 시작")
    
    for report_dir in report_dirs:
        if os.path.exists(report_dir):
            # 디렉토리 내 모든 파일 삭제
            for filename in os.listdir(report_dir):
                file_path = os.path.join(report_dir, filename)
                if os.path.isfile(file_path) and filename.endswith('.json'):
                    os.remove(file_path)
                    deleted_files += 1
                    print(f"  삭제: {filename}")
            
            print(f"  {report_dir}: 완료")
        else:
            print(f"  {report_dir}: 디렉토리 없음")
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 기존 보고서 삭제 완료: {deleted_files}개 파일")
    return deleted_files

def regenerate_all_reports():
    """모든 보고서를 재생성"""
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 보고서 재생성 시작")
    
    # 현재 연도
    current_year = datetime.now().year
    
    # 주간 보고서 생성 (7월~10월)
    print("=== 주간 보고서 생성 ===")
    for month in [7, 8, 9, 10]:
        max_weeks = 5 if month in [7, 8, 9] else 4  # 10월은 4주차까지만
        for week in range(1, max_weeks + 1):
            try:
                print(f"  {month}월 {week}주차 생성 중...")
                report_generator.generate_weekly_report(current_year, month, week)
                print(f"  {month}월 {week}주차 완료")
            except Exception as e:
                print(f"  {month}월 {week}주차 오류: {e}")
    
    # 월간 보고서 생성
    print("=== 월간 보고서 생성 ===")
    for month in [7, 8, 9, 10]:
        try:
            print(f"  {month}월 생성 중...")
            report_generator.generate_monthly_report(current_year, month)
            print(f"  {month}월 완료")
        except Exception as e:
            print(f"  {month}월 오류: {e}")
    
    # 분기 보고서 생성
    print("=== 분기 보고서 생성 ===")
    for quarter in [1, 2, 3, 4]:
        try:
            print(f"  {quarter}분기 생성 중...")
            report_generator.generate_quarterly_report(current_year, quarter)
            print(f"  {quarter}분기 완료")
        except Exception as e:
            print(f"  {quarter}분기 오류: {e}")
    
    # 연간 보고서 생성
    print("=== 연간 보고서 생성 ===")
    try:
        print(f"  {current_year}년 생성 중...")
        report_generator.generate_yearly_report(current_year)
        print(f"  {current_year}년 완료")
    except Exception as e:
        print(f"  {current_year}년 오류: {e}")
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 보고서 재생성 완료")

def main():
    """메인 실행 함수"""
    try:
        print("=" * 60)
        print("매일 보고서 재생성 배치 작업 시작")
        print("=" * 60)
        
        # 1. 기존 보고서 삭제
        deleted_count = delete_existing_reports()
        
        # 2. 모든 보고서 재생성
        regenerate_all_reports()
        
        print("=" * 60)
        print("✅ 매일 보고서 재생성 배치 작업 완료")
        print(f"   삭제된 파일: {deleted_count}개")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ 배치 작업 실패: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

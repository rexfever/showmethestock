#!/usr/bin/env python3
"""
주간 보고서 재생성 스크립트
개선된 로직으로 모든 주간 보고서를 다시 생성합니다.
"""

import os
import sys
from services.report_generator import report_generator

def regenerate_weekly_reports():
    """주간 보고서 재생성"""
    
    # 기존 주간 보고서 목록 확인
    weekly_reports = []
    weekly_dir = "backend/reports/weekly"
    
    if os.path.exists(weekly_dir):
        for filename in os.listdir(weekly_dir):
            if filename.startswith("weekly_") and filename.endswith(".json"):
                # weekly_2025_07_week1.json 형식 파싱
                parts = filename.replace(".json", "").split("_")
                if len(parts) == 4:
                    try:
                        year = int(parts[1])
                        month = int(parts[2])
                        week = int(parts[3].replace("week", ""))
                        weekly_reports.append((year, month, week, filename))
                    except ValueError:
                        continue
    
    print(f"발견된 주간 보고서: {len(weekly_reports)}개")
    
    # 재생성
    success_count = 0
    fail_count = 0
    
    for year, month, week, filename in sorted(weekly_reports):
        print(f"재생성 중: {year}년 {month}월 {week}주차...")
        
        try:
            success = report_generator.generate_weekly_report(year, month, week)
            if success:
                success_count += 1
                print(f"✅ 성공: {filename}")
            else:
                fail_count += 1
                print(f"❌ 실패: {filename} (데이터 없음)")
        except Exception as e:
            fail_count += 1
            print(f"❌ 오류: {filename} - {e}")
    
    print(f"\n=== 재생성 완료 ===")
    print(f"성공: {success_count}개")
    print(f"실패: {fail_count}개")
    print(f"총 처리: {len(weekly_reports)}개")

if __name__ == "__main__":
    regenerate_weekly_reports()
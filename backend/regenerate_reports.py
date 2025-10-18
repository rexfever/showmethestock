#!/usr/bin/env python3
"""
보고서 재생성 스크립트 (최고가 기준으로 수정)
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.report_generator import report_generator

def regenerate_reports():
    """보고서 재생성"""
    
    # 7월 주간 보고서 재생성
    print("7월 주간 보고서 재생성 중...")
    for week in range(1, 6):
        try:
            print(f'7월 {week}주차 보고서 재생성 중...')
            report_generator.generate_weekly_report(2025, 7, week)
            print(f'7월 {week}주차 완료')
        except Exception as e:
            print(f'7월 {week}주차 오류: {e}')
    
    # 8월 주간 보고서 재생성
    print("\n8월 주간 보고서 재생성 중...")
    for week in range(1, 6):
        try:
            print(f'8월 {week}주차 보고서 재생성 중...')
            report_generator.generate_weekly_report(2025, 8, week)
            print(f'8월 {week}주차 완료')
        except Exception as e:
            print(f'8월 {week}주차 오류: {e}')
    
    # 9월 주간 보고서 재생성
    print("\n9월 주간 보고서 재생성 중...")
    for week in range(1, 6):
        try:
            print(f'9월 {week}주차 보고서 재생성 중...')
            report_generator.generate_weekly_report(2025, 9, week)
            print(f'9월 {week}주차 완료')
        except Exception as e:
            print(f'9월 {week}주차 오류: {e}')
    
    # 10월 주간 보고서 재생성
    print("\n10월 주간 보고서 재생성 중...")
    for week in range(1, 5):
        try:
            print(f'10월 {week}주차 보고서 재생성 중...')
            report_generator.generate_weekly_report(2025, 10, week)
            print(f'10월 {week}주차 완료')
        except Exception as e:
            print(f'10월 {week}주차 오류: {e}')
    
    print("\n모든 보고서 재생성 완료!")

if __name__ == "__main__":
    regenerate_reports()

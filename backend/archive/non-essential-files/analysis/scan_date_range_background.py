#!/usr/bin/env python3
"""
날짜 범위 스캔 스크립트 (백그라운드 실행용)
2025년 9월 1일부터 11월 20일까지 스캔 실행 및 DB 저장
"""
import sys
import os
import requests
import time
from datetime import datetime, timedelta
from typing import List

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def is_trading_day(date_str: str) -> bool:
    """거래일 여부 확인 (간단한 버전)"""
    try:
        date_obj = datetime.strptime(date_str, '%Y%m%d')
        # 주말 체크
        if date_obj.weekday() >= 5:  # 토요일(5), 일요일(6)
            return False
        
        # 한국 공휴일 체크 (간단한 버전 - 실제로는 holidays 라이브러리 사용 권장)
        # 2025년 한국 공휴일
        holidays_2025 = [
            '20250101', '20250128', '20250129', '20250130',  # 신정, 설날
            '20250301',  # 삼일절
            '20250505',  # 어린이날
            '20250606',  # 현충일
            '20250815',  # 광복절
            '20251003',  # 개천절
            '20251009',  # 한글날
            '20251225',  # 크리스마스
        ]
        
        if date_str in holidays_2025:
            return False
        
        return True
    except Exception:
        return False

def scan_date_range(start_date: str, end_date: str, base_url: str = "http://localhost:8010"):
    """날짜 범위 스캔 실행"""
    start = datetime.strptime(start_date, '%Y%m%d')
    end = datetime.strptime(end_date, '%Y%m%d')
    
    dates_to_scan = []
    current = start
    while current <= end:
        date_str = current.strftime('%Y%m%d')
        if is_trading_day(date_str):
            dates_to_scan.append(date_str)
        current += timedelta(days=1)
    
    print(f"📅 스캔 대상 날짜: {len(dates_to_scan)}개")
    print(f"   시작: {start_date}, 종료: {end_date}")
    print(f"   거래일만 스캔합니다.\n")
    
    success_count = 0
    fail_count = 0
    skipped_count = 0
    
    for i, date_str in enumerate(dates_to_scan, 1):
        try:
            print(f"[{i}/{len(dates_to_scan)}] {date_str} 스캔 중...", end=' ', flush=True)
            
            # API 호출
            url = f"{base_url}/scan"
            params = {
                'date': date_str,
                'save_snapshot': 'true'
            }
            
            response = requests.get(url, params=params, timeout=300)
            
            if response.status_code == 200:
                data = response.json()
                matched_count = data.get('matched_count', 0)
                print(f"✅ 완료 (매칭: {matched_count}개)")
                success_count += 1
            elif response.status_code == 400:
                error_msg = response.json().get('detail', 'Unknown error')
                if '거래일이 아닙니다' in error_msg:
                    print(f"⏭️  건너뜀 (거래일 아님)")
                    skipped_count += 1
                else:
                    print(f"⚠️  실패: {error_msg}")
                    fail_count += 1
            else:
                print(f"❌ 실패 (HTTP {response.status_code})")
                fail_count += 1
            
            # API 부하 방지를 위한 대기
            time.sleep(2)
            
        except requests.exceptions.Timeout:
            print(f"❌ 타임아웃")
            fail_count += 1
        except Exception as e:
            print(f"❌ 오류: {str(e)}")
            fail_count += 1
            time.sleep(5)  # 오류 시 더 긴 대기
    
    print(f"\n{'='*60}")
    print(f"스캔 완료 요약")
    print(f"{'='*60}")
    print(f"성공: {success_count}개")
    print(f"실패: {fail_count}개")
    print(f"건너뜀: {skipped_count}개")
    print(f"총 처리: {len(dates_to_scan)}개")
    print(f"{'='*60}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='날짜 범위 스캔 실행')
    parser.add_argument('--start', type=str, default='20250901', help='시작 날짜 (YYYYMMDD)')
    parser.add_argument('--end', type=str, default='20251120', help='종료 날짜 (YYYYMMDD)')
    parser.add_argument('--url', type=str, default='http://localhost:8010', help='API URL')
    
    args = parser.parse_args()
    
    print(f"{'='*60}")
    print(f"날짜 범위 스캔 시작")
    print(f"{'='*60}")
    print(f"시작 날짜: {args.start}")
    print(f"종료 날짜: {args.end}")
    print(f"API URL: {args.url}")
    print(f"{'='*60}\n")
    
    scan_date_range(args.start, args.end, args.url)


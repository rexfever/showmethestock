#!/usr/bin/env python3
"""
매일 현재 수익률을 업데이트하는 배치 스크립트
기존 보고서 파일들의 current_return 값을 최신 데이터로 갱신
"""

import json
import glob
import os
import sys
from datetime import datetime
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
sys.path.append(str(Path(__file__).parent))

from services.returns_service import calculate_returns

def update_current_returns_in_reports():
    """모든 보고서 파일의 현재 수익률을 업데이트"""
    
    # 보고서 디렉토리들
    report_dirs = [
        'backend/reports/weekly',
        'backend/reports/monthly', 
        'backend/reports/quarterly',
        'backend/reports/yearly'
    ]
    
    total_files = 0
    updated_files = 0
    error_files = 0
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 현재 수익률 업데이트 시작")
    
    for report_dir in report_dirs:
        if not os.path.exists(report_dir):
            print(f"  {report_dir} 디렉토리가 존재하지 않습니다.")
            continue
            
        # JSON 파일 찾기
        json_files = glob.glob(f'{report_dir}/*.json')
        print(f"  {report_dir}: {len(json_files)}개 파일 발견")
        total_files += len(json_files)
        
        for file_path in json_files:
            try:
                # 파일 읽기
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # stocks 배열의 current_return 업데이트
                if 'stocks' in data and isinstance(data['stocks'], list):
                    stocks_updated = 0
                    
                    for stock in data['stocks']:
                        if 'code' in stock and 'date' in stock:
                            try:
                                # 현재 수익률 계산
                                current_return = calculate_returns(
                                    stock['code'], 
                                    stock['date']
                                )
                                
                                # current_return 업데이트
                                if 'current_return' in stock:
                                    old_return = stock['current_return']
                                    stock['current_return'] = round(current_return, 1)
                                    
                                    if old_return != stock['current_return']:
                                        stocks_updated += 1
                                        
                            except Exception as e:
                                print(f"    종목 {stock.get('code', 'Unknown')} 수익률 계산 오류: {e}")
                                continue
                    
                    # 파일이 업데이트되었으면 저장
                    if stocks_updated > 0:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            json.dump(data, f, ensure_ascii=False, indent=2)
                        
                        updated_files += 1
                        print(f"    업데이트: {os.path.basename(file_path)} ({stocks_updated}개 종목)")
                    else:
                        print(f"    변경없음: {os.path.basename(file_path)}")
                        
            except Exception as e:
                error_files += 1
                print(f"    오류: {os.path.basename(file_path)} - {e}")
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 업데이트 완료")
    print(f"  총 {total_files}개 파일 중 {updated_files}개 파일 업데이트, {error_files}개 오류")
    
    return updated_files, error_files

def update_statistics_avg_return(report_dirs=None):
    """통계의 평균 수익률을 current_return 기준으로 재계산"""
    
    if report_dirs is None:
        report_dirs = [
            'backend/reports/weekly',
            'backend/reports/monthly', 
            'backend/reports/quarterly',
            'backend/reports/yearly'
        ]
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 통계 평균 수익률 재계산 시작")
    
    for report_dir in report_dirs:
        if not os.path.exists(report_dir):
            continue
            
        json_files = glob.glob(f'{report_dir}/*.json')
        
        for file_path in json_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # statistics.avg_return을 current_return 기준으로 재계산
                if 'statistics' in data and 'stocks' in data:
                    stocks = data['stocks']
                    if stocks:
                        # current_return 기준으로 평균 계산
                        total_current_return = sum(
                            stock.get('current_return', 0) for stock in stocks
                        )
                        new_avg_return = round(total_current_return / len(stocks), 1)
                        
                        # 기존 값과 다르면 업데이트
                        if data['statistics'].get('avg_return') != new_avg_return:
                            data['statistics']['avg_return'] = new_avg_return
                            
                            with open(file_path, 'w', encoding='utf-8') as f:
                                json.dump(data, f, ensure_ascii=False, indent=2)
                            
                            print(f"    통계 업데이트: {os.path.basename(file_path)} - avg_return: {new_avg_return}%")
                            
            except Exception as e:
                print(f"    통계 오류: {os.path.basename(file_path)} - {e}")
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 통계 재계산 완료")

if __name__ == "__main__":
    try:
        # 1. 현재 수익률 업데이트
        updated_files, error_files = update_current_returns_in_reports()
        
        # 2. 통계 평균 수익률 재계산 (current_return 기준)
        update_statistics_avg_return()
        
        print(f"\n✅ 배치 작업 완료: {updated_files}개 파일 업데이트")
        
        if error_files > 0:
            print(f"⚠️  {error_files}개 파일에서 오류 발생")
            
    except Exception as e:
        print(f"❌ 배치 작업 실패: {e}")
        sys.exit(1)

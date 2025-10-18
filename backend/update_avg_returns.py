#!/usr/bin/env python3
"""
기존 보고서의 평균 수익률을 최고가 기준으로 업데이트
"""
import json
import os
import glob

def update_avg_returns():
    """기존 보고서의 평균 수익률 업데이트"""
    
    # 보고서 디렉토리들
    report_dirs = [
        'reports/weekly',
        'reports/monthly', 
        'reports/quarterly',
        'reports/yearly'
    ]
    
    print(f"현재 디렉토리: {os.getcwd()}")
    print(f"reports 디렉토리 존재: {os.path.exists('reports')}")
    
    updated_count = 0
    
    for report_dir in report_dirs:
        if not os.path.exists(report_dir):
            print(f"디렉토리 없음: {report_dir}")
            continue
            
        # 모든 JSON 파일 찾기
        json_files = glob.glob(f"{report_dir}/*.json")
        print(f"{report_dir}: {len(json_files)}개 파일 발견")
        if json_files:
            print(f"  파일들: {json_files[:3]}...")  # 처음 3개만 출력
        
        for json_file in json_files:
            try:
                # 기존 보고서 읽기
                with open(json_file, 'r', encoding='utf-8') as f:
                    report = json.load(f)
                
                # stocks 데이터가 있는지 확인
                if 'data' in report and 'stocks' in report['data']:
                    stocks = report['data']['stocks']
                    
                    # 최고가 기준으로 평균 수익률 재계산
                    if stocks:
                        total_max_return = sum(stock.get('max_return', 0) for stock in stocks)
                        avg_return = total_max_return / len(stocks)
                        
                        # 통계 업데이트
                        if 'statistics' in report['data']:
                            report['data']['statistics']['avg_return'] = round(avg_return, 2)
                            
                            # 보고서 파일 저장
                            with open(json_file, 'w', encoding='utf-8') as f:
                                json.dump(report, f, ensure_ascii=False, indent=2)
                            
                            print(f"업데이트: {json_file} - 평균 수익률: {round(avg_return, 2)}%")
                            updated_count += 1
                            
            except Exception as e:
                print(f"오류 ({json_file}): {e}")
    
    print(f"\n총 {updated_count}개 보고서 업데이트 완료!")

if __name__ == "__main__":
    update_avg_returns()

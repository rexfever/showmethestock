#!/usr/bin/env python3
"""
11월 레짐 데이터 실제 API로 업데이트
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

def update_november_with_api():
    """실제 API 사용해서 11월 레짐 데이터 업데이트"""
    print("=== 11월 레짐 데이터 API 업데이트 ===\n")
    
    november_dates = [
        "20251103", "20251104", "20251105", "20251106", "20251107",
        "20251110", "20251111", "20251112", "20251113", "20251114", 
        "20251117", "20251118", "20251119", "20251120", "20251121",
        "20251124", "20251125", "20251126", "20251127", "20251128"
    ]
    
    try:
        from market_analyzer import market_analyzer
        
        success_count = 0
        
        for i, date in enumerate(november_dates, 1):
            try:
                print(f"[{i:2d}/20] {date} API 분석...", end=" ")
                
                # 실제 API 사용한 v3 분석
                condition = market_analyzer.analyze_market_condition_v3(date, mode="backtest")
                
                print(f"✅ {condition.final_regime}")
                success_count += 1
                
            except Exception as e:
                print(f"❌ {e}")
                continue
        
        print(f"\n성공: {success_count}/20일")
        
    except Exception as e:
        print(f"❌ 실패: {e}")

if __name__ == "__main__":
    update_november_with_api()
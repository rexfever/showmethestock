#!/usr/bin/env python3
"""
11월 레짐 데이터 업데이트 (최신 분석기 사용)
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

def update_november_regime():
    """11월 전체 기간 레짐 데이터 업데이트"""
    print("=== 11월 레짐 데이터 업데이트 ===\n")
    
    # 11월 거래일 목록
    november_dates = [
        "20251103", "20251104", "20251105", "20251106", "20251107",
        "20251110", "20251111", "20251112", "20251113", "20251114", 
        "20251117", "20251118", "20251119", "20251120", "20251121",
        "20251124", "20251125", "20251126", "20251127", "20251128"
    ]
    
    try:
        from market_analyzer import market_analyzer
        
        success_count = 0
        error_count = 0
        
        print(f"총 {len(november_dates)}일 업데이트 시작...\n")
        
        for i, date in enumerate(november_dates, 1):
            try:
                print(f"[{i:2d}/{len(november_dates)}] {date} 분석 중...", end=" ")
                
                # v4 분석 실행 (최신)
                condition = market_analyzer.analyze_market_condition_v4(date, mode="backtest")
                
                print(f"✅ {condition.final_regime} (점수: {condition.final_score:.2f})")
                success_count += 1
                
            except Exception as e:
                print(f"❌ 실패: {e}")
                error_count += 1
                continue
        
        print(f"\n=== 업데이트 완료 ===")
        print(f"성공: {success_count}일")
        print(f"실패: {error_count}일")
        
        if success_count > 0:
            print(f"\n업데이트된 데이터 확인:")
            from query_november_regime_fixed import query_november_regime
            query_november_regime()
        
    except Exception as e:
        print(f"❌ 업데이트 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    update_november_regime()
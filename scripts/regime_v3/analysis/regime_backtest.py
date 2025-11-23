#!/usr/bin/env python3
"""
Global Regime 백테스트 실행 스크립트 (캐시 기반)
"""
import sys
import os
import json
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../backend'))

def run_backtest(start_date, end_date, save_result=True):
    """백테스트 실행 및 결과 저장 (캐시 기반)"""
    try:
        from services.regime_analyzer_cached import regime_analyzer_cached
        from datetime import datetime, timedelta
        
        print(f"🔄 캐시 기반 백테스트 실행: {start_date} ~ {end_date}")
        
        # 날짜 범위 생성
        start_dt = datetime.strptime(start_date, '%Y%m%d')
        end_dt = datetime.strptime(end_date, '%Y%m%d')
        
        regime_data = []
        current_dt = start_dt
        
        while current_dt <= end_dt:
            date_str = current_dt.strftime('%Y%m%d')
            
            try:
                # 캐시 기반 레짐 분석
                result = regime_analyzer_cached.analyze_regime_v4_cached(date_str)
                regime_data.append({
                    'date': date_str,
                    'final_regime': result['final_regime'],
                    'final_score': result['final_score'],
                    'kr_regime': result['kr_regime'],
                    'us_prev_regime': result['us_prev_regime']
                })
                print(f"  {date_str}: {result['final_regime']} ({result['final_score']:.2f})")
            except Exception as e:
                print(f"  {date_str}: 오류 - {e}")
            
            current_dt += timedelta(days=1)
        
        # 통계 계산
        regime_counts = {}
        for data in regime_data:
            regime = data['final_regime']
            regime_counts[regime] = regime_counts.get(regime, 0) + 1
        
        result = {
            'period': f"{start_date} ~ {end_date}",
            'total_days': len(regime_data),
            'regime_distribution': regime_counts,
            'daily_data': regime_data
        }
        
        # 결과 저장
        if save_result:
            output_file = f"backtest_result_{start_date}_{end_date}.json"
            output_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'backend', 'reports', output_file)
            
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            combined_result = {
                'backtest': result,
                'transitions': transitions,
                'generated_at': f"{start_date}_{end_date}"
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(combined_result, f, ensure_ascii=False, indent=2)
            
            print(f"\n💾 결과 저장: {output_path}")
        
        return result
        
    except Exception as e:
        print(f"❌ 백테스트 실행 실패: {e}")
        return None

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Global Regime v3 백테스트')
    parser.add_argument('--start', required=True, help='시작 날짜 (YYYYMMDD)')
    parser.add_argument('--end', required=True, help='종료 날짜 (YYYYMMDD)')
    parser.add_argument('--no-save', action='store_true', help='결과 저장 안함')
    args = parser.parse_args()
    
    run_backtest(args.start, args.end, not args.no_save)
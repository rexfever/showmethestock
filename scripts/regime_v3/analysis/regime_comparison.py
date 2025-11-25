#!/usr/bin/env python3
"""
v1 vs v3 장세 분석 비교 스크립트
"""
import sys
import os
from datetime import datetime, timedelta
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../backend'))

def compare_regimes(start_date, end_date):
    """v1과 v3 장세 분석 결과 비교"""
    try:
        from market_analyzer import market_analyzer
        from main import is_trading_day
        
        start_dt = datetime.strptime(start_date, '%Y%m%d')
        end_dt = datetime.strptime(end_date, '%Y%m%d')
        
        comparisons = []
        current_dt = start_dt
        
        while current_dt <= end_dt:
            date_str = current_dt.strftime('%Y%m%d')
            
            try:
                if not is_trading_day(date_str):
                    current_dt += timedelta(days=1)
                    continue
            except Exception:
                if current_dt.weekday() >= 5:
                    current_dt += timedelta(days=1)
                    continue
            
            try:
                # v1 분석
                v1_condition = market_analyzer.analyze_market_condition(date_str)
                
                # v3 분석
                v3_condition = market_analyzer.analyze_market_condition_v3(date_str, mode="backtest")
                
                comparison = {
                    'date': date_str,
                    'v1_sentiment': v1_condition.market_sentiment,
                    'v3_regime': v3_condition.final_regime if v3_condition.version == "regime_v3" else "failed",
                    'v1_score': v1_condition.sentiment_score,
                    'v3_score': v3_condition.final_score if v3_condition.version == "regime_v3" else 0.0,
                    'match': v1_condition.market_sentiment == (v3_condition.final_regime if v3_condition.version == "regime_v3" else "failed")
                }
                
                comparisons.append(comparison)
                
            except Exception as e:
                print(f"⚠️ {date_str} 분석 실패: {e}")
            
            current_dt += timedelta(days=1)
        
        # 결과 분석
        if not comparisons:
            print("❌ 비교할 데이터가 없습니다")
            return
        
        total_days = len(comparisons)
        matches = sum(1 for c in comparisons if c['match'])
        match_rate = (matches / total_days * 100) if total_days > 0 else 0
        
        print(f"\n📊 v1 vs v3 장세 분석 비교 결과")
        print(f"기간: {start_date} ~ {end_date} ({total_days}일)")
        print(f"일치율: {matches}/{total_days} ({match_rate:.1f}%)")
        
        # 불일치 케이스 분석
        mismatches = [c for c in comparisons if not c['match']]
        if mismatches:
            print(f"\n🔍 불일치 케이스 ({len(mismatches)}건):")
            for mm in mismatches[:10]:  # 최대 10개만 표시
                print(f"  {mm['date']}: v1={mm['v1_sentiment']} vs v3={mm['v3_regime']}")
        
        # 레짐별 분포
        v1_dist = {}
        v3_dist = {}
        for c in comparisons:
            v1_dist[c['v1_sentiment']] = v1_dist.get(c['v1_sentiment'], 0) + 1
            v3_dist[c['v3_regime']] = v3_dist.get(c['v3_regime'], 0) + 1
        
        print(f"\n📈 레짐 분포:")
        print(f"v1: {v1_dist}")
        print(f"v3: {v3_dist}")
        
        return comparisons
        
    except Exception as e:
        print(f"❌ 비교 분석 실패: {e}")
        return None

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='v1 vs v3 장세 분석 비교')
    parser.add_argument('--start', required=True, help='시작 날짜 (YYYYMMDD)')
    parser.add_argument('--end', required=True, help='종료 날짜 (YYYYMMDD)')
    args = parser.parse_args()
    
    compare_regimes(args.start, args.end)
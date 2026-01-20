#!/usr/bin/env python3
"""
11월 장세 분석 스크립트 (기존 daily_regime_check.py 활용)
"""
import sys
import os
from datetime import datetime
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'scripts/regime_v3/analysis'))

def analyze_november_regime():
    """11월 전체 기간 장세 분석"""
    print("=== 2025년 11월 장세 분석 ===\n")
    
    # 11월 거래일 목록
    november_dates = [
        "20251103", "20251104", "20251105", "20251106", "20251107",
        "20251110", "20251111", "20251112", "20251113", "20251114", 
        "20251117", "20251118", "20251119", "20251120", "20251121",
        "20251124", "20251125", "20251126", "20251127", "20251128"
    ]
    
    try:
        from market_analyzer import market_analyzer
        
        results = []
        regime_counts = {"bull": 0, "neutral": 0, "bear": 0, "crash": 0}
        
        print("날짜별 장세 분석 결과:")
        print("-" * 100)
        print(f"{'날짜':>8} | {'최종레짐':>8} | {'한국레짐':>8} | {'미국레짐':>8} | {'최종점수':>8} | {'한국점수':>8} | {'미국점수':>8}")
        print("-" * 100)
        
        for date in november_dates:
            try:
                # Global Regime v3 분석 실행
                condition = market_analyzer.analyze_market_condition_v3(date, mode="backtest")
                
                if condition.version == "regime_v3":
                    # v3 결과 사용
                    final_regime = condition.final_regime
                    kr_regime = condition.kr_regime
                    us_regime = condition.us_prev_regime
                    final_score = condition.final_score
                    kr_score = condition.kr_score
                    us_score = condition.us_prev_score
                else:
                    # v1 결과를 v3 형식으로 변환
                    final_regime = condition.market_sentiment
                    kr_regime = condition.market_sentiment
                    us_regime = "neutral"
                    final_score = 0.0
                    kr_score = 0.0
                    us_score = 0.0
                
                # 결과 저장
                result = {
                    "date": date,
                    "final_regime": final_regime,
                    "kr_regime": kr_regime,
                    "us_regime": us_regime,
                    "final_score": final_score,
                    "kr_score": kr_score,
                    "us_score": us_score,
                    "version": condition.version
                }
                results.append(result)
                
                # 카운트 업데이트
                regime_counts[final_regime] += 1
                
                # 출력
                print(f"{date} | {final_regime:>8} | {kr_regime:>8} | {us_regime:>8} | "
                      f"{final_score:>8.2f} | {kr_score:>8.2f} | {us_score:>8.2f}")
                
            except Exception as e:
                print(f"{date} | ERROR: {e}")
                continue
        
        print("-" * 100)
        
        # 요약 통계
        total_days = len([r for r in results if r])
        print(f"\n=== 11월 장세 요약 ===")
        print(f"총 분석일: {total_days}일")
        print(f"강세장(bull): {regime_counts['bull']}일 ({regime_counts['bull']/total_days*100:.1f}%)")
        print(f"중립장(neutral): {regime_counts['neutral']}일 ({regime_counts['neutral']/total_days*100:.1f}%)")
        print(f"약세장(bear): {regime_counts['bear']}일 ({regime_counts['bear']/total_days*100:.1f}%)")
        print(f"급락장(crash): {regime_counts['crash']}일 ({regime_counts['crash']/total_days*100:.1f}%)")
        
        # 점수 통계
        final_scores = [r["final_score"] for r in results if r["final_score"] != 0]
        kr_scores = [r["kr_score"] for r in results if r["kr_score"] != 0]
        us_scores = [r["us_score"] for r in results if r["us_score"] != 0]
        
        if final_scores:
            print(f"\n=== 점수 통계 ===")
            print(f"최종 점수 평균: {sum(final_scores)/len(final_scores):+.2f}")
            print(f"최종 점수 범위: {min(final_scores):+.2f} ~ {max(final_scores):+.2f}")
            
        if kr_scores:
            print(f"한국 점수 평균: {sum(kr_scores)/len(kr_scores):+.2f}")
            print(f"한국 점수 범위: {min(kr_scores):+.2f} ~ {max(kr_scores):+.2f}")
            
        if us_scores:
            print(f"미국 점수 평균: {sum(us_scores)/len(us_scores):+.2f}")
            print(f"미국 점수 범위: {min(us_scores):+.2f} ~ {max(us_scores):+.2f}")
        
        # 레짐 변화 분석
        print(f"\n=== 레짐 변화 패턴 ===")
        regime_changes = 0
        prev_regime = None
        
        for result in results:
            if result and prev_regime and result["final_regime"] != prev_regime:
                regime_changes += 1
                print(f"{result['date']}: {prev_regime} → {result['final_regime']}")
            if result:
                prev_regime = result["final_regime"]
        
        print(f"총 레짐 변화: {regime_changes}회")
        
        # 한국 vs 미국 레짐 비교
        print(f"\n=== 한국 vs 미국 레짐 비교 ===")
        kr_regimes = [r["kr_regime"] for r in results if r]
        us_regimes = [r["us_regime"] for r in results if r]
        
        agreement = sum(1 for kr, us in zip(kr_regimes, us_regimes) if kr == us)
        if kr_regimes:
            print(f"한국-미국 레짐 일치율: {agreement/len(kr_regimes)*100:.1f}% ({agreement}/{len(kr_regimes)})")
        
        # 결과를 JSON으로 저장
        import json
        output_data = {
            "generated_at": datetime.now().isoformat(),
            "period": "2025년 11월",
            "total_days": total_days,
            "regime_summary": regime_counts,
            "regime_changes": regime_changes,
            "agreement_rate": agreement/len(kr_regimes)*100 if kr_regimes else 0,
            "daily_results": results
        }
        
        with open("november_regime_analysis.json", "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n분석 결과가 november_regime_analysis.json에 저장되었습니다.")
        
        return results
        
    except Exception as e:
        print(f"❌ 장세 분석 실패: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    analyze_november_regime()
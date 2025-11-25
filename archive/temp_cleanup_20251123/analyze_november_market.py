#!/usr/bin/env python3
"""
11월 장세 분석 스크립트
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

import json
from datetime import datetime, timedelta
from backend.market_analyzer import market_analyzer
import pandas as pd

def analyze_november_market():
    """11월 장세 분석"""
    print("=== 11월 장세 분석 ===\n")
    
    # 11월 거래일 목록 (2025년 기준)
    november_dates = [
        "20251103", "20251104", "20251105", "20251106", "20251107",
        "20251110", "20251111", "20251112", "20251113", "20251114",
        "20251117", "20251118", "20251119", "20251120", "20251121",
        "20251124", "20251125", "20251126", "20251127", "20251128"
    ]
    
    results = []
    sentiment_counts = {"bull": 0, "neutral": 0, "bear": 0, "crash": 0}
    
    print("날짜별 장세 분석:")
    print("-" * 80)
    
    for date in november_dates:
        try:
            # 장세 분석 실행
            condition = market_analyzer.analyze_market_condition(date)
            
            # 결과 저장
            result = {
                "date": date,
                "sentiment": condition.market_sentiment,
                "kospi_return": condition.kospi_return,
                "volatility": condition.volatility,
                "rsi_threshold": condition.rsi_threshold,
                "min_signals": condition.min_signals,
                "sector_rotation": condition.sector_rotation,
                "foreign_flow": condition.foreign_flow,
                "volume_trend": condition.volume_trend
            }
            results.append(result)
            
            # 카운트 업데이트
            sentiment_counts[condition.market_sentiment] += 1
            
            # 출력
            print(f"{date}: {condition.market_sentiment:>7} | "
                  f"KOSPI: {condition.kospi_return*100:+6.2f}% | "
                  f"변동성: {condition.volatility*100:5.2f}% | "
                  f"RSI임계: {condition.rsi_threshold:4.1f} | "
                  f"최소신호: {condition.min_signals}")
            
        except Exception as e:
            print(f"{date}: ERROR - {e}")
            continue
    
    print("-" * 80)
    print("\n=== 11월 장세 요약 ===")
    print(f"총 거래일: {len(november_dates)}일")
    print(f"강세장(bull): {sentiment_counts['bull']}일 ({sentiment_counts['bull']/len(november_dates)*100:.1f}%)")
    print(f"중립장(neutral): {sentiment_counts['neutral']}일 ({sentiment_counts['neutral']/len(november_dates)*100:.1f}%)")
    print(f"약세장(bear): {sentiment_counts['bear']}일 ({sentiment_counts['bear']/len(november_dates)*100:.1f}%)")
    print(f"급락장(crash): {sentiment_counts['crash']}일 ({sentiment_counts['crash']/len(november_dates)*100:.1f}%)")
    
    # 평균 수익률 계산
    returns = [r["kospi_return"] for r in results if r["kospi_return"] is not None]
    if returns:
        avg_return = sum(returns) / len(returns)
        print(f"\n평균 KOSPI 수익률: {avg_return*100:+.2f}%")
        print(f"최고 수익률: {max(returns)*100:+.2f}%")
        print(f"최저 수익률: {min(returns)*100:+.2f}%")
    
    # 변동성 분석
    volatilities = [r["volatility"] for r in results if r["volatility"] is not None]
    if volatilities:
        avg_vol = sum(volatilities) / len(volatilities)
        print(f"평균 변동성: {avg_vol*100:.2f}%")
        print(f"최고 변동성: {max(volatilities)*100:.2f}%")
        print(f"최저 변동성: {min(volatilities)*100:.2f}%")
    
    # 섹터 로테이션 분석
    sector_counts = {}
    for r in results:
        sector = r.get("sector_rotation", "mixed")
        sector_counts[sector] = sector_counts.get(sector, 0) + 1
    
    print(f"\n섹터 로테이션:")
    for sector, count in sector_counts.items():
        print(f"  {sector}: {count}일 ({count/len(results)*100:.1f}%)")
    
    # 외국인 수급 분석
    foreign_counts = {}
    for r in results:
        foreign = r.get("foreign_flow", "neutral")
        foreign_counts[foreign] = foreign_counts.get(foreign, 0) + 1
    
    print(f"\n외국인 수급:")
    for flow, count in foreign_counts.items():
        print(f"  {flow}: {count}일 ({count/len(results)*100:.1f}%)")
    
    # 거래량 추세 분석
    volume_counts = {}
    for r in results:
        volume = r.get("volume_trend", "normal")
        volume_counts[volume] = volume_counts.get(volume, 0) + 1
    
    print(f"\n거래량 추세:")
    for trend, count in volume_counts.items():
        print(f"  {trend}: {count}일 ({count/len(results)*100:.1f}%)")
    
    # 결과를 JSON 파일로 저장
    output_file = "november_market_analysis.json"
    analysis_result = {
        "generated_at": datetime.now().isoformat(),
        "period": "2025년 11월",
        "total_days": len(november_dates),
        "sentiment_summary": sentiment_counts,
        "statistics": {
            "avg_return": avg_return if returns else 0,
            "max_return": max(returns) if returns else 0,
            "min_return": min(returns) if returns else 0,
            "avg_volatility": avg_vol if volatilities else 0,
            "max_volatility": max(volatilities) if volatilities else 0,
            "min_volatility": min(volatilities) if volatilities else 0
        },
        "sector_rotation": sector_counts,
        "foreign_flow": foreign_counts,
        "volume_trend": volume_counts,
        "daily_details": results
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(analysis_result, f, ensure_ascii=False, indent=2)
    
    print(f"\n분석 결과가 {output_file}에 저장되었습니다.")
    
    return analysis_result

if __name__ == "__main__":
    analyze_november_market()
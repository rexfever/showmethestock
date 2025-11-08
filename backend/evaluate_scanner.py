#!/usr/bin/env python3
"""
스캐너 성과 평가 스크립트
생성된 보고서들을 분석하여 스캐너의 성과를 평가합니다.
"""
import json
import os
import glob
from collections import defaultdict
from datetime import datetime
from typing import Dict, List

def load_report(report_type: str, filename: str) -> Dict:
    """보고서 파일 로드"""
    # 프로젝트 루트 찾기
    current_dir = os.path.dirname(os.path.abspath(__file__))
    reports_dir = os.path.join(current_dir, "reports", report_type)
    file_path = os.path.join(reports_dir, filename)
    
    if not os.path.exists(file_path):
        return None
    
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def analyze_reports():
    """모든 보고서 분석"""
    
    # 주간 보고서 분석
    weekly_reports = []
    weekly_dir = "reports/weekly"
    if os.path.exists(weekly_dir):
        for filename in sorted(glob.glob(f"{weekly_dir}/weekly_2025_*.json")):
            report = load_report("weekly", os.path.basename(filename))
            if report:
                weekly_reports.append(report)
    
    # 월간 보고서 분석
    monthly_reports = []
    monthly_dir = "reports/monthly"
    if os.path.exists(monthly_dir):
        for filename in sorted(glob.glob(f"{monthly_dir}/monthly_2025_*.json")):
            report = load_report("monthly", os.path.basename(filename))
            if report:
                monthly_reports.append(report)
    
    # 분기 보고서 분석
    quarterly_reports = []
    quarterly_dir = "reports/quarterly"
    if os.path.exists(quarterly_dir):
        for filename in sorted(glob.glob(f"{quarterly_dir}/quarterly_2025_*.json")):
            report = load_report("quarterly", os.path.basename(filename))
            if report:
                quarterly_reports.append(report)
    
    print("=" * 80)
    print("📊 스캐너 성과 평가 리포트")
    print("=" * 80)
    print(f"\n분석 기준일: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"분석 기간: 2025년 7월 ~ 11월")
    
    # 주간 보고서 통계
    print("\n" + "=" * 80)
    print("📈 주간 보고서 통계")
    print("=" * 80)
    print(f"총 주간 보고서 수: {len(weekly_reports)}개")
    
    if weekly_reports:
        all_weekly_stats = []
        for report in weekly_reports:
            stats = report.get("statistics", {})
            if stats:
                all_weekly_stats.append(stats)
        
        if all_weekly_stats:
            total_stocks = sum(s.get("total_stocks", 0) for s in all_weekly_stats)
            avg_returns = [s.get("avg_return", 0) for s in all_weekly_stats]
            positive_rates = [s.get("positive_rate", 0) for s in all_weekly_stats]
            
            print(f"\n총 추천 종목 수: {total_stocks}개")
            print(f"주간 평균 추천 종목 수: {total_stocks / len(all_weekly_stats):.1f}개")
            print(f"평균 수익률: {sum(avg_returns) / len(avg_returns):.2f}%")
            print(f"최고 주간 평균 수익률: {max(avg_returns):.2f}%")
            print(f"최저 주간 평균 수익률: {min(avg_returns):.2f}%")
            print(f"평균 양수 수익률 비율: {sum(positive_rates) / len(positive_rates):.2f}%")
            print(f"최고 양수 수익률 비율: {max(positive_rates):.2f}%")
            
            # 최고/최악 종목 찾기
            best_stocks = []
            worst_stocks = []
            for report in weekly_reports:
                stats = report.get("statistics", {})
                if stats.get("best_stock"):
                    best_stocks.append(stats["best_stock"])
                if stats.get("worst_stock"):
                    worst_stocks.append(stats["worst_stock"])
            
            if best_stocks:
                overall_best = max(best_stocks, key=lambda x: x.get("max_return", 0))
                print(f"\n🏆 전체 최고 성과 종목:")
                print(f"   종목명: {overall_best.get('name', 'N/A')} ({overall_best.get('ticker', 'N/A')})")
                print(f"   최고 수익률: {overall_best.get('max_return', 0):.2f}%")
                print(f"   현재 수익률: {overall_best.get('current_return', 0):.2f}%")
            
            if worst_stocks:
                overall_worst = min(worst_stocks, key=lambda x: x.get("max_return", 0))
                print(f"\n⚠️  전체 최악 성과 종목:")
                print(f"   종목명: {overall_worst.get('name', 'N/A')} ({overall_worst.get('ticker', 'N/A')})")
                print(f"   최저 수익률: {overall_worst.get('max_return', 0):.2f}%")
                print(f"   현재 수익률: {overall_worst.get('current_return', 0):.2f}%")
    
    # 월간 보고서 통계
    print("\n" + "=" * 80)
    print("📅 월간 보고서 통계")
    print("=" * 80)
    print(f"총 월간 보고서 수: {len(monthly_reports)}개")
    
    if monthly_reports:
        for report in monthly_reports:
            stats = report.get("statistics", {})
            year = report.get("year", "N/A")
            month = report.get("month", "N/A")
            
            if stats:
                print(f"\n{year}년 {month}월:")
                print(f"  추천 종목 수: {stats.get('total_stocks', 0)}개")
                print(f"  평균 수익률: {stats.get('avg_return', 0):.2f}%")
                print(f"  양수 수익률 비율: {stats.get('positive_rate', 0):.2f}%")
                if stats.get("best_stock"):
                    best = stats["best_stock"]
                    print(f"  최고 종목: {best.get('name', 'N/A')} ({best.get('max_return', 0):.2f}%)")
    
    # 분기 보고서 통계
    print("\n" + "=" * 80)
    print("📊 분기 보고서 통계")
    print("=" * 80)
    print(f"총 분기 보고서 수: {len(quarterly_reports)}개")
    
    if quarterly_reports:
        for report in quarterly_reports:
            stats = report.get("statistics", {})
            year = report.get("year", "N/A")
            quarter = report.get("quarter", "N/A")
            
            if stats:
                print(f"\n{year}년 {quarter}분기:")
                print(f"  추천 종목 수: {stats.get('total_stocks', 0)}개")
                print(f"  평균 수익률: {stats.get('avg_return', 0):.2f}%")
                print(f"  양수 수익률 비율: {stats.get('positive_rate', 0):.2f}%")
                if stats.get("best_stock"):
                    best = stats["best_stock"]
                    print(f"  최고 종목: {best.get('name', 'N/A')} ({best.get('max_return', 0):.2f}%)")
    
    # 종목별 반복 추천 분석
    print("\n" + "=" * 80)
    print("🔄 종목별 반복 추천 분석")
    print("=" * 80)
    
    stock_recommendations = defaultdict(int)
    stock_performance = defaultdict(list)
    
    for report in weekly_reports:
        stocks = report.get("stocks", [])
        for stock in stocks:
            ticker = stock.get("ticker", "N/A")
            stock_recommendations[ticker] += 1
            stock_performance[ticker].append(stock.get("max_return", 0))
    
    if stock_recommendations:
        most_recommended = sorted(stock_recommendations.items(), key=lambda x: x[1], reverse=True)[:10]
        print("\n가장 자주 추천된 종목 TOP 10:")
        for ticker, count in most_recommended:
            avg_return = sum(stock_performance[ticker]) / len(stock_performance[ticker])
            print(f"  {ticker}: {count}회 추천, 평균 수익률: {avg_return:.2f}%")
    
    # 종합 평가
    print("\n" + "=" * 80)
    print("⭐ 종합 평가")
    print("=" * 80)
    
    if all_weekly_stats:
        avg_return = sum(avg_returns) / len(avg_returns)
        avg_positive_rate = sum(positive_rates) / len(positive_rates)
        
        print(f"\n📊 핵심 지표:")
        print(f"  평균 수익률: {avg_return:.2f}%")
        print(f"  양수 수익률 비율: {avg_positive_rate:.2f}%")
        print(f"  주간 평균 추천 종목 수: {total_stocks / len(all_weekly_stats):.1f}개")
        
        print(f"\n💡 평가:")
        
        # 수익률 평가
        if avg_return >= 30:
            return_grade = "매우 우수"
        elif avg_return >= 20:
            return_grade = "우수"
        elif avg_return >= 10:
            return_grade = "양호"
        elif avg_return >= 0:
            return_grade = "보통"
        else:
            return_grade = "개선 필요"
        
        # 승률 평가
        if avg_positive_rate >= 70:
            winrate_grade = "매우 우수"
        elif avg_positive_rate >= 60:
            winrate_grade = "우수"
        elif avg_positive_rate >= 50:
            winrate_grade = "양호"
        elif avg_positive_rate >= 40:
            winrate_grade = "보통"
        else:
            winrate_grade = "개선 필요"
        
        print(f"  수익률: {return_grade} ({avg_return:.2f}%)")
        print(f"  승률: {winrate_grade} ({avg_positive_rate:.2f}%)")
        
        # 종합 등급
        if avg_return >= 20 and avg_positive_rate >= 60:
            overall_grade = "A"
        elif avg_return >= 10 and avg_positive_rate >= 50:
            overall_grade = "B"
        elif avg_return >= 0 and avg_positive_rate >= 40:
            overall_grade = "C"
        else:
            overall_grade = "D"
        
        print(f"\n  종합 등급: {overall_grade}")
        
        print(f"\n📝 개선 사항:")
        if avg_return < 10:
            print(f"  - 평균 수익률 개선 필요 (현재: {avg_return:.2f}%)")
        if avg_positive_rate < 50:
            print(f"  - 양수 수익률 비율 개선 필요 (현재: {avg_positive_rate:.2f}%)")
        if total_stocks / len(all_weekly_stats) < 10:
            print(f"  - 추천 종목 수 증가 고려 (현재 주간 평균: {total_stocks / len(all_weekly_stats):.1f}개)")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    analyze_reports()



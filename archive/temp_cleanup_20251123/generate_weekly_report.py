#!/usr/bin/env python3
"""
이번 주 성과 보고서 생성
"""

import requests
import json
from datetime import datetime, timedelta

def get_weekly_data():
    """이번 주 스캔 데이터 수집"""
    # 이번 주 날짜들 (10월 27일-30일, 실제 거래일만)
    week_dates = ["20251027", "20251028", "20251029", "20251030"]
    
    weekly_stocks = []
    total_scans = 0
    
    for date in week_dates:
        try:
            # 각 날짜별 스캔 결과 조회
            url = f"https://sohntech.ai.kr/api/scan-by-date/{date[:4]}-{date[4:6]}-{date[6:8]}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    scan_data = data.get("data", {})
                    items = scan_data.get("items", [])
                    
                    print(f"{date}: {len(items)}개 종목")
                    total_scans += len(items)
                    
                    for item in items:
                        weekly_stocks.append({
                            "date": date,
                            "ticker": item.get("ticker"),
                            "name": item.get("name"),
                            "score": item.get("score", 0),
                            "score_label": item.get("score_label", ""),
                            "current_price": item.get("current_price", 0),
                            "change_rate": item.get("change_rate", 0),
                            "strategy": item.get("strategy", "")
                        })
                else:
                    print(f"{date}: 데이터 없음")
            else:
                print(f"{date}: API 오류 ({response.status_code})")
                
        except Exception as e:
            print(f"{date}: 요청 실패 - {e}")
    
    return weekly_stocks, total_scans

def analyze_weekly_performance(stocks):
    """주간 성과 분석"""
    if not stocks:
        return {
            "total_stocks": 0,
            "avg_score": 0,
            "score_distribution": {},
            "top_stocks": [],
            "daily_summary": {}
        }
    
    # 점수별 분포
    score_dist = {}
    total_score = 0
    
    # 일별 요약
    daily_summary = {}
    
    # 상위 종목 (점수 기준)
    top_stocks = sorted(stocks, key=lambda x: x["score"], reverse=True)[:10]
    
    for stock in stocks:
        score = stock["score"]
        date = stock["date"]
        
        total_score += score
        
        # 점수 분포
        score_range = f"{int(score)}-{int(score)+1}"
        score_dist[score_range] = score_dist.get(score_range, 0) + 1
        
        # 일별 요약
        if date not in daily_summary:
            daily_summary[date] = {"count": 0, "avg_score": 0, "total_score": 0}
        
        daily_summary[date]["count"] += 1
        daily_summary[date]["total_score"] += score
    
    # 일별 평균 점수 계산
    for date in daily_summary:
        if daily_summary[date]["count"] > 0:
            daily_summary[date]["avg_score"] = round(
                daily_summary[date]["total_score"] / daily_summary[date]["count"], 2
            )
    
    return {
        "total_stocks": len(stocks),
        "avg_score": round(total_score / len(stocks), 2) if stocks else 0,
        "score_distribution": score_dist,
        "top_stocks": top_stocks,
        "daily_summary": daily_summary
    }

def generate_report():
    """주간 보고서 생성"""
    print("=== 이번 주 성과 보고서 생성 ===")
    print("기간: 2025년 10월 27일 ~ 10월 30일")
    
    # 데이터 수집
    print("\n📊 데이터 수집 중...")
    stocks, total_scans = get_weekly_data()
    
    # 성과 분석
    print("\n📈 성과 분석 중...")
    analysis = analyze_weekly_performance(stocks)
    
    # 보고서 생성
    report = {
        "period": "2025년 10월 5주차 (10/27-10/30)",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "total_scans": total_scans,
            "total_stocks": analysis["total_stocks"],
            "avg_score": analysis["avg_score"],
            "trading_days": 4
        },
        "daily_breakdown": analysis["daily_summary"],
        "score_distribution": analysis["score_distribution"],
        "top_performers": analysis["top_stocks"][:5],
        "insights": generate_insights(analysis)
    }
    
    # 보고서 저장
    with open("weekly_report_2025_10_week5.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    return report

def generate_insights(analysis):
    """인사이트 생성"""
    insights = []
    
    if analysis["total_stocks"] == 0:
        insights.append("이번 주는 스캔 조건을 만족하는 종목이 없었습니다.")
        return insights
    
    # 평균 점수 분석
    avg_score = analysis["avg_score"]
    if avg_score >= 8:
        insights.append(f"평균 점수 {avg_score}로 매우 우수한 주간 성과를 보였습니다.")
    elif avg_score >= 6:
        insights.append(f"평균 점수 {avg_score}로 양호한 주간 성과를 보였습니다.")
    else:
        insights.append(f"평균 점수 {avg_score}로 보통 수준의 주간 성과를 보였습니다.")
    
    # 일별 분석
    daily = analysis["daily_summary"]
    if daily:
        best_day = max(daily.keys(), key=lambda x: daily[x]["count"])
        insights.append(f"가장 활발한 거래일은 {best_day}로 {daily[best_day]['count']}개 종목이 선별되었습니다.")
    
    # 상위 종목 분석
    top_stocks = analysis["top_stocks"]
    if top_stocks:
        best_stock = top_stocks[0]
        insights.append(f"최고 점수 종목: {best_stock['name']} ({best_stock['score']}점)")
    
    return insights

def print_report(report):
    """보고서 출력"""
    print(f"\n📋 {report['period']} 성과 보고서")
    print(f"생성일시: {report['generated_at']}")
    print("=" * 50)
    
    summary = report["summary"]
    print(f"📊 요약")
    print(f"  - 총 스캔 수: {summary['total_scans']}개")
    print(f"  - 선별 종목: {summary['total_stocks']}개")
    print(f"  - 평균 점수: {summary['avg_score']}")
    print(f"  - 거래일 수: {summary['trading_days']}일")
    
    print(f"\n📅 일별 현황")
    for date, data in report["daily_breakdown"].items():
        formatted_date = f"{date[:4]}-{date[4:6]}-{date[6:8]}"
        print(f"  {formatted_date}: {data['count']}개 (평균 {data['avg_score']}점)")
    
    print(f"\n🏆 상위 종목")
    for i, stock in enumerate(report["top_performers"], 1):
        print(f"  {i}. {stock['name']} ({stock['ticker']}) - {stock['score']}점")
    
    print(f"\n💡 인사이트")
    for insight in report["insights"]:
        print(f"  • {insight}")

if __name__ == "__main__":
    try:
        report = generate_report()
        print_report(report)
        print(f"\n✅ 보고서가 'weekly_report_2025_10_week5.json'에 저장되었습니다.")
    except Exception as e:
        print(f"❌ 보고서 생성 실패: {e}")
        import traceback
        traceback.print_exc()
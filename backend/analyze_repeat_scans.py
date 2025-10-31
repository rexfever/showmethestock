#!/usr/bin/env python3
"""
반복 스캔 종목 분석 스크립트
반복적으로 스캔되는 종목들의 의미와 투자 성과를 분석합니다.
"""

import sqlite3
from collections import Counter, defaultdict
import json
from datetime import datetime, timedelta

def analyze_repeat_scans():
    """반복 스캔 종목 분석"""
    
    # DB 연결
    conn = sqlite3.connect('snapshots.db')
    cursor = conn.cursor()
    
    print("=" * 70)
    print("🔄 반복 스캔 종목 분석 리포트")
    print("=" * 70)
    
    # 최근 60일간 데이터 조회
    cursor.execute('''
        SELECT date, code, name, score, strategy 
        FROM scan_rank 
        WHERE date >= date('now', '-60 days')
        ORDER BY date DESC
    ''')
    
    data = cursor.fetchall()
    
    # 종목별 데이터 정리
    stock_data = defaultdict(list)
    for date, code, name, score, strategy in data:
        stock_data[code].append({
            'date': date,
            'name': name,
            'score': score or 0,
            'strategy': strategy or ''
        })
    
    # 반복 스캔 종목 필터링 (3회 이상)
    frequent_stocks = {code: records for code, records in stock_data.items() 
                      if len(records) >= 3}
    
    print(f"📊 총 분석 데이터: {len(data)}개 레코드")
    print(f"🔄 반복 스캔 종목: {len(frequent_stocks)}개")
    print()
    
    # 1. 스캔 빈도별 분석
    print("📈 1. 스캔 빈도별 분석")
    print("-" * 50)
    
    frequency_groups = defaultdict(list)
    for code, records in frequent_stocks.items():
        name = records[0]['name']
        freq = len(records)
        avg_score = sum(r['score'] for r in records) / len(records)
        
        if freq >= 7:
            frequency_groups['매우높음(7회+)'].append((name, freq, avg_score))
        elif freq >= 5:
            frequency_groups['높음(5-6회)'].append((name, freq, avg_score))
        else:
            frequency_groups['보통(3-4회)'].append((name, freq, avg_score))
    
    for group, stocks in frequency_groups.items():
        print(f"\n🔸 {group}: {len(stocks)}개")
        for name, freq, score in sorted(stocks, key=lambda x: x[1], reverse=True)[:5]:
            print(f"   • {name}: {freq}회 (평균점수 {score:.1f})")
    
    # 2. 전략 패턴 분석
    print("\n🎯 2. 전략 패턴 분석")
    print("-" * 50)
    
    strategy_analysis = Counter()
    strategy_performance = defaultdict(list)
    
    for code, records in frequent_stocks.items():
        strategies = [r['strategy'] for r in records if r['strategy']]
        scores = [r['score'] for r in records]
        avg_score = sum(scores) / len(scores)
        
        for strategy in strategies:
            strategy_analysis[strategy] += 1
            strategy_performance[strategy].append(avg_score)
    
    print("주요 전략별 출현 빈도:")
    for strategy, count in strategy_analysis.most_common(5):
        if strategy:
            avg_perf = sum(strategy_performance[strategy]) / len(strategy_performance[strategy])
            print(f"   • {strategy}: {count}회 (평균성과 {avg_perf:.1f})")
    
    # 3. 종목 특성별 분석
    print("\n🏢 3. 종목 특성별 분석")
    print("-" * 50)
    
    sector_keywords = {
        '대형주': ['삼성', 'LG', 'SK', '현대', '포스코', '네이버', '카카오'],
        'IT/반도체': ['반도체', '전자', '디스플레이', '소프트웨어', '게임'],
        '바이오/제약': ['바이오', '제약', '의료', '헬스케어'],
        '에너지/화학': ['에너지', '화학', '소재', '배터리'],
        '금융': ['증권', '은행', '보험', '카드', '금융'],
        '건설/부동산': ['건설', '부동산', '건축', '토목']
    }
    
    sector_analysis = defaultdict(list)
    
    for code, records in frequent_stocks.items():
        name = records[0]['name']
        freq = len(records)
        avg_score = sum(r['score'] for r in records) / len(records)
        
        categorized = False
        for sector, keywords in sector_keywords.items():
            if any(keyword in name for keyword in keywords):
                sector_analysis[sector].append((name, freq, avg_score))
                categorized = True
                break
        
        if not categorized:
            sector_analysis['기타'].append((name, freq, avg_score))
    
    for sector, stocks in sector_analysis.items():
        if stocks:
            avg_freq = sum(s[1] for s in stocks) / len(stocks)
            avg_score = sum(s[2] for s in stocks) / len(stocks)
            print(f"\n🔸 {sector}: {len(stocks)}개")
            print(f"   평균 스캔빈도: {avg_freq:.1f}회, 평균점수: {avg_score:.1f}")
            
            # 상위 3개 종목
            top_stocks = sorted(stocks, key=lambda x: x[1], reverse=True)[:3]
            for name, freq, score in top_stocks:
                print(f"   • {name}: {freq}회 ({score:.1f}점)")
    
    # 4. 투자 의미 및 시사점
    print("\n💡 4. 투자 의미 및 시사점")
    print("-" * 50)
    
    print("🎯 반복 스캔의 의미:")
    print("   1. 지속적 모멘텀: 기술적 신호가 반복 발생하는 종목")
    print("   2. 안정적 상승: 꾸준한 상승 패턴을 보이는 종목")
    print("   3. 시장 관심: 투자자들의 지속적 관심을 받는 종목")
    print("   4. 변동성 기회: 단기 트레이딩 기회를 제공하는 종목")
    
    print("\n📊 활용 방안:")
    print("   • 고빈도 스캔 종목: 포트폴리오 핵심 후보")
    print("   • 일관된 전략 종목: 중장기 투자 고려")
    print("   • 대형주 반복 스캔: 시장 전반 상승 신호")
    print("   • 섹터별 집중: 특정 업종의 상승 사이클 파악")
    
    # 5. 최고 성과 종목 상세 분석
    print("\n🏆 5. 최고 성과 종목 분석")
    print("-" * 50)
    
    # 스캔 빈도 기준 상위 3개
    top_frequent = sorted(frequent_stocks.items(), key=lambda x: len(x[1]), reverse=True)[:3]
    
    for i, (code, records) in enumerate(top_frequent, 1):
        name = records[0]['name']
        dates = [r['date'] for r in records]
        scores = [r['score'] for r in records]
        strategies = [r['strategy'] for r in records if r['strategy']]
        
        print(f"\n{i}. {name} ({code})")
        print(f"   스캔 횟수: {len(records)}회")
        print(f"   기간: {min(dates)} ~ {max(dates)}")
        print(f"   점수: {min(scores):.1f} ~ {max(scores):.1f} (평균 {sum(scores)/len(scores):.1f})")
        
        if strategies:
            strategy_count = Counter(strategies)
            main_strategy = strategy_count.most_common(1)[0]
            print(f"   주요전략: {main_strategy[0]} ({main_strategy[1]}회)")
    
    conn.close()
    
    print("\n" + "=" * 70)
    print("분석 완료")
    print("=" * 70)

if __name__ == "__main__":
    analyze_repeat_scans()
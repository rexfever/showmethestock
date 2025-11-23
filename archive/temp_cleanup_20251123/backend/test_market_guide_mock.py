#!/usr/bin/env python3
"""
Market Guide 목데이터 테스트
다양한 시장 상황을 시뮬레이션하여 가이드 메시지 확인
"""

from market_guide import get_market_guide, get_detailed_stock_advice
import json

def create_mock_scan_response(scenario_name, matched_count, rsi_threshold, stocks_data):
    """목 스캔 응답 생성"""
    items = []
    for stock in stocks_data:
        items.append({
            'ticker': stock['ticker'],
            'indicators': {'change_rate': stock['change_rate']},
            'flags': {'vol_expand': stock.get('vol_expand', False)}
        })
    
    return {
        'scenario': scenario_name,
        'matched_count': matched_count,
        'rsi_threshold': rsi_threshold,
        'items': items
    }

def test_market_scenarios():
    """다양한 시장 시나리오 테스트"""
    
    print("🎯 Market Guide 목데이터 테스트\n")
    
    # 시나리오 1: 강세장 (많은 종목, 높은 RSI, 대부분 상승)
    bull_market = create_mock_scan_response(
        "강세장", 12, 62,
        [
            {'ticker': '005930', 'change_rate': 3.2, 'vol_expand': True},
            {'ticker': '000660', 'change_rate': 2.8, 'vol_expand': True},
            {'ticker': '035420', 'change_rate': 4.1, 'vol_expand': False},
            {'ticker': '051910', 'change_rate': 1.9, 'vol_expand': True},
        ]
    )
    
    # 시나리오 2: 약세장 (적은 종목, 낮은 RSI, 대부분 하락)
    bear_market = create_mock_scan_response(
        "약세장", 2, 42,
        [
            {'ticker': '084110', 'change_rate': -4.2, 'vol_expand': False},
            {'ticker': '096530', 'change_rate': -2.1, 'vol_expand': False},
        ]
    )
    
    # 시나리오 3: 급락장 (매우 적은 종목, 매우 낮은 RSI, 큰 하락)
    crash_market = create_mock_scan_response(
        "급락장", 1, 35,
        [
            {'ticker': '005930', 'change_rate': -8.5, 'vol_expand': False},
        ]
    )
    
    # 시나리오 4: 중립장 (보통 종목 수, 보통 RSI, 혼재)
    neutral_market = create_mock_scan_response(
        "중립장", 5, 52,
        [
            {'ticker': '005930', 'change_rate': 0.8, 'vol_expand': False},
            {'ticker': '000660', 'change_rate': -0.5, 'vol_expand': True},
            {'ticker': '035420', 'change_rate': 1.2, 'vol_expand': False},
            {'ticker': '051910', 'change_rate': -1.1, 'vol_expand': False},
            {'ticker': '068270', 'change_rate': 0.3, 'vol_expand': True},
        ]
    )
    
    # 시나리오 5: 추천종목 없음
    no_result = create_mock_scan_response(
        "추천종목 없음", 1, 38,
        [
            {'ticker': 'NORESULT', 'change_rate': 0, 'vol_expand': False},
        ]
    )
    
    # 시나리오 6: 상승장 (적당한 종목, 좋은 RSI, 상승 우세)
    rising_market = create_mock_scan_response(
        "상승장", 7, 56,
        [
            {'ticker': '005930', 'change_rate': 2.1, 'vol_expand': True},
            {'ticker': '000660', 'change_rate': 1.5, 'vol_expand': False},
            {'ticker': '035420', 'change_rate': -0.3, 'vol_expand': False},
        ]
    )
    
    scenarios = [bull_market, bear_market, crash_market, neutral_market, no_result, rising_market]
    
    for scenario in scenarios:
        print(f"📊 {scenario['scenario']} 시나리오")
        print(f"   매칭 종목: {scenario['matched_count']}개")
        print(f"   RSI 임계값: {scenario['rsi_threshold']}")
        
        # 평균 등락률 계산
        valid_items = [item for item in scenario['items'] if item['ticker'] != 'NORESULT']
        if valid_items:
            avg_change = sum(item['indicators']['change_rate'] for item in valid_items) / len(valid_items)
            print(f"   평균 등락률: {avg_change:.2f}%")
        
        guide = get_market_guide(scenario)
        
        print(f"   🎯 시장 상황: {guide['market_condition']}")
        print(f"   💬 가이드: {guide['guide_message']}")
        print(f"   📈 전략: {guide['investment_strategy']}")
        print(f"   ⚠️  리스크: {guide['risk_level']}")
        print(f"   ⏰ 타이밍: {guide['timing_advice']}")
        print()

def test_individual_stock_advice():
    """개별 종목 조언 테스트"""
    
    print("🔍 개별 종목 조언 테스트\n")
    
    # 다양한 종목 상황 시뮬레이션
    stock_scenarios = [
        {
            'name': '고점수 급등주',
            'data': {'ticker': '005930', 'score': 9.2, 'indicators': {'change_rate': 5.8}, 'flags': {'vol_expand': True}}
        },
        {
            'name': '고점수 급락주', 
            'data': {'ticker': '084110', 'score': 8.5, 'indicators': {'change_rate': -6.2}, 'flags': {'vol_expand': False}}
        },
        {
            'name': '중간점수 보합주',
            'data': {'ticker': '000660', 'score': 6.1, 'indicators': {'change_rate': 0.2}, 'flags': {'vol_expand': True}}
        },
        {
            'name': '낮은점수 하락주',
            'data': {'ticker': '096530', 'score': 4.3, 'indicators': {'change_rate': -2.1}, 'flags': {'vol_expand': False}}
        },
        {
            'name': '중간점수 상승주',
            'data': {'ticker': '035420', 'score': 6.8, 'indicators': {'change_rate': 2.3}, 'flags': {'vol_expand': True}}
        }
    ]
    
    for scenario in stock_scenarios:
        print(f"📈 {scenario['name']}")
        stock_data = scenario['data']
        print(f"   종목: {stock_data['ticker']}")
        print(f"   점수: {stock_data['score']}")
        print(f"   등락률: {stock_data['indicators']['change_rate']}%")
        print(f"   거래량 확대: {stock_data['flags']['vol_expand']}")
        
        advice = get_detailed_stock_advice(stock_data)
        if advice:
            print(f"   💡 조언: {advice['advice']}")
            print(f"   🎯 행동: {advice['action']}")
            print(f"   ⏰ 타이밍: {advice['timing']}")
            print(f"   ⚠️  리스크: {advice['risk']}")
        print()

def test_edge_cases():
    """극단적 상황 테스트"""
    
    print("🚨 극단적 상황 테스트\n")
    
    # 극단 케이스들
    edge_cases = [
        {
            'name': '초강세장 (매우 많은 종목)',
            'data': create_mock_scan_response("초강세장", 25, 68, [
                {'ticker': f'00{i:04d}', 'change_rate': 3 + i*0.5, 'vol_expand': True} 
                for i in range(5)
            ])
        },
        {
            'name': '패닉 상황 (0개 종목)',
            'data': create_mock_scan_response("패닉", 0, 25, [])
        },
        {
            'name': '혼조세 (큰 변동성)',
            'data': create_mock_scan_response("혼조세", 6, 48, [
                {'ticker': '005930', 'change_rate': 7.2, 'vol_expand': True},
                {'ticker': '000660', 'change_rate': -5.8, 'vol_expand': True},
                {'ticker': '035420', 'change_rate': 3.1, 'vol_expand': False},
                {'ticker': '051910', 'change_rate': -4.2, 'vol_expand': True},
            ])
        }
    ]
    
    for case in edge_cases:
        print(f"⚡ {case['name']}")
        guide = get_market_guide(case['data'])
        print(f"   시장 상황: {guide['market_condition']}")
        print(f"   가이드: {guide['guide_message']}")
        print(f"   리스크: {guide['risk_level']}")
        print()

if __name__ == "__main__":
    test_market_scenarios()
    test_individual_stock_advice() 
    test_edge_cases()
    print("✅ 모든 테스트 완료!")
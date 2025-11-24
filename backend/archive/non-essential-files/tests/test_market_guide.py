#!/usr/bin/env python3
"""
Market Guide 기능 테스트
"""

from market_guide import get_market_guide, get_detailed_stock_advice

def test_market_guide():
    """다양한 시장 상황에 대한 가이드 테스트"""
    
    print("=== Market Guide 테스트 ===\n")
    
    # 테스트 케이스 1: 강세장 (많은 종목, 높은 RSI, 상승)
    print("1. 강세장 시나리오:")
    strong_market = {
        'matched_count': 15,
        'rsi_threshold': 60,
        'items': [
            {'ticker': '005930', 'indicators': {'change_rate': 2.5}, 'flags': {'vol_expand': True}},
            {'ticker': '000660', 'indicators': {'change_rate': 1.8}, 'flags': {'vol_expand': True}},
            {'ticker': '035420', 'indicators': {'change_rate': 3.2}, 'flags': {'vol_expand': False}}
        ]
    }
    guide = get_market_guide(strong_market)
    print(f"시장 상황: {guide['market_condition']}")
    print(f"가이드: {guide['guide_message']}")
    print(f"전략: {guide['investment_strategy']}")
    print(f"리스크: {guide['risk_level']}")
    print(f"타이밍: {guide['timing_advice']}\n")
    
    # 테스트 케이스 2: 약세장 (적은 종목, 낮은 RSI, 하락)
    print("2. 약세장 시나리오:")
    weak_market = {
        'matched_count': 2,
        'rsi_threshold': 44,
        'items': [
            {'ticker': '084110', 'indicators': {'change_rate': -3.38}, 'flags': {'vol_expand': False}},
            {'ticker': '096530', 'indicators': {'change_rate': -0.95}, 'flags': {'vol_expand': False}}
        ]
    }
    guide = get_market_guide(weak_market)
    print(f"시장 상황: {guide['market_condition']}")
    print(f"가이드: {guide['guide_message']}")
    print(f"전략: {guide['investment_strategy']}")
    print(f"리스크: {guide['risk_level']}")
    print(f"타이밍: {guide['timing_advice']}\n")
    
    # 테스트 케이스 3: NORESULT 상황
    print("3. 추천종목 없음 시나리오:")
    no_result = {
        'matched_count': 1,
        'rsi_threshold': 40,
        'items': [
            {'ticker': 'NORESULT', 'indicators': {'change_rate': 0}, 'flags': {'vol_expand': False}}
        ]
    }
    guide = get_market_guide(no_result)
    print(f"시장 상황: {guide['market_condition']}")
    print(f"가이드: {guide['guide_message']}")
    print(f"전략: {guide['investment_strategy']}")
    print(f"리스크: {guide['risk_level']}")
    print(f"타이밍: {guide['timing_advice']}\n")
    
    # 테스트 케이스 4: 중립 시장
    print("4. 중립 시장 시나리오:")
    neutral_market = {
        'matched_count': 5,
        'rsi_threshold': 50,
        'items': [
            {'ticker': '005930', 'indicators': {'change_rate': 0.5}, 'flags': {'vol_expand': False}},
            {'ticker': '000660', 'indicators': {'change_rate': -0.3}, 'flags': {'vol_expand': True}},
            {'ticker': '035420', 'indicators': {'change_rate': 1.1}, 'flags': {'vol_expand': False}}
        ]
    }
    guide = get_market_guide(neutral_market)
    print(f"시장 상황: {guide['market_condition']}")
    print(f"가이드: {guide['guide_message']}")
    print(f"전략: {guide['investment_strategy']}")
    print(f"리스크: {guide['risk_level']}")
    print(f"타이밍: {guide['timing_advice']}\n")

def test_stock_advice():
    """개별 종목 조언 테스트"""
    
    print("=== 개별 종목 조언 테스트 ===\n")
    
    # 고점수 상승 종목
    print("1. 고점수 상승 종목:")
    high_score_up = {
        'ticker': '005930',
        'score': 8.5,
        'indicators': {'change_rate': 2.1},
        'flags': {'vol_expand': True}
    }
    advice = get_detailed_stock_advice(high_score_up)
    if advice:
        print(f"조언: {advice['advice']}")
        print(f"행동: {advice['action']}")
        print(f"타이밍: {advice['timing']}")
        print(f"리스크: {advice['risk']}\n")
    
    # 고점수 하락 종목
    print("2. 고점수 하락 종목:")
    high_score_down = {
        'ticker': '084110',
        'score': 8.0,
        'indicators': {'change_rate': -3.38},
        'flags': {'vol_expand': False}
    }
    advice = get_detailed_stock_advice(high_score_down)
    if advice:
        print(f"조언: {advice['advice']}")
        print(f"행동: {advice['action']}")
        print(f"타이밍: {advice['timing']}")
        print(f"리스크: {advice['risk']}\n")
    
    # 중간점수 종목
    print("3. 중간점수 종목:")
    mid_score = {
        'ticker': '096530',
        'score': 6.0,
        'indicators': {'change_rate': -0.95},
        'flags': {'vol_expand': False}
    }
    advice = get_detailed_stock_advice(mid_score)
    if advice:
        print(f"조언: {advice['advice']}")
        print(f"행동: {advice['action']}")
        print(f"타이밍: {advice['timing']}")
        print(f"리스크: {advice['risk']}\n")
    
    # NORESULT 테스트
    print("4. NORESULT 종목:")
    noresult = {
        'ticker': 'NORESULT',
        'score': 0,
        'indicators': {'change_rate': 0},
        'flags': {'vol_expand': False}
    }
    advice = get_detailed_stock_advice(noresult)
    print(f"조언: {advice if advice else 'None (정상적으로 None 반환)'}\n")

if __name__ == "__main__":
    test_market_guide()
    test_stock_advice()
    print("=== 테스트 완료 ===")
"""
전략 결정 디버깅 스크립트
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scanner_v2.core.strategy import determine_trading_strategy

# 테스트 케이스: 유바이로직스와 유사한 상황
test_cases = [
    {
        "name": "케이스 1: adjusted_score = 9.0, 모든 지표 False",
        "flags": {
            "cross": False,
            "vol_expand": False,
            "macd_ok": False,
            "rsi_ok": False,
            "tema_slope_ok": False,
            "obv_slope_ok": False,
            "above_cnt5_ok": False,
            "dema_slope_ok": False
        },
        "adjusted_score": 9.0
    },
    {
        "name": "케이스 2: adjusted_score = 8.0, 모든 지표 False",
        "flags": {
            "cross": False,
            "vol_expand": False,
            "macd_ok": False,
            "rsi_ok": False,
            "tema_slope_ok": False,
            "obv_slope_ok": False,
            "above_cnt5_ok": False,
            "dema_slope_ok": False
        },
        "adjusted_score": 8.0
    },
    {
        "name": "케이스 3: adjusted_score = 6.0, 모든 지표 False",
        "flags": {
            "cross": False,
            "vol_expand": False,
            "macd_ok": False,
            "rsi_ok": False,
            "tema_slope_ok": False,
            "obv_slope_ok": False,
            "above_cnt5_ok": False,
            "dema_slope_ok": False
        },
        "adjusted_score": 6.0
    },
    {
        "name": "케이스 4: adjusted_score = 5.9, 모든 지표 False",
        "flags": {
            "cross": False,
            "vol_expand": False,
            "macd_ok": False,
            "rsi_ok": False,
            "tema_slope_ok": False,
            "obv_slope_ok": False,
            "above_cnt5_ok": False,
            "dema_slope_ok": False
        },
        "adjusted_score": 5.9
    }
]

print("=== 전략 결정 디버깅 ===\n")

for case in test_cases:
    print(f"{case['name']}")
    print(f"  adjusted_score: {case['adjusted_score']}")
    
    # momentum_score 계산
    momentum_score = 0
    if case['flags'].get("cross"):
        momentum_score += 3
    if case['flags'].get("vol_expand"):
        momentum_score += 2
    if case['flags'].get("macd_ok"):
        momentum_score += 1
    if case['flags'].get("rsi_ok"):
        momentum_score += 1
    
    # trend_score 계산
    trend_score = 0
    if case['flags'].get("tema_slope_ok"):
        trend_score += 2
    if case['flags'].get("obv_slope_ok"):
        trend_score += 2
    if case['flags'].get("above_cnt5_ok"):
        trend_score += 2
    if case['flags'].get("dema_slope_ok"):
        trend_score += 2
    
    print(f"  momentum_score: {momentum_score}")
    print(f"  trend_score: {trend_score}")
    
    # 전략 결정
    strategy, target_profit, stop_loss, holding_period = determine_trading_strategy(
        case['flags'], 
        case['adjusted_score']
    )
    
    # 레이블 결정
    if case['adjusted_score'] >= 10:
        label = "강한 매수"
    elif case['adjusted_score'] >= 8:
        label = "매수 후보"
    elif case['adjusted_score'] >= 6:
        label = "관심 종목"
    else:
        label = "후보 종목"
    
    print(f"  결과:")
    print(f"    레이블: {label}")
    print(f"    전략: {strategy}")
    print(f"    목표수익률: {target_profit}")
    print(f"    손절기준: {stop_loss}")
    print(f"    보유기간: {holding_period}")
    print()





































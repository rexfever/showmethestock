"""
시장 상황에 따른 투자 가이드 메시지 생성
"""

def get_market_guide(scan_result):
    """
    스캔 결과를 분석하여 시장 상황에 맞는 투자 가이드 제공
    
    Args:
        scan_result: 스캔 결과 딕셔너리
        
    Returns:
        dict: 가이드 메시지와 투자 전략
    """
    matched_count = scan_result.get('matched_count', 0)
    rsi_threshold = scan_result.get('rsi_threshold', 58)
    items = scan_result.get('items', [])
    
    # 추천 종목들의 평균 등락률 계산
    total_change_rate = 0
    declining_count = 0
    
    for item in items:
        if item.get('ticker') == 'NORESULT':
            continue
        change_rate = item.get('indicators', {}).get('change_rate', 0)
        total_change_rate += change_rate
        if change_rate < 0:
            declining_count += 1
    
    avg_change_rate = total_change_rate / len(items) if items else 0
    declining_ratio = declining_count / len(items) if items else 0
    
    # 시장 상황 판단
    market_condition = _analyze_market_condition(
        matched_count, rsi_threshold, avg_change_rate, declining_ratio
    )
    
    # 가이드 메시지 생성
    guide = _generate_guide_message(market_condition, matched_count, items)
    
    return {
        "market_condition": market_condition,
        "guide_message": guide["message"],
        "investment_strategy": guide["strategy"],
        "risk_level": guide["risk_level"],
        "timing_advice": guide["timing"]
    }

def _analyze_market_condition(matched_count, rsi_threshold, avg_change_rate, declining_ratio):
    """시장 상황 분석 (고도화된 버전)"""
    
    # 점수 기반 종합 판단
    bull_score = 0
    bear_score = 0
    
    # 1. 매칭 종목 수 평가
    if matched_count >= 15:
        bull_score += 3
    elif matched_count >= 10:
        bull_score += 2
    elif matched_count >= 5:
        bull_score += 1
    elif matched_count <= 2:
        bear_score += 2
    elif matched_count <= 1:
        bear_score += 3
    
    # 2. RSI 임계값 평가 (시장 과열/침체)
    if rsi_threshold >= 65:
        bull_score += 2
    elif rsi_threshold >= 55:
        bull_score += 1
    elif rsi_threshold <= 40:
        bear_score += 2
    elif rsi_threshold <= 45:
        bear_score += 1
    
    # 3. 평균 등락률 평가
    if avg_change_rate >= 2.0:
        bull_score += 2
    elif avg_change_rate >= 1.0:
        bull_score += 1
    elif avg_change_rate <= -2.0:
        bear_score += 3
    elif avg_change_rate <= -1.0:
        bear_score += 2
    elif avg_change_rate < 0:
        bear_score += 1
    
    # 4. 하락 종목 비율 평가
    if declining_ratio <= 0.2:
        bull_score += 2
    elif declining_ratio <= 0.4:
        bull_score += 1
    elif declining_ratio >= 0.8:
        bear_score += 3
    elif declining_ratio >= 0.6:
        bear_score += 2
    
    # 종합 판단
    if bull_score >= 6:
        return "강세"
    elif bull_score >= 4:
        return "상승"
    elif bear_score >= 6:
        return "급락"
    elif bear_score >= 4:
        return "약세"
    else:
        return "중립"

def _generate_guide_message(condition, matched_count, items):
    """시장 상황별 가이드 메시지 생성"""
    
    guides = {
        "강세": {
            "message": "🚀 강세장입니다. 적극적인 매수 기회를 활용하세요.",
            "strategy": "즉시 매수 후 단기 수익 실현 전략",
            "risk_level": "낮음",
            "timing": "장 시작 직후 또는 상승 모멘텀 확인 시 매수"
        },
        "상승": {
            "message": "📈 상승 추세입니다. 선별적 매수를 고려하세요.",
            "strategy": "우량주 중심 매수, 분할 매수 권장",
            "risk_level": "보통",
            "timing": "시초가 확인 후 매수, 급등 시 추격 매수 지양"
        },
        "중립": {
            "message": "⚖️ 중립적 시장입니다. 신중한 접근이 필요합니다.",
            "strategy": "관망 또는 소량 분할 매수",
            "risk_level": "보통",
            "timing": "하락 시 매수, 상승 확인 후 추가 매수"
        },
        "약세": {
            "message": "⚠️ 약세장입니다. 매수보다는 관망을 권장합니다.",
            "strategy": "관심종목 등록 후 추가 하락 시 매수 기회 포착",
            "risk_level": "높음",
            "timing": "당일 매수 지양, 익일 시초가 확인 후 판단"
        },
        "급락": {
            "message": "🔴 급락장입니다. 매수는 피하고 현금 보유를 권장합니다.",
            "strategy": "전면 관망, 바닥 확인 후 점진적 진입",
            "risk_level": "매우 높음",
            "timing": "2-3일 후 시장 안정화 확인 후 매수 검토"
        }
    }
    
    base_guide = guides.get(condition, guides["중립"])
    
    # 추천 종목이 없는 경우 특별 메시지
    if matched_count == 0:
        base_guide["message"] = "😔 추천 종목이 없습니다. 시장 상황이 좋지 않으니 휴식을 권장합니다."
        base_guide["strategy"] = "전면 관망, 투자 휴식"
        base_guide["timing"] = "시장 회복 신호까지 대기"
    
    # NORESULT인 경우
    elif len(items) == 1 and items[0].get('ticker') == 'NORESULT':
        base_guide["message"] = "☕ 장이 좋지 않아 추천 종목이 없습니다. 투자에도 휴식이 필요합니다."
        base_guide["strategy"] = "현금 보유, 다음 기회 대기"
        base_guide["timing"] = "시장 개선 시까지 관망"
    
    return base_guide

def get_detailed_stock_advice(item):
    """개별 종목에 대한 상세 투자 조언"""
    
    if not item or item.get('ticker') == 'NORESULT':
        return None
    
    score = item.get('score', 0)
    change_rate = item.get('indicators', {}).get('change_rate', 0)
    volume_ok = item.get('flags', {}).get('vol_expand', False)
    
    # 점수별 기본 조언
    if score >= 8:
        base_advice = "강력 추천 종목"
        action = "적극 매수"
    elif score >= 6:
        base_advice = "매수 후보"
        action = "선별 매수"
    elif score >= 4:
        base_advice = "관심 종목"
        action = "관망 후 매수"
    else:
        base_advice = "투자 부적합"
        action = "매수 지양"
    
    # 현재 상황별 조정
    if change_rate < -3:
        timing = "급락 중이므로 추가 하락 확인 후 매수"
        risk = "높음"
    elif change_rate < 0:
        timing = "하락 중이므로 신중한 매수"
        risk = "보통"
    elif change_rate > 3:
        timing = "급등 중이므로 추격 매수 지양"
        risk = "높음"
    else:
        timing = "적정 수준에서 매수 고려"
        risk = "낮음"
    
    # 거래량 고려
    if not volume_ok:
        timing += ", 거래량 부족으로 유동성 주의"
    
    return {
        "advice": base_advice,
        "action": action,
        "timing": timing,
        "risk": risk
    }
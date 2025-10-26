"""
일반인도 이해할 수 있는 주식 분석 결과 제공 모듈
"""

def get_user_friendly_analysis(analysis_result):
    """
    기술적 분석 결과를 일반인이 이해하기 쉬운 언어로 변환
    
    Args:
        analysis_result: /analyze API의 응답 데이터 (AnalyzeResponse 객체)
        
    Returns:
        dict: 사용자 친화적인 분석 결과
    """
    if not analysis_result or not analysis_result.ok or not analysis_result.item:
        return {
            'summary': '분석할 수 없습니다.',
            'recommendation': '분석 실패',
            'confidence': '낮음',
            'explanation': '종목 데이터를 가져올 수 없어 분석이 불가능합니다.'
        }
    
    item = analysis_result.item
    indicators = item.indicators.__dict__ if item.indicators else {}
    flags = item.flags.__dict__ if item.flags else {}
    trend = item.trend.__dict__ if item.trend else {}
    score = item.score
    match = item.match
    
    # trend 데이터를 indicators에 병합
    indicators.update(trend)
    
    # 1. 종합 평가
    summary, recommendation, confidence = get_overall_assessment(score, match, flags)
    
    # 2. 상세 설명
    explanations = get_detailed_explanations(indicators, flags, score)
    
    # 3. 투자 조언
    investment_advice = get_investment_advice(score, match, indicators, flags)
    
    # 4. 주의사항
    warnings = get_warnings(indicators, flags)
    
    return {
        'summary': summary,
        'recommendation': recommendation,
        'confidence': confidence,
        'explanations': explanations,
        'investment_advice': investment_advice,
        'warnings': warnings,
        'simple_indicators': get_simple_indicators(indicators)
    }


def get_overall_assessment(score, match, flags):
    """종합 평가 및 추천도"""
    
    # 점수 기반 평가
    if score >= 8:
        summary = "매우 좋은 투자 기회"
        recommendation = "강력 추천"
        confidence = "높음"
    elif score >= 6:
        summary = "좋은 투자 기회"
        recommendation = "추천"
        confidence = "보통"
    elif score >= 4:
        summary = "관심 종목"
        recommendation = "관심"
        confidence = "낮음"
    elif score >= 2:
        summary = "신중한 검토 필요"
        recommendation = "신중"
        confidence = "낮음"
    else:
        summary = "투자 부적합"
        recommendation = "비추천"
        confidence = "매우 낮음"
    
    # 매칭 여부에 따른 조정
    if not match:
        if "유동성부족" in str(flags.get('label', '')):
            summary = "거래량이 너무 적어 투자 부적합"
            recommendation = "비추천"
        elif "저가종목" in str(flags.get('label', '')):
            summary = "가격이 너무 낮아 위험"
            recommendation = "비추천"
        elif "과열" in str(flags.get('label', '')):
            summary = "현재 과열 상태로 조정 가능성 높음"
            recommendation = "신중"
        else:
            summary = "현재 투자 조건 미충족"
            recommendation = "관심"
    
    return summary, recommendation, confidence


def get_detailed_explanations(indicators, flags, score):
    """상세 설명"""
    explanations = []
    
    # 골든크로스 설명
    if flags.get('cross'):
        explanations.append({
            'title': '📈 상승 신호 포착',
            'description': '단기 이동평균선이 장기 이동평균선을 위로 뚫고 올라갔습니다. 이는 주가 상승의 신호로 해석됩니다.',
            'impact': '긍정적'
        })
    
    # 거래량 설명
    if flags.get('vol_expand'):
        explanations.append({
            'title': '📊 거래량 급증',
            'description': '평소보다 거래량이 크게 늘어났습니다. 많은 투자자들이 이 종목에 관심을 보이고 있다는 의미입니다.',
            'impact': '긍정적'
        })
    
    # MACD 설명
    if flags.get('macd_ok'):
        if flags.get('macd_golden_cross'):
            explanations.append({
                'title': '⚡ 모멘텀 전환',
                'description': '주가의 상승 모멘텀이 강해지고 있습니다. 단기적으로 상승 가능성이 높아 보입니다.',
                'impact': '긍정적'
            })
        else:
            explanations.append({
                'title': '📈 상승 추세 지속',
                'description': '현재 상승 추세가 유지되고 있습니다.',
                'impact': '긍정적'
            })
    
    # RSI 설명
    rsi_tema = indicators.get('RSI_TEMA', 0)
    if rsi_tema > 70:
        explanations.append({
            'title': '⚠️ 과매수 상태',
            'description': '현재 주가가 과도하게 상승한 상태입니다. 조정 가능성이 있으니 주의가 필요합니다.',
            'impact': '부정적'
        })
    elif rsi_tema < 30:
        explanations.append({
            'title': '💡 과매도 상태',
            'description': '현재 주가가 과도하게 하락한 상태입니다. 반등 가능성이 있을 수 있습니다.',
            'impact': '긍정적'
        })
    elif 50 < rsi_tema < 70:
        explanations.append({
            'title': '📊 적정 수준',
            'description': '현재 주가 수준이 적정한 범위에 있습니다.',
            'impact': '중립'
        })
    
    # 점수별 설명
    if score >= 8:
        explanations.append({
            'title': '🎯 우수한 투자 조건',
            'description': '여러 기술적 지표가 모두 좋은 신호를 보이고 있습니다.',
            'impact': '긍정적'
        })
    elif score >= 6:
        explanations.append({
            'title': '✅ 양호한 투자 조건',
            'description': '대부분의 기술적 지표가 긍정적인 신호를 보이고 있습니다.',
            'impact': '긍정적'
        })
    elif score >= 4:
        explanations.append({
            'title': '🤔 보통 수준',
            'description': '일부 지표는 좋지만 전체적으로는 보통 수준입니다.',
            'impact': '중립'
        })
    else:
        explanations.append({
            'title': '❌ 투자 조건 부족',
            'description': '대부분의 기술적 지표가 투자에 부적합한 신호를 보이고 있습니다.',
            'impact': '부정적'
        })
    
    return explanations


def get_investment_advice(score, match, indicators, flags):
    """투자 조언"""
    advice = []
    
    if score >= 8 and match:
        advice.extend([
            "💪 강력한 매수 신호가 나타났습니다",
            "📈 단기적으로 상승 가능성이 높습니다",
            "💰 적절한 타이밍에 진입을 고려해보세요",
            "⏰ 단기 투자보다는 중기 관점에서 접근하세요"
        ])
    elif score >= 6 and match:
        advice.extend([
            "👍 매수 신호가 나타났습니다",
            "📊 관심을 가지고 지켜볼 만합니다",
            "💡 소량으로 시작해보는 것을 추천합니다",
            "📅 1-2주 정도 관찰 후 결정하세요"
        ])
    elif score >= 4:
        advice.extend([
            "🤔 신중한 관찰이 필요합니다",
            "📉 추가 하락 가능성도 고려하세요",
            "⏳ 더 나은 기회를 기다리는 것도 좋습니다",
            "📊 다른 종목과 비교해보세요"
        ])
    else:
        advice.extend([
            "❌ 현재는 투자하지 않는 것이 좋습니다",
            "📉 하락 위험이 높습니다",
            "⏰ 더 나은 기회를 기다리세요",
            "🔍 다른 종목을 찾아보세요"
        ])
    
    # 특별한 상황별 조언
    if flags.get('label') == '과열':
        advice.append("🔥 현재 과열 상태이므로 조정 후 진입을 고려하세요")
    
    if indicators.get('RSI_TEMA', 0) > 75:
        advice.append("⚠️ RSI가 매우 높아 조정 가능성이 큽니다")
    
    if indicators.get('VOL', 0) > indicators.get('VOL_MA5', 0) * 3:
        advice.append("📊 거래량이 급증했으니 주가 변동이 클 수 있습니다")
    
    return advice


def get_warnings(indicators, flags):
    """주의사항"""
    warnings = []
    
    # 기본 주의사항
    warnings.append("📚 주식 투자는 원금 손실 위험이 있습니다")
    warnings.append("💡 이 분석은 참고용이며, 투자 결정은 본인 책임입니다")
    warnings.append("📊 시장 상황에 따라 결과가 달라질 수 있습니다")
    
    # 기술적 지표 기반 경고
    rsi_tema = indicators.get('RSI_TEMA', 0)
    if rsi_tema > 80:
        warnings.append("🚨 RSI가 매우 높아 급격한 하락 위험이 있습니다")
    elif rsi_tema < 20:
        warnings.append("📉 RSI가 매우 낮아 추가 하락 가능성이 있습니다")
    
    # 거래량 관련 경고
    vol_ratio = indicators.get('VOL', 0) / indicators.get('VOL_MA5', 1) if indicators.get('VOL_MA5', 0) > 0 else 1
    if vol_ratio > 5:
        warnings.append("📊 거래량이 급증했으니 변동성이 클 수 있습니다")
    
    # 특별한 상황 경고
    if flags.get('label') == '유동성부족':
        warnings.append("💧 거래량이 적어 매매가 어려울 수 있습니다")
    
    if flags.get('label') == '저가종목':
        warnings.append("⚠️ 저가 종목은 변동성이 클 수 있습니다")
    
    return warnings


def get_simple_indicators(indicators):
    """간단한 지표 설명"""
    return {
        'current_price': {
            'value': f"{indicators.get('close', 0):,.0f}원",
            'description': '현재 주가'
        },
        'volume': {
            'value': f"{indicators.get('VOL', 0):,}주",
            'description': '오늘 거래량'
        },
        'rsi': {
            'value': f"{indicators.get('RSI_TEMA', 0):.1f}",
            'description': '과매수/과매도 지표 (70 이상: 과매수, 30 이하: 과매도)'
        },
        'trend': {
            'value': '상승' if indicators.get('TEMA20_SLOPE20', 0) > 0 else '하락',
            'description': f'현재 추세 방향 (TEMA20 기울기: {indicators.get("TEMA20_SLOPE20", 0):.2f})'
        }
    }

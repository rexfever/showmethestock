"""
일반인도 이해할 수 있는 주식 분석 결과 제공 모듈
"""

def get_user_friendly_analysis(analysis_result):
    """
    기술적 분석 결과를 일반인이 이해하기 쉬운 언어로 변환
    현재 상태 분석에 중점을 둠 (스캔 조건 매칭보다는 현재 상황 설명)
    
    Args:
        analysis_result: /analyze API의 응답 데이터 (AnalyzeResponse 객체)
        
    Returns:
        dict: 사용자 친화적인 분석 결과
    """
    if not analysis_result or not analysis_result.ok or not analysis_result.item:
        return {
            'summary': '분석할 수 없습니다.',
            'current_status': '데이터 부족',
            'market_position': '알 수 없음',
            'explanation': '종목 데이터를 가져올 수 없어 분석이 불가능합니다.'
        }
    
    item = analysis_result.item
    indicators = item.indicators.__dict__ if item.indicators else {}
    flags = item.flags.__dict__ if item.flags else {}
    trend = item.trend.__dict__ if item.trend else {}
    score = item.score
    
    # trend 데이터를 indicators에 병합
    indicators.update(trend)
    
    # 1. 현재 상태 분석
    current_status = analyze_current_status(indicators, flags)
    
    # 2. 시장 포지션 분석
    market_position = analyze_market_position(indicators, flags)
    
    # 3. 기술적 지표 상태
    technical_status = analyze_technical_indicators(indicators, flags)
    
    # 4. 종합 요약
    summary = generate_summary(current_status, market_position, technical_status)
    
    # 5. 주의사항
    warnings = get_warnings(indicators, flags)
    
    return {
        'summary': summary,
        'current_status': current_status,
        'market_position': market_position,
        'technical_status': technical_status,
        'warnings': warnings,
        'simple_indicators': get_simple_indicators(indicators)
    }


def analyze_current_status(indicators, flags):
    """현재 상태 분석"""
    rsi_tema = indicators.get('RSI_TEMA', 50)
    macd_osc = indicators.get('MACD_OSC', 0)
    vol_ratio = indicators.get('VOL', 0) / indicators.get('VOL_MA5', 1) if indicators.get('VOL_MA5', 0) > 0 else 1
    
    status_parts = []
    
    # RSI 기반 상태
    if rsi_tema > 70:
        status_parts.append("과매수 구간")
    elif rsi_tema < 30:
        status_parts.append("과매도 구간")
    elif rsi_tema > 50:
        status_parts.append("상승 모멘텀")
    else:
        status_parts.append("하락 모멘텀")
    
    # MACD 기반 상태
    if macd_osc > 0:
        status_parts.append("상승 추세")
    else:
        status_parts.append("하락 추세")
    
    # 거래량 상태
    if vol_ratio > 2:
        status_parts.append("거래량 급증")
    elif vol_ratio > 1.5:
        status_parts.append("거래량 증가")
    elif vol_ratio < 0.5:
        status_parts.append("거래량 감소")
    
    return ", ".join(status_parts)

def analyze_market_position(indicators, flags):
    """시장 포지션 분석"""
    tema20_slope = indicators.get('TEMA20_SLOPE20', 0)
    dema10_slope = indicators.get('DEMA10_SLOPE20', 0)
    above_cnt5 = indicators.get('ABOVE_CNT5', 0)
    
    if tema20_slope > 0.5 and dema10_slope > 0.5:
        return "강한 상승 추세"
    elif tema20_slope > 0 and dema10_slope > 0:
        return "상승 추세"
    elif tema20_slope < -0.5 and dema10_slope < -0.5:
        return "강한 하락 추세"
    elif tema20_slope < 0 and dema10_slope < 0:
        return "하락 추세"
    elif above_cnt5 >= 3:
        return "횡보 상승"
    elif above_cnt5 <= 2:
        return "횡보 하락"
    else:
        return "횡보 구간"

def analyze_technical_indicators(indicators, flags):
    """기술적 지표 상태 분석"""
    status = []
    
    # 골든크로스/데드크로스
    if flags.get('cross'):
        status.append("골든크로스 발생")
    
    # MACD 상태
    if flags.get('macd_golden_cross'):
        status.append("MACD 골든크로스")
    elif flags.get('macd_ok'):
        status.append("MACD 상승 신호")
    
    # 거래량 상태
    if flags.get('vol_expand'):
        status.append("거래량 확장")
    
    # RSI 상태
    rsi_tema = indicators.get('RSI_TEMA', 50)
    if rsi_tema > 70:
        status.append("RSI 과매수")
    elif rsi_tema < 30:
        status.append("RSI 과매도")
    
    return status if status else ["특별한 신호 없음"]

def generate_summary(current_status, market_position, technical_status):
    """종합 요약 생성"""
    return f"현재 {current_status} 상태이며, {market_position}를 보이고 있습니다."


# 기존 함수는 제거하고 새로운 분석 함수들로 대체됨


# 투자 조언 함수는 제거 - 현재 상태 분석에 집중


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

"""
전략 표시 End-to-End 테스트
실제 API 응답 구조를 시뮬레이션하여 전체 데이터 흐름 확인
"""
import pytest
import json


def simulate_backend_response():
    """백엔드 API 응답 시뮬레이션"""
    # 실제 DB에서 가져온 데이터 구조
    db_row = {
        "code": "206650",
        "name": "유바이오로직스",
        "score": 9.0,
        "score_label": "매수 후보",
        "current_price": 12740.0,
        "volume": 129952.0,
        "change_rate": 2.17,
        "market": None,
        "strategy": None,  # DB 컬럼에 없음
        "indicators": json.dumps({}),
        "trend": json.dumps({}),
        "flags": json.dumps({
            "trading_strategy": "포지션",
            "label": "매수 후보",
            "target_profit": 0.1,
            "stop_loss": -0.07,
            "holding_period": "2주~3개월"
        }),
        "details": json.dumps({}),
        "returns": None,
        "recurrence": None,
        "scanner_version": "v2"
    }
    
    # 백엔드 로직 (main.py의 get_scan_by_date)
    data = db_row
    strategy = data.get("strategy")
    
    flags = data.get("flags")
    flags_dict = {}
    if isinstance(flags, str) and flags:
        try:
            flags_dict = json.loads(flags)
        except:
            flags_dict = {}
    elif not flags:
        flags_dict = {}
    
    if not strategy and flags_dict and isinstance(flags_dict, dict):
        strategy = flags_dict.get('trading_strategy')
    
    # API 응답 생성
    api_response_item = {
        "ticker": data.get("code"),
        "name": data.get("name"),
        "score": data.get("score"),
        "score_label": data.get("score_label"),
        "strategy": strategy,
        "flags": flags_dict
    }
    
    return api_response_item


def simulate_frontend_processing(api_item):
    """프론트엔드 데이터 처리 시뮬레이션"""
    item = api_item
    
    # 프론트엔드 로직 (StockCardV2.js)
    strategy = item.get("strategy")
    flags = item.get("flags", {})
    
    strategyFromFlags = flags.get("trading_strategy") or None
    normalizedStrategy = (strategy and strategy.strip()) or (strategyFromFlags and strategyFromFlags.strip()) or '관찰'
    
    strategyConfig = {
        "스윙": { "icon": "⚡", "desc": "단기 매매 (3~10일)" },
        "포지션": { "icon": "📈", "desc": "중기 추세 추종 (2주~3개월)" },
        "장기": { "icon": "🌱", "desc": "장기 투자 (3개월 이상)" },
        "관찰": { "icon": "⏳", "desc": "관심 종목 (매수 대기)" }
    }
    
    strategyInfo = strategyConfig.get(normalizedStrategy) or strategyConfig["관찰"]
    
    return {
        "normalizedStrategy": normalizedStrategy,
        "strategyInfo": strategyInfo,
        "displayText": f"{strategyInfo['icon']} {normalizedStrategy}",
        "description": strategyInfo['desc']
    }


def test_end_to_end_strategy_display():
    """End-to-End 전략 표시 테스트"""
    # 1. 백엔드 응답 생성
    api_item = simulate_backend_response()
    
    # 검증: 백엔드에서 strategy가 올바르게 추출되었는지
    assert api_item["strategy"] == "포지션", f"백엔드 strategy 추출 실패: {api_item['strategy']}"
    assert api_item["flags"]["trading_strategy"] == "포지션"
    
    # 2. 프론트엔드 처리
    frontend_result = simulate_frontend_processing(api_item)
    
    # 검증: 프론트엔드에서 normalizedStrategy가 올바른지
    assert frontend_result["normalizedStrategy"] == "포지션", \
        f"프론트엔드 정규화 실패: {frontend_result['normalizedStrategy']}"
    assert frontend_result["strategyInfo"]["icon"] == "📈"
    assert "포지션" in frontend_result["displayText"]
    assert "중기 추세 추종" in frontend_result["description"]


def test_end_to_end_with_null_strategy():
    """strategy가 null인 경우 End-to-End 테스트"""
    # 백엔드 응답 (strategy가 null)
    api_item = {
        "ticker": "123456",
        "name": "테스트 종목",
        "score": 8.0,
        "score_label": "관심 종목",
        "strategy": None,
        "flags": {
            "trading_strategy": "장기",
            "label": "관심 종목"
        }
    }
    
    # 프론트엔드 처리
    frontend_result = simulate_frontend_processing(api_item)
    
    # 검증: flags.trading_strategy가 사용되어야 함
    assert frontend_result["normalizedStrategy"] == "장기"
    assert frontend_result["strategyInfo"]["icon"] == "🌱"


def test_end_to_end_with_no_strategy():
    """strategy와 flags.trading_strategy 모두 없는 경우"""
    # 백엔드 응답 (둘 다 없음)
    api_item = {
        "ticker": "123456",
        "name": "테스트 종목",
        "score": 5.0,
        "score_label": "후보 종목",
        "strategy": None,
        "flags": {}
    }
    
    # 프론트엔드 처리
    frontend_result = simulate_frontend_processing(api_item)
    
    # 검증: 기본값 "관찰"이 사용되어야 함
    assert frontend_result["normalizedStrategy"] == "관찰"
    assert frontend_result["strategyInfo"]["icon"] == "⏳"
    assert "관심 종목 (매수 대기)" in frontend_result["description"]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])





































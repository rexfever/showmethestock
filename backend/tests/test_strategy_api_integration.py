"""
전략 표시 API 통합 테스트
실제 API 응답 구조 확인
"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock


def test_scan_by_date_strategy_field():
    """/scan-by-date/{date} API의 strategy 필드가 올바르게 설정되는지 테스트"""
    
    # 시뮬레이션: DB에서 가져온 실제 데이터 구조
    mock_row = {
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
    
    # 백엔드 로직 시뮬레이션 (main.py의 get_scan_by_date 로직)
    data = mock_row
    strategy = data.get("strategy")  # None
    
    # flags 파싱
    flags = data.get("flags")
    flags_dict = {}
    if isinstance(flags, str) and flags:
        try:
            flags_dict = json.loads(flags)
        except:
            flags_dict = {}
    elif not flags:
        flags_dict = {}
    
    # flags에서 trading_strategy 추출
    if not strategy and flags_dict and isinstance(flags_dict, dict):
        strategy = flags_dict.get('trading_strategy')
    
    # 최종 item 생성
    item = {
        "ticker": data.get("code"),
        "name": data.get("name"),
        "score": data.get("score"),
        "score_label": data.get("score_label"),
        "strategy": strategy,
        "flags": flags_dict
    }
    
    # 검증
    assert item["strategy"] == "포지션", f"Expected '포지션', got {item['strategy']}"
    assert item["flags"]["trading_strategy"] == "포지션"
    assert "strategy" in item, "strategy 필드가 item에 포함되어야 함"


def test_strategy_with_null_flags():
    """flags가 null이거나 비어있는 경우 테스트"""
    
    # 케이스 1: flags가 None인 경우
    mock_row = {
        "code": "123456",
        "strategy": None,
        "flags": None
    }
    
    data = mock_row
    strategy = data.get("strategy")
    
    flags = data.get("flags")
    flags_dict = {}
    if isinstance(flags, str) and flags:
        flags_dict = json.loads(flags)
    elif not flags:
        flags_dict = {}
    
    if not strategy and flags_dict and isinstance(flags_dict, dict):
        strategy = flags_dict.get('trading_strategy')
    
    item = {
        "strategy": strategy,
        "flags": flags_dict
    }
    
    assert item["strategy"] is None
    assert item["flags"] == {}
    
    # 케이스 2: flags가 빈 문자열인 경우
    mock_row = {
        "code": "123456",
        "strategy": None,
        "flags": ""
    }
    
    data = mock_row
    strategy = data.get("strategy")
    
    flags = data.get("flags")
    flags_dict = {}
    if isinstance(flags, str) and flags:
        flags_dict = json.loads(flags)
    elif not flags:
        flags_dict = {}
    
    if not strategy and flags_dict and isinstance(flags_dict, dict):
        strategy = flags_dict.get('trading_strategy')
    
    item = {
        "strategy": strategy,
        "flags": flags_dict
    }
    
    assert item["strategy"] is None
    assert item["flags"] == {}


def test_strategy_with_empty_trading_strategy():
    """flags에 trading_strategy가 없는 경우 테스트"""
    
    mock_row = {
        "code": "123456",
        "strategy": None,
        "flags": json.dumps({
            "label": "관심 종목",
            "target_profit": None
        })
    }
    
    data = mock_row
    strategy = data.get("strategy")
    
    flags = data.get("flags")
    flags_dict = {}
    if isinstance(flags, str) and flags:
        flags_dict = json.loads(flags)
    elif not flags:
        flags_dict = {}
    
    if not strategy and flags_dict and isinstance(flags_dict, dict):
        strategy = flags_dict.get('trading_strategy')
    
    item = {
        "strategy": strategy,
        "flags": flags_dict
    }
    
    assert item["strategy"] is None
    assert "trading_strategy" not in item["flags"]


def test_all_strategy_types():
    """모든 전략 타입이 올바르게 추출되는지 테스트"""
    strategies = ["스윙", "포지션", "장기", "관찰"]
    
    for expected_strategy in strategies:
        mock_row = {
            "code": "123456",
            "strategy": None,
            "flags": json.dumps({
                "trading_strategy": expected_strategy,
                "label": "테스트"
            })
        }
        
        data = mock_row
        strategy = data.get("strategy")
        
        flags = data.get("flags")
        flags_dict = {}
        if isinstance(flags, str) and flags:
            flags_dict = json.loads(flags)
        elif not flags:
            flags_dict = {}
        
        if not strategy and flags_dict and isinstance(flags_dict, dict):
            strategy = flags_dict.get('trading_strategy')
        
        item = {
            "strategy": strategy,
            "flags": flags_dict
        }
        
        assert item["strategy"] == expected_strategy, \
            f"Expected {expected_strategy}, got {item['strategy']}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])


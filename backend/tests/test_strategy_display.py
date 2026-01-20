"""
전략 표시 로직 테스트
백엔드에서 프론트엔드로 전략 데이터가 올바르게 전달되는지 확인
"""
import pytest
import json
from unittest.mock import Mock, patch


def test_strategy_extraction_from_flags():
    """flags에서 trading_strategy 추출 테스트"""
    # 케이스 1: flags에 trading_strategy가 있는 경우
    flags_dict = {
        'trading_strategy': '포지션',
        'label': '매수 후보',
        'target_profit': 0.1
    }
    strategy = None
    if not strategy and flags_dict and isinstance(flags_dict, dict):
        strategy = flags_dict.get('trading_strategy')
    assert strategy == '포지션'
    
    # 케이스 2: flags가 JSON 문자열인 경우
    flags_str = json.dumps({
        'trading_strategy': '스윙',
        'label': '강한 매수'
    })
    flags_dict = json.loads(flags_str)
    strategy = None
    if not strategy and flags_dict and isinstance(flags_dict, dict):
        strategy = flags_dict.get('trading_strategy')
    assert strategy == '스윙'
    
    # 케이스 3: flags에 trading_strategy가 없는 경우
    flags_dict = {
        'label': '관심 종목',
        'target_profit': None
    }
    strategy = None
    if not strategy and flags_dict and isinstance(flags_dict, dict):
        strategy = flags_dict.get('trading_strategy')
    assert strategy is None
    
    # 케이스 4: flags가 빈 딕셔너리인 경우
    flags_dict = {}
    strategy = None
    if not strategy and flags_dict and isinstance(flags_dict, dict):
        strategy = flags_dict.get('trading_strategy')
    assert strategy is None


def test_strategy_in_api_response():
    """API 응답에 strategy가 올바르게 포함되는지 테스트"""
    # 시뮬레이션: DB에서 가져온 데이터
    data = {
        "code": "206650",
        "name": "유바이오로직스",
        "score": 9.0,
        "strategy": None,  # DB 컬럼에 없음
        "flags": json.dumps({
            "trading_strategy": "포지션",
            "label": "매수 후보",
            "target_profit": 0.1
        })
    }
    
    # 백엔드 로직 시뮬레이션
    strategy = data.get("strategy")
    flags_dict = json.loads(data.get("flags")) if isinstance(data.get("flags"), str) else {}
    
    if not strategy and flags_dict and isinstance(flags_dict, dict):
        strategy = flags_dict.get('trading_strategy')
    
    # 최종 item 생성
    item = {
        "ticker": data.get("code"),
        "name": data.get("name"),
        "score": data.get("score"),
        "strategy": strategy,
        "flags": flags_dict
    }
    
    assert item["strategy"] == "포지션"
    assert item["flags"]["trading_strategy"] == "포지션"


def test_strategy_fallback_to_observation():
    """strategy가 없을 때 기본값 처리 테스트"""
    # 케이스 1: strategy와 flags.trading_strategy 모두 없는 경우
    data = {
        "code": "123456",
        "strategy": None,
        "flags": json.dumps({
            "label": "관심 종목"
        })
    }
    
    strategy = data.get("strategy")
    flags_dict = json.loads(data.get("flags")) if isinstance(data.get("flags"), str) else {}
    
    if not strategy and flags_dict and isinstance(flags_dict, dict):
        strategy = flags_dict.get('trading_strategy')
    
    # 프론트엔드 로직 시뮬레이션
    normalizedStrategy = strategy or '관찰'
    
    assert normalizedStrategy == '관찰'


def test_frontend_strategy_normalization():
    """프론트엔드 전략 정규화 로직 테스트"""
    # 케이스 1: item.strategy가 있는 경우
    item = {
        "strategy": "스윙",
        "flags": {}
    }
    strategyFromFlags = item.get("flags", {}).get("trading_strategy") or None
    normalizedStrategy = item.get("strategy") or strategyFromFlags or '관찰'
    assert normalizedStrategy == "스윙"
    
    # 케이스 2: item.strategy가 없고 flags.trading_strategy가 있는 경우
    item = {
        "strategy": None,
        "flags": {
            "trading_strategy": "포지션"
        }
    }
    strategyFromFlags = item.get("flags", {}).get("trading_strategy") or None
    normalizedStrategy = item.get("strategy") or strategyFromFlags or '관찰'
    assert normalizedStrategy == "포지션"
    
    # 케이스 3: 둘 다 없는 경우
    item = {
        "strategy": None,
        "flags": {}
    }
    strategyFromFlags = item.get("flags", {}).get("trading_strategy") or None
    normalizedStrategy = item.get("strategy") or strategyFromFlags or '관찰'
    assert normalizedStrategy == "관찰"
    
    # 케이스 4: strategy가 빈 문자열인 경우
    item = {
        "strategy": "",
        "flags": {
            "trading_strategy": "장기"
        }
    }
    strategyFromFlags = item.get("flags", {}).get("trading_strategy") or None
    normalizedStrategy = item.get("strategy") or strategyFromFlags or '관찰'
    # 빈 문자열은 falsy이므로 strategyFromFlags 사용
    assert normalizedStrategy == "장기"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])





































"""
전략 표시 디버깅 테스트
실제 데이터 구조와 값 확인
"""
import json


def debug_strategy_extraction():
    """실제 데이터 구조로 전략 추출 디버깅"""
    
    # 실제 API 응답 구조 시뮬레이션
    test_cases = [
        {
            "name": "케이스 1: flags에 trading_strategy가 있는 경우",
            "data": {
                "code": "206650",
                "strategy": None,
                "flags": json.dumps({
                    "trading_strategy": "포지션",
                    "label": "매수 후보"
                })
            },
            "expected": "포지션"
        },
        {
            "name": "케이스 2: strategy가 빈 문자열인 경우",
            "data": {
                "code": "206650",
                "strategy": "",
                "flags": json.dumps({
                    "trading_strategy": "스윙"
                })
            },
            "expected": "스윙"
        },
        {
            "name": "케이스 3: 둘 다 없는 경우",
            "data": {
                "code": "206650",
                "strategy": None,
                "flags": json.dumps({})
            },
            "expected": None
        },
        {
            "name": "케이스 4: flags가 None인 경우",
            "data": {
                "code": "206650",
                "strategy": None,
                "flags": None
            },
            "expected": None
        }
    ]
    
    for case in test_cases:
        print(f"\n{case['name']}")
        print(f"입력: strategy={case['data']['strategy']}, flags={case['data']['flags']}")
        
        # 백엔드 로직
        data = case['data']
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
        
        print(f"결과: strategy={strategy}")
        print(f"기대값: {case['expected']}")
        print(f"일치: {strategy == case['expected']}")
        
        # 프론트엔드 로직 시뮬레이션
        item = {
            "strategy": strategy,
            "flags": flags_dict
        }
        
        strategy_from_flags = item.get("flags", {}).get("trading_strategy") or None
        normalized_strategy = (item.get("strategy") and item.get("strategy").strip()) or \
                             (strategy_from_flags and strategy_from_flags.strip()) or '관찰'
        
        print(f"프론트엔드 정규화 결과: {normalized_strategy}")


if __name__ == '__main__':
    debug_strategy_extraction()





































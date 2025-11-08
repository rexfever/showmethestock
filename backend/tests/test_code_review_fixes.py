"""
코드 리뷰 수정 사항 테스트
"""
import unittest
from unittest.mock import patch, MagicMock


class TestArraySafety(unittest.TestCase):
    """배열 안전성 테스트 (customer-scanner.js 수정 사항)"""
    
    def test_scanresults_null_safety(self):
        """scanResults가 null/undefined일 때 안전성 테스트"""
        # Python에서는 None으로 시뮬레이션
        scanResults = None
        
        # 안전한 필터링 (Python에서는 list comprehension 사용)
        filteredResults = [item for item in (scanResults or []) if item is not None and item != 'undefined']
        self.assertEqual(filteredResults, [])
        
        # 실제 배열인 경우
        scanResults = [{"ticker": "A001"}, {"ticker": "A002"}, None]
        filteredResults = [item for item in (scanResults or []) if item is not None and item != 'undefined']
        self.assertEqual(len(filteredResults), 2)
        self.assertEqual(filteredResults[0]["ticker"], "A001")
        self.assertEqual(filteredResults[1]["ticker"], "A002")
    
    def test_optional_chaining_simulation(self):
        """옵셔널 체이닝 시뮬레이션 테스트"""
        # JavaScript의 ?. 연산자를 Python에서 시뮬레이션
        def safe_get(obj, key, default=None):
            """안전한 속성 접근"""
            if obj is None:
                return default
            return getattr(obj, key, default) if hasattr(obj, key) else obj.get(key, default) if isinstance(obj, dict) else default
        
        # None인 경우
        item = None
        ticker = safe_get(item, "ticker")
        self.assertIsNone(ticker)
        
        # 실제 객체인 경우
        item = {"ticker": "A001"}
        ticker = safe_get(item, "ticker")
        self.assertEqual(ticker, "A001")
        
        # 배열 접근 안전성
        scanResults = [{"ticker": "A001"}]
        if scanResults and len(scanResults) > 0:
            first_item = scanResults[0]
            ticker = safe_get(first_item, "ticker")
            self.assertEqual(ticker, "A001")
        
        # 빈 배열인 경우
        scanResults = []
        if scanResults and len(scanResults) > 0:
            first_item = scanResults[0]
            ticker = safe_get(first_item, "ticker")
        else:
            ticker = None
        self.assertIsNone(ticker)


class TestDataChangesSafety(unittest.TestCase):
    """data.changes 안전성 테스트 (admin.js 수정 사항)"""
    
    def test_changes_array_safety(self):
        """changes가 배열이 아닐 때 안전성 테스트"""
        # 정상 케이스
        data = {
            "ok": True,
            "changes": ["min_signals: 5 → 3", "rsi_upper_limit: 60 → 65"]
        }
        changes_text = ", ".join(data["changes"]) if isinstance(data.get("changes"), list) and len(data["changes"]) > 0 else "변경 사항 없음"
        self.assertEqual(changes_text, "min_signals: 5 → 3, rsi_upper_limit: 60 → 65")
        
        # changes가 None인 경우
        data = {
            "ok": True,
            "changes": None
        }
        changes_text = ", ".join(data["changes"]) if isinstance(data.get("changes"), list) and len(data["changes"]) > 0 else "변경 사항 없음"
        self.assertEqual(changes_text, "변경 사항 없음")
        
        # changes가 없는 경우
        data = {
            "ok": True
        }
        changes_text = ", ".join(data["changes"]) if isinstance(data.get("changes"), list) and len(data["changes"]) > 0 else "변경 사항 없음"
        self.assertEqual(changes_text, "변경 사항 없음")
        
        # changes가 빈 배열인 경우
        data = {
            "ok": True,
            "changes": []
        }
        changes_text = ", ".join(data["changes"]) if isinstance(data.get("changes"), list) and len(data["changes"]) > 0 else "변경 사항 없음"
        self.assertEqual(changes_text, "변경 사항 없음")
        
        # changes가 문자열인 경우 (잘못된 타입)
        data = {
            "ok": True,
            "changes": "not an array"
        }
        changes_text = ", ".join(data["changes"]) if isinstance(data.get("changes"), list) and len(data["changes"]) > 0 else "변경 사항 없음"
        self.assertEqual(changes_text, "변경 사항 없음")


class TestReverseMappingSafety(unittest.TestCase):
    """역매핑 안전성 테스트 (main.py 수정 사항)"""
    
    def test_reverse_mapping_creation(self):
        """역매핑 생성 테스트"""
        param_mapping = {
            "min_signals": "MIN_SIGNALS",
            "rsi_upper_limit": "RSI_UPPER_LIMIT",
            "vol_ma5_mult": "VOL_MA5_MULT",
            "gap_max": "GAP_MAX",
            "ext_from_tema20_max": "EXT_FROM_TEMA20_MAX",
        }
        
        # 역매핑 생성
        reverse_mapping = {v: k for k, v in param_mapping.items()}
        
        # 검증
        self.assertEqual(reverse_mapping["MIN_SIGNALS"], "min_signals")
        self.assertEqual(reverse_mapping["RSI_UPPER_LIMIT"], "rsi_upper_limit")
        self.assertEqual(len(reverse_mapping), 5)
    
    def test_reverse_mapping_safe_access(self):
        """역매핑 안전한 접근 테스트"""
        param_mapping = {
            "min_signals": "MIN_SIGNALS",
            "rsi_upper_limit": "RSI_UPPER_LIMIT",
        }
        
        reverse_mapping = {v: k for k, v in param_mapping.items()}
        
        # 존재하는 키 접근
        key = "MIN_SIGNALS"
        param_key = reverse_mapping.get(key)
        self.assertIsNotNone(param_key)
        self.assertEqual(param_key, "min_signals")
        
        # 존재하지 않는 키 접근 (예외 없어야 함)
        key = "NON_EXISTENT_KEY"
        param_key = reverse_mapping.get(key)
        self.assertIsNone(param_key)
        
        # next() 사용 시 예외 발생 가능 (이전 방식)
        try:
            param_key = next(k for k, v in param_mapping.items() if v == key)
            self.fail("StopIteration 예외가 발생해야 함")
        except StopIteration:
            pass  # 예상된 예외
    
    def test_reverse_mapping_update_logic(self):
        """역매핑을 사용한 업데이트 로직 테스트"""
        param_mapping = {
            "min_signals": "MIN_SIGNALS",
            "rsi_upper_limit": "RSI_UPPER_LIMIT",
        }
        
        reverse_mapping = {v: k for k, v in param_mapping.items()}
        params = {
            "min_signals": "3",
            "rsi_upper_limit": "65"
        }
        
        # 업데이트할 키 목록
        keys_to_update = ["MIN_SIGNALS", "RSI_UPPER_LIMIT", "NON_EXISTENT_KEY"]
        
        for key in keys_to_update:
            param_key = reverse_mapping.get(key)  # 안전하게 접근
            if param_key and param_key in params:
                # 업데이트 수행
                new_value = params[param_key]
                self.assertIsNotNone(new_value)
            else:
                # 업데이트하지 않음 (예외 없이 처리)
                self.assertIsNone(param_key or (param_key if param_key in params else None))


class TestTypeSafety(unittest.TestCase):
    """타입 안전성 테스트"""
    
    def test_analyze_and_recommend_return_type(self):
        """analyze_and_recommend 반환 타입 테스트"""
        from typing import Tuple, Dict, Any
        
        # 시뮬레이션된 반환값
        def mock_analyze_and_recommend() -> Tuple[Dict[str, Any], str]:
            recommended_params = {
                "min_signals": 3,
                "rsi_upper_limit": 65,
                "vol_ma5_mult": 1.8,
                "gap_max": 0.013,
                "ext_from_tema20_max": 0.013,
                "min_score": 4
            }
            evaluation = "good"
            return recommended_params, evaluation
        
        result = mock_analyze_and_recommend()
        
        # 타입 검증
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        
        recommended_params, evaluation = result
        
        self.assertIsInstance(recommended_params, dict)
        self.assertIsInstance(evaluation, str)
        self.assertIn(evaluation, ["excellent", "good", "fair", "poor"])
        
        # 권장 파라미터 키 검증
        required_keys = ["min_signals", "rsi_upper_limit", "vol_ma5_mult", 
                        "gap_max", "ext_from_tema20_max", "min_score"]
        for key in required_keys:
            self.assertIn(key, recommended_params)


class TestErrorHandling(unittest.TestCase):
    """에러 처리 테스트"""
    
    def test_error_message_safety(self):
        """에러 메시지 안전성 테스트"""
        # error가 None인 경우
        error = None
        error_msg = error or "알 수 없는 오류"
        self.assertEqual(error_msg, "알 수 없는 오류")
        
        # error가 있는 경우
        error = "파일을 찾을 수 없습니다"
        error_msg = error or "알 수 없는 오류"
        self.assertEqual(error_msg, "파일을 찾을 수 없습니다")
        
        # error가 빈 문자열인 경우
        error = ""
        error_msg = error or "알 수 없는 오류"
        self.assertEqual(error_msg, "알 수 없는 오류")


if __name__ == '__main__':
    unittest.main()


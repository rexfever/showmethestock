"""
사용자 친화적 분석 기능 단위 테스트
"""
import unittest
from unittest.mock import Mock, MagicMock
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from user_friendly_analysis import (
    get_user_friendly_analysis,
    get_overall_assessment,
    get_detailed_explanations,
    get_investment_advice,
    get_warnings,
    get_simple_indicators
)


class TestUserFriendlyAnalysis(unittest.TestCase):
    """사용자 친화적 분석 기능 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        # Mock 분석 결과 생성
        self.mock_item = Mock()
        self.mock_item.ticker = "005930"
        self.mock_item.name = "삼성전자"
        self.mock_item.score = 7.5
        self.mock_item.match = True
        self.mock_item.strategy = "상승시작 / 상승추세정착"
        
        # Mock 지표 데이터 - 직접 속성 설정
        self.mock_indicators = Mock()
        self.mock_indicators.TEMA20 = 100000.0
        self.mock_indicators.DEMA10 = 95000.0
        self.mock_indicators.MACD_OSC = 500.0
        self.mock_indicators.RSI_TEMA = 65.0
        self.mock_indicators.RSI_DEMA = 60.0
        self.mock_indicators.OBV = 1000000.0
        self.mock_indicators.VOL = 5000000
        self.mock_indicators.VOL_MA5 = 3000000.0
        self.mock_indicators.close = 100000.0
        
        # Mock 플래그 데이터 - 직접 속성 설정
        self.mock_flags = Mock()
        self.mock_flags.cross = True
        self.mock_flags.vol_expand = True
        self.mock_flags.macd_ok = True
        self.mock_flags.rsi_dema_setup = True
        self.mock_flags.rsi_tema_trigger = False
        self.mock_flags.rsi_dema_value = 60.0
        self.mock_flags.rsi_tema_value = 65.0
        self.mock_flags.overheated_rsi_tema = False
        self.mock_flags.tema_slope_ok = True
        self.mock_flags.obv_slope_ok = True
        self.mock_flags.above_cnt5_ok = True
        self.mock_flags.dema_slope_ok = True
        self.mock_flags.label = '우수'
        
        self.mock_item.indicators = self.mock_indicators
        self.mock_item.flags = self.mock_flags
        
        # Mock 분석 결과
        self.mock_analysis_result = Mock()
        self.mock_analysis_result.ok = True
        self.mock_analysis_result.item = self.mock_item
    
    def test_get_user_friendly_analysis_success(self):
        """정상적인 분석 결과 테스트"""
        result = get_user_friendly_analysis(self.mock_analysis_result)
        
        # 기본 구조 검증
        self.assertIn('summary', result)
        self.assertIn('recommendation', result)
        self.assertIn('confidence', result)
        self.assertIn('explanations', result)
        self.assertIn('investment_advice', result)
        self.assertIn('warnings', result)
        self.assertIn('simple_indicators', result)
        
        # 내용 검증
        self.assertEqual(result['summary'], "좋은 투자 기회")
        self.assertEqual(result['recommendation'], "추천")
        self.assertEqual(result['confidence'], "보통")
        self.assertIsInstance(result['explanations'], list)
        self.assertIsInstance(result['investment_advice'], list)
        self.assertIsInstance(result['warnings'], list)

    def test_get_user_friendly_analysis_failure(self):
        """분석 실패 케이스 테스트"""
        # 실패한 분석 결과
        failed_result = Mock()
        failed_result.ok = False
        failed_result.item = None
        
        result = get_user_friendly_analysis(failed_result)
        
        self.assertEqual(result['summary'], '분석할 수 없습니다.')
        self.assertEqual(result['recommendation'], '분석 실패')
        self.assertEqual(result['confidence'], '낮음')
    
    def test_get_user_friendly_analysis_none_input(self):
        """None 입력 테스트"""
        result = get_user_friendly_analysis(None)
        
        self.assertEqual(result['summary'], '분석할 수 없습니다.')
        self.assertEqual(result['recommendation'], '분석 실패')

    def test_get_overall_assessment_high_score(self):
        """높은 점수 평가 테스트"""
        summary, recommendation, confidence = get_overall_assessment(8.5, True, {})
        
        self.assertEqual(summary, "매우 좋은 투자 기회")
        self.assertEqual(recommendation, "강력 추천")
        self.assertEqual(confidence, "높음")

    def test_get_overall_assessment_low_score(self):
        """낮은 점수 평가 테스트"""
        summary, recommendation, confidence = get_overall_assessment(1.0, False, {})
        
        self.assertEqual(summary, "현재 투자 조건 미충족")
        self.assertEqual(recommendation, "관심")
        self.assertEqual(confidence, "매우 낮음")

    def test_get_overall_assessment_no_match(self):
        """매칭되지 않은 경우 테스트"""
        flags = {'label': '유동성부족'}
        summary, recommendation, confidence = get_overall_assessment(5.0, False, flags)
        
        self.assertEqual(summary, "거래량이 너무 적어 투자 부적합")
        self.assertEqual(recommendation, "비추천")

    def test_get_detailed_explanations_with_signals(self):
        """신호가 있는 경우 설명 테스트"""
        indicators = {
            'RSI_TEMA': 75.0,
            'VOL': 10000000,
            'VOL_MA5': 2000000.0
        }
        flags = {
            'cross': True,
            'vol_expand': True,
            'macd_ok': True
        }
        
        explanations = get_detailed_explanations(indicators, flags, 7.0)
        
        # 설명이 생성되었는지 확인
        self.assertIsInstance(explanations, list)
        self.assertGreater(len(explanations), 0)
        
        # 골든크로스 설명 확인
        cross_explanation = next((exp for exp in explanations if '상승 신호' in exp['title']), None)
        self.assertIsNotNone(cross_explanation)
        self.assertEqual(cross_explanation['impact'], '긍정적')

    def test_get_detailed_explanations_rsi_overbought(self):
        """RSI 과매수 상태 설명 테스트"""
        indicators = {'RSI_TEMA': 75.0}
        flags = {}
        
        explanations = get_detailed_explanations(indicators, flags, 5.0)
        
        # 과매수 설명 확인
        rsi_explanation = next((exp for exp in explanations if '과매수' in exp['title']), None)
        self.assertIsNotNone(rsi_explanation)
        self.assertEqual(rsi_explanation['impact'], '부정적')

    def test_get_detailed_explanations_rsi_oversold(self):
        """RSI 과매도 상태 설명 테스트"""
        indicators = {'RSI_TEMA': 25.0}
        flags = {}
        
        explanations = get_detailed_explanations(indicators, flags, 5.0)
        
        # 과매도 설명 확인
        rsi_explanation = next((exp for exp in explanations if '과매도' in exp['title']), None)
        self.assertIsNotNone(rsi_explanation)
        self.assertEqual(rsi_explanation['impact'], '긍정적')

    def test_get_investment_advice_high_score(self):
        """높은 점수 투자 조언 테스트"""
        indicators = {'RSI_TEMA': 65.0, 'VOL': 5000000, 'VOL_MA5': 2000000.0}
        flags = {'label': '우수'}
        
        advice = get_investment_advice(8.0, True, indicators, flags)
        
        self.assertIsInstance(advice, list)
            self.assertGreater(len(advice), 0)
        self.assertTrue(any('강력한 매수 신호' in a for a in advice))

    def test_get_investment_advice_low_score(self):
        """낮은 점수 투자 조언 테스트"""
        indicators = {'RSI_TEMA': 30.0}
        flags = {}
        
        advice = get_investment_advice(1.0, False, indicators, flags)
        
        self.assertIsInstance(advice, list)
        self.assertTrue(any('투자하지 않는 것이 좋습니다' in a for a in advice))

    def test_get_warnings_basic(self):
        """기본 주의사항 테스트"""
        indicators = {'RSI_TEMA': 50.0, 'VOL': 1000000, 'VOL_MA5': 1000000.0}
        flags = {}
        
        warnings = get_warnings(indicators, flags)
        
        self.assertIsInstance(warnings, list)
        self.assertGreater(len(warnings), 0)
        self.assertTrue(any('원금 손실 위험' in w for w in warnings))

    def test_get_warnings_rsi_extreme(self):
        """RSI 극값 경고 테스트"""
        # 매우 높은 RSI
        indicators_high = {'RSI_TEMA': 85.0, 'VOL': 1000000, 'VOL_MA5': 1000000.0}
        flags = {}
        
        warnings_high = get_warnings(indicators_high, flags)
        self.assertTrue(any('RSI가 매우 높아' in w for w in warnings_high))
        
        # 매우 낮은 RSI
        indicators_low = {'RSI_TEMA': 15.0, 'VOL': 1000000, 'VOL_MA5': 1000000.0}
        warnings_low = get_warnings(indicators_low, flags)
        self.assertTrue(any('RSI가 매우 낮아' in w for w in warnings_low))

    def test_get_warnings_volume_spike(self):
        """거래량 급증 경고 테스트"""
        indicators = {'RSI_TEMA': 50.0, 'VOL': 15000000, 'VOL_MA5': 2000000.0}  # 7.5배로 수정
        flags = {}
        
        warnings = get_warnings(indicators, flags)
        self.assertTrue(any('거래량이 급증했으니 변동성이 클 수 있습니다' in w for w in warnings))

    def test_get_simple_indicators(self):
        """간단한 지표 설명 테스트"""
        indicators = {
            'close': 100000.0,
            'VOL': 5000000,
            'RSI_TEMA': 65.0,
            'TEMA': 100000.0,
            'DEMA': 95000.0
        }
        
        simple_indicators = get_simple_indicators(indicators)
        
        self.assertIn('current_price', simple_indicators)
        self.assertIn('volume', simple_indicators)
        self.assertIn('rsi', simple_indicators)
        self.assertIn('trend', simple_indicators)
        
        # 값 검증
        self.assertEqual(simple_indicators['current_price']['value'], '100,000원')
        self.assertEqual(simple_indicators['volume']['value'], '5,000,000주')
        self.assertEqual(simple_indicators['rsi']['value'], '65.0')
        self.assertEqual(simple_indicators['trend']['value'], '상승')

    def test_get_simple_indicators_downtrend(self):
        """하락 추세 지표 테스트"""
        indicators = {
            'close': 100000.0,
            'VOL': 5000000,
            'RSI_TEMA': 35.0,
            'TEMA': 95000.0,
            'DEMA': 100000.0
        }
        
        simple_indicators = get_simple_indicators(indicators)
        self.assertEqual(simple_indicators['trend']['value'], '하락')


if __name__ == '__main__':
    unittest.main()
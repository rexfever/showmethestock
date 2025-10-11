"""
사용자 친화적 분석 테스트
"""
import unittest
import sys
import os
from unittest.mock import MagicMock

# 상위 디렉토리의 모듈 import
sys.path.append('..')
from user_friendly_analysis import get_user_friendly_analysis
from models import AnalyzeResponse, AnalyzeItem, IndicatorPayload, TrendPayload, ScoreFlags

class TestUserFriendlyAnalysis(unittest.TestCase):
    """사용자 친화적 분석 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        # 샘플 분석 결과 생성
        self.sample_indicators = IndicatorPayload(
            TEMA=100.5,
            DEMA=99.8,
            MACD_OSC=1.2,
            MACD_LINE=0.8,
            MACD_SIGNAL=0.6,
            RSI_TEMA=65.0,
            RSI_DEMA=62.0,
            OBV=1500000,
            VOL=2000000,
            VOL_MA5=1800000,
            close=100.0
        )
        
        self.sample_trend = TrendPayload(
            TEMA20_SLOPE20=0.5,
            OBV_SLOPE20=0.3,
            ABOVE_CNT5=3,
            DEMA10_SLOPE20=0.4
        )
        
        self.sample_flags = ScoreFlags(
            tema_dema_golden_cross=True,
            macd_osc_positive=True,
            rsi_tema_above_threshold=True,
            volume_surge=True,
            price_uptrend=True,
            obv_uptrend=True,
            consecutive_up_days=True,
            rsi_momentum=True
        )
        
        self.sample_item = AnalyzeItem(
            ticker="005930",
            name="삼성전자",
            indicators=self.sample_indicators,
            trend=self.sample_trend,
            flags=self.sample_flags,
            score=15,
            match=True
        )
        
        self.sample_response = AnalyzeResponse(
            ok=True,
            item=self.sample_item,
            error=None
        )
    
    def test_get_user_friendly_analysis_success(self):
        """성공적인 분석 결과 테스트"""
        result = get_user_friendly_analysis(self.sample_response)
        
        # 기본 구조 검증
        self.assertIsInstance(result, dict)
        self.assertIn('summary', result)
        self.assertIn('recommendation', result)
        self.assertIn('confidence', result)
        self.assertIn('explanations', result)
        self.assertIn('investment_advice', result)
        self.assertIn('warnings', result)
        self.assertIn('simple_indicators', result)
        
        # 추천 레벨 검증 (모든 조건이 True이므로 강력 추천이어야 함)
        self.assertEqual(result['recommendation'], '강력 추천')
        self.assertEqual(result['confidence'], '높음')
    
    def test_get_user_friendly_analysis_failed_response(self):
        """실패한 분석 결과 테스트"""
        failed_response = AnalyzeResponse(
            ok=False,
            item=None,
            error="분석 실패"
        )
        
        result = get_user_friendly_analysis(failed_response)
        
        # 실패 시 기본값 반환 검증
        self.assertEqual(result['summary'], '분석할 수 없습니다.')
        self.assertEqual(result['recommendation'], '분석 실패')
        self.assertEqual(result['confidence'], '낮음')
    
    def test_get_user_friendly_analysis_none_response(self):
        """None 응답 테스트"""
        result = get_user_friendly_analysis(None)
        
        # None 응답 시 기본값 반환 검증
        self.assertEqual(result['summary'], '분석할 수 없습니다.')
        self.assertEqual(result['recommendation'], '분석 실패')
        self.assertEqual(result['confidence'], '낮음')
    
    def test_recommendation_levels(self):
        """추천 레벨별 테스트"""
        # 강력 추천 (15점)
        strong_item = self.sample_item.copy()
        strong_item.score = 15
        strong_response = AnalyzeResponse(ok=True, item=strong_item, error=None)
        
        result = get_user_friendly_analysis(strong_response)
        self.assertEqual(result['recommendation'], '강력 추천')
        
        # 추천 (10점)
        recommend_item = self.sample_item.copy()
        recommend_item.score = 10
        recommend_response = AnalyzeResponse(ok=True, item=recommend_item, error=None)
        
        result = get_user_friendly_analysis(recommend_response)
        self.assertEqual(result['recommendation'], '추천')
        
        # 관심 (7점)
        interest_item = self.sample_item.copy()
        interest_item.score = 7
        interest_response = AnalyzeResponse(ok=True, item=interest_item, error=None)
        
        result = get_user_friendly_analysis(interest_response)
        self.assertEqual(result['recommendation'], '관심')
        
        # 신중 (4점)
        caution_item = self.sample_item.copy()
        caution_item.score = 4
        caution_response = AnalyzeResponse(ok=True, item=caution_item, error=None)
        
        result = get_user_friendly_analysis(caution_response)
        self.assertEqual(result['recommendation'], '신중')
        
        # 비추천 (1점)
        avoid_item = self.sample_item.copy()
        avoid_item.score = 1
        avoid_response = AnalyzeResponse(ok=True, item=avoid_item, error=None)
        
        result = get_user_friendly_analysis(avoid_response)
        self.assertEqual(result['recommendation'], '비추천')
    
    def test_explanations_structure(self):
        """설명 구조 테스트"""
        result = get_user_friendly_analysis(self.sample_response)
        
        # explanations가 리스트인지 확인
        self.assertIsInstance(result['explanations'], list)
        
        # 각 설명이 올바른 구조를 가지는지 확인
        for explanation in result['explanations']:
            self.assertIn('title', explanation)
            self.assertIn('description', explanation)
            self.assertIn('impact', explanation)
            self.assertIn(explanation['impact'], ['긍정적', '부정적', '중립'])
    
    def test_investment_advice_structure(self):
        """투자 조언 구조 테스트"""
        result = get_user_friendly_analysis(self.sample_response)
        
        # investment_advice가 리스트인지 확인
        self.assertIsInstance(result['investment_advice'], list)
        
        # 각 조언이 문자열인지 확인
        for advice in result['investment_advice']:
            self.assertIsInstance(advice, str)
            self.assertGreater(len(advice), 0)
    
    def test_warnings_structure(self):
        """주의사항 구조 테스트"""
        result = get_user_friendly_analysis(self.sample_response)
        
        # warnings가 리스트인지 확인
        self.assertIsInstance(result['warnings'], list)
        
        # 각 경고가 문자열인지 확인
        for warning in result['warnings']:
            self.assertIsInstance(warning, str)
            self.assertGreater(len(warning), 0)
    
    def test_simple_indicators_structure(self):
        """간단한 지표 구조 테스트"""
        result = get_user_friendly_analysis(self.sample_response)
        
        # simple_indicators가 딕셔너리인지 확인
        self.assertIsInstance(result['simple_indicators'], dict)
        
        # 필수 지표들이 있는지 확인
        required_indicators = ['current_price', 'volume', 'rsi', 'macd']
        for indicator in required_indicators:
            self.assertIn(indicator, result['simple_indicators'])
            
            # 각 지표가 올바른 구조를 가지는지 확인
            indicator_data = result['simple_indicators'][indicator]
            self.assertIn('value', indicator_data)
            self.assertIn('description', indicator_data)
    
    def test_negative_flags_handling(self):
        """부정적인 플래그 처리 테스트"""
        # 부정적인 플래그들
        negative_flags = ScoreFlags(
            tema_dema_golden_cross=False,
            macd_osc_positive=False,
            rsi_tema_above_threshold=False,
            volume_surge=False,
            price_uptrend=False,
            obv_uptrend=False,
            consecutive_up_days=False,
            rsi_momentum=False
        )
        
        negative_item = self.sample_item.copy()
        negative_item.flags = negative_flags
        negative_item.score = 0
        
        negative_response = AnalyzeResponse(ok=True, item=negative_item, error=None)
        
        result = get_user_friendly_analysis(negative_response)
        
        # 부정적인 결과 검증
        self.assertEqual(result['recommendation'], '비추천')
        self.assertEqual(result['confidence'], '낮음')
        
        # 부정적인 설명들이 있는지 확인
        negative_explanations = [exp for exp in result['explanations'] if exp['impact'] == '부정적']
        self.assertGreater(len(negative_explanations), 0)
    
    def test_mixed_flags_handling(self):
        """혼합된 플래그 처리 테스트"""
        # 일부만 True인 플래그들
        mixed_flags = ScoreFlags(
            tema_dema_golden_cross=True,
            macd_osc_positive=True,
            rsi_tema_above_threshold=False,
            volume_surge=False,
            price_uptrend=True,
            obv_uptrend=False,
            consecutive_up_days=False,
            rsi_momentum=True
        )
        
        mixed_item = self.sample_item.copy()
        mixed_item.flags = mixed_flags
        mixed_item.score = 4
        
        mixed_response = AnalyzeResponse(ok=True, item=mixed_item, error=None)
        
        result = get_user_friendly_analysis(mixed_response)
        
        # 혼합된 결과 검증
        self.assertEqual(result['recommendation'], '신중')
        
        # 긍정적과 부정적 설명이 모두 있는지 확인
        positive_explanations = [exp for exp in result['explanations'] if exp['impact'] == '긍정적']
        negative_explanations = [exp for exp in result['explanations'] if exp['impact'] == '부정적']
        
        self.assertGreater(len(positive_explanations), 0)
        self.assertGreater(len(negative_explanations), 0)

if __name__ == '__main__':
    unittest.main()

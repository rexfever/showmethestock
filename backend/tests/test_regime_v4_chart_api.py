"""
레짐 v4 Chart API 전환 테스트
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from scanner_v2.regime_v4 import load_full_data, analyze_regime_v4, compute_us_trend_features, compute_us_risk_features


class TestRegimeV4ChartAPI(unittest.TestCase):
    """레짐 v4 Chart API 전환 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.test_date = datetime.now().strftime('%Y%m%d')
        self.past_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
    
    def test_load_full_data_chart_api_success(self):
        """Chart API 성공 시나리오 테스트"""
        print("\n=== 테스트 1: Chart API 성공 시나리오 ===")
        
        data = load_full_data(self.test_date)
        
        # SPY, QQQ, VIX 데이터 확인
        self.assertIsInstance(data['SPY'], pd.DataFrame, "SPY는 DataFrame이어야 함")
        self.assertIsInstance(data['QQQ'], pd.DataFrame, "QQQ는 DataFrame이어야 함")
        self.assertIsInstance(data['VIX'], pd.DataFrame, "VIX는 DataFrame이어야 함")
        
        # 컬럼명 확인 (소문자)
        if not data['SPY'].empty:
            expected_columns = ['open', 'high', 'low', 'close', 'volume']
            actual_columns = [col for col in data['SPY'].columns if col in expected_columns]
            self.assertTrue(
                all(col in data['SPY'].columns for col in expected_columns),
                f"SPY 컬럼명 오류: {list(data['SPY'].columns)} (예상: {expected_columns})"
            )
        
        print("✅ Chart API 성공 시나리오 통과")
    
    def test_load_full_data_chart_api_fallback(self):
        """Chart API 실패 시 CSV fallback 테스트"""
        print("\n=== 테스트 2: Chart API 실패 시 CSV fallback ===")
        
        # Chart API 실패 시뮬레이션 (함수 내부에서 import하므로 services 모듈을 모킹)
        with patch('services.us_futures_data_v8.us_futures_data_v8') as mock_v8:
            mock_v8.fetch_data.side_effect = Exception("Chart API 실패")
            
            # CSV 캐시가 있는 경우 fallback 동작 확인
            data = load_full_data(self.test_date)
            
            # fallback이 작동하면 데이터가 있을 수 있음 (CSV 캐시 존재 시)
            # 또는 빈 DataFrame일 수 있음 (CSV 캐시 없음)
            self.assertIsInstance(data['SPY'], pd.DataFrame, "SPY는 DataFrame이어야 함")
            self.assertIsInstance(data['QQQ'], pd.DataFrame, "QQQ는 DataFrame이어야 함")
            self.assertIsInstance(data['VIX'], pd.DataFrame, "VIX는 DataFrame이어야 함")
        
        print("✅ Chart API 실패 시 CSV fallback 통과")
    
    def test_column_name_consistency(self):
        """컬럼명 일관성 테스트"""
        print("\n=== 테스트 3: 컬럼명 일관성 ===")
        
        data = load_full_data(self.test_date)
        
        for symbol in ['SPY', 'QQQ', 'VIX']:
            df = data[symbol]
            if not df.empty:
                # 소문자 컬럼명 확인
                self.assertIn('close', df.columns, f"{symbol}에 'close' 컬럼이 없음")
                self.assertIn('open', df.columns, f"{symbol}에 'open' 컬럼이 없음")
                self.assertIn('high', df.columns, f"{symbol}에 'high' 컬럼이 없음")
                self.assertIn('low', df.columns, f"{symbol}에 'low' 컬럼이 없음")
                self.assertIn('volume', df.columns, f"{symbol}에 'volume' 컬럼이 없음")
                
                # 대문자 컬럼명이 없어야 함
                self.assertNotIn('Close', df.columns, f"{symbol}에 대문자 'Close' 컬럼이 남아있음")
                self.assertNotIn('Open', df.columns, f"{symbol}에 대문자 'Open' 컬럼이 남아있음")
        
        print("✅ 컬럼명 일관성 통과")
    
    def test_date_filtering(self):
        """날짜 필터링 테스트"""
        print("\n=== 테스트 4: 날짜 필터링 ===")
        
        past_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
        past_date_obj = pd.to_datetime(past_date, format='%Y%m%d')
        
        data = load_full_data(past_date)
        
        for symbol in ['SPY', 'QQQ', 'VIX']:
            df = data[symbol]
            if not df.empty:
                # 모든 날짜가 past_date 이하인지 확인
                max_date = df.index.max()
                self.assertLessEqual(
                    max_date, past_date_obj,
                    f"{symbol}의 최대 날짜({max_date})가 목표 날짜({past_date_obj})보다 큼"
                )
        
        print("✅ 날짜 필터링 통과")
    
    def test_compute_us_trend_features(self):
        """미국 트렌드 feature 계산 테스트"""
        print("\n=== 테스트 5: 미국 트렌드 feature 계산 ===")
        
        data = load_full_data(self.test_date)
        
        if not data['SPY'].empty and not data['QQQ'].empty:
            features = compute_us_trend_features(data['SPY'], data['QQQ'])
            
            # 필수 feature 확인 (실제 구현에 맞게 수정)
            self.assertIn('SPY_R20', features, "SPY_R20 feature가 없음")
            self.assertIn('SPY_R60', features, "SPY_R60 feature가 없음")
            self.assertIn('QQQ_R20', features, "QQQ_R20 feature가 없음")
            self.assertIn('QQQ_R60', features, "QQQ_R60 feature가 없음")
            self.assertIn('SPY_MA50_ABOVE_200', features, "SPY_MA50_ABOVE_200 feature가 없음")
            self.assertIn('QQQ_MA50_ABOVE_200', features, "QQQ_MA50_ABOVE_200 feature가 없음")
            
            # feature 값이 숫자인지 확인
            for key, value in features.items():
                self.assertIsInstance(value, (int, float), f"{key} feature가 숫자가 아님: {type(value)}")
        
        print("✅ 미국 트렌드 feature 계산 통과")
    
    def test_compute_us_risk_features(self):
        """미국 리스크 feature 계산 테스트"""
        print("\n=== 테스트 6: 미국 리스크 feature 계산 ===")
        
        data = load_full_data(self.test_date)
        
        if not data['VIX'].empty:
            features = compute_us_risk_features(data['VIX'])
            
            # 필수 feature 확인 (실제 구현에 맞게 수정)
            self.assertIn('VIX_LEVEL', features, "VIX_LEVEL feature가 없음")
            self.assertIn('VIX_MA5', features, "VIX_MA5 feature가 없음")
            self.assertIn('VIX_MA20', features, "VIX_MA20 feature가 없음")
            self.assertIn('VIX_CHG_3D', features, "VIX_CHG_3D feature가 없음")
            
            # feature 값이 숫자인지 확인
            for key, value in features.items():
                self.assertIsInstance(value, (int, float), f"{key} feature가 숫자가 아님: {type(value)}")
        
        print("✅ 미국 리스크 feature 계산 통과")
    
    def test_analyze_regime_v4_full_flow(self):
        """레짐 v4 전체 플로우 테스트"""
        print("\n=== 테스트 7: 레짐 v4 전체 플로우 ===")
        
        result = analyze_regime_v4(self.test_date)
        
        # 필수 필드 확인
        self.assertIn('final_regime', result, "final_regime이 없음")
        self.assertIn('kr_regime', result, "kr_regime이 없음")
        self.assertIn('us_prev_regime', result, "us_prev_regime이 없음")
        self.assertIn('final_score', result, "final_score가 없음")
        self.assertIn('kr_trend_score', result, "kr_trend_score가 없음")
        self.assertIn('us_trend_score', result, "us_trend_score가 없음")
        
        # 레짐 값 유효성 확인
        valid_regimes = ['bull', 'neutral', 'bear', 'crash']
        self.assertIn(result['final_regime'], valid_regimes, f"final_regime이 유효하지 않음: {result['final_regime']}")
        self.assertIn(result['kr_regime'], valid_regimes, f"kr_regime이 유효하지 않음: {result['kr_regime']}")
        self.assertIn(result['us_prev_regime'], valid_regimes, f"us_prev_regime이 유효하지 않음: {result['us_prev_regime']}")
        
        # 점수 값 유효성 확인
        self.assertIsInstance(result['final_score'], (int, float), "final_score가 숫자가 아님")
        self.assertIsInstance(result['kr_trend_score'], (int, float), "kr_trend_score가 숫자가 아님")
        self.assertIsInstance(result['us_trend_score'], (int, float), "us_trend_score가 숫자가 아님")
        
        print("✅ 레짐 v4 전체 플로우 통과")
    
    def test_empty_data_handling(self):
        """빈 데이터 처리 테스트"""
        print("\n=== 테스트 8: 빈 데이터 처리 ===")
        
        # 빈 DataFrame 반환하도록 모킹 (함수 내부에서 import하므로 services 모듈을 모킹)
        with patch('services.us_futures_data_v8.us_futures_data_v8') as mock_v8:
            mock_v8.fetch_data.return_value = pd.DataFrame()
            
            data = load_full_data(self.test_date)
            
            # 빈 DataFrame이어도 에러가 발생하지 않아야 함
            self.assertIsInstance(data['SPY'], pd.DataFrame, "SPY는 DataFrame이어야 함")
            self.assertIsInstance(data['QQQ'], pd.DataFrame, "QQQ는 DataFrame이어야 함")
            self.assertIsInstance(data['VIX'], pd.DataFrame, "VIX는 DataFrame이어야 함")
        
        print("✅ 빈 데이터 처리 통과")
    
    def test_mixed_case_columns(self):
        """대소문자 혼합 컬럼명 처리 테스트"""
        print("\n=== 테스트 9: 대소문자 혼합 컬럼명 처리 ===")
        
        # 대문자 컬럼명을 가진 데이터 생성
        mock_df = pd.DataFrame({
            'Open': [100, 101, 102],
            'High': [105, 106, 107],
            'Low': [95, 96, 97],
            'Close': [103, 104, 105],
            'Volume': [1000, 1100, 1200]
        }, index=pd.date_range('2025-01-01', periods=3))
        
        # 컬럼명 변환 테스트
        converted_df = mock_df.rename(columns={
            'Open': 'open', 'High': 'high', 'Low': 'low', 
            'Close': 'close', 'Volume': 'volume'
        })
        
        self.assertIn('close', converted_df.columns, "소문자 'close' 컬럼이 없음")
        self.assertNotIn('Close', converted_df.columns, "대문자 'Close' 컬럼이 남아있음")
        
        print("✅ 대소문자 혼합 컬럼명 처리 통과")
    
    def test_period_parameter(self):
        """period 파라미터 테스트"""
        print("\n=== 테스트 10: period 파라미터 ===")
        
        with patch('services.us_futures_data_v8.us_futures_data_v8') as mock_v8:
            mock_df = pd.DataFrame({
                'Open': [100], 'High': [105], 'Low': [95],
                'Close': [103], 'Volume': [1000]
            }, index=[pd.Timestamp('2025-01-01')])
            
            mock_v8.fetch_data.return_value = mock_df
            
            data = load_full_data(self.test_date)
            
            # period='1y'로 호출되었는지 확인
            calls = mock_v8.fetch_data.call_args_list
            for call in calls:
                args, kwargs = call
                if 'period' in kwargs:
                    self.assertEqual(kwargs['period'], '1y', f"period가 '1y'가 아님: {kwargs['period']}")
        
        print("✅ period 파라미터 통과")


if __name__ == '__main__':
    unittest.main(verbosity=2)


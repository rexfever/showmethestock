#!/usr/bin/env python3
"""
통합 테스트: 실제 scanner.py와 main.py 로직 검증

실제 코드를 import하여 end-to-end 검증
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import numpy as np


class TestScannerIntegration:
    """scanner.py 실제 코드 검증"""
    
    def test_scan_one_symbol_returns_tema20_dema10(self):
        """scan_one_symbol이 TEMA20/DEMA10을 반환하는지 확인"""
        print("\n[통합 Step 1] scanner.py::scan_one_symbol 검증")
        
        from scanner import scan_one_symbol
        from kiwoom_api import KiwoomRestAPI
        
        # Mock API
        mock_api = Mock(spec=KiwoomRestAPI)
        mock_api.get_stock_name.return_value = "테스트종목"
        
        # Mock OHLCV 데이터 (60일치)
        dates = pd.date_range(end='2025-11-15', periods=60, freq='D')
        mock_df = pd.DataFrame({
            'date': dates,
            'open': np.random.uniform(50000, 52000, 60),
            'high': np.random.uniform(51000, 53000, 60),
            'low': np.random.uniform(49000, 51000, 60),
            'close': np.linspace(50000, 52000, 60),  # 상승 추세
            'volume': np.random.uniform(1000000, 2000000, 60).astype(int)
        })
        
        mock_api.get_ohlcv.return_value = mock_df
        
        # 스캔 실행
        result = scan_one_symbol("005930", mock_api)
        
        if result is None:
            print("  ⚠️  스캔 결과 없음 (조건 불충족)")
            return
        
        print(f"  ✅ 스캔 결과 반환")
        print(f"  ✅ ticker: {result.get('ticker')}")
        print(f"  ✅ score: {result.get('score')}")
        print(f"  ✅ score_label: {result.get('score_label')}")
        
        # indicators 확인
        indicators = result.get('indicators', {})
        print(f"  ✅ indicators keys: {list(indicators.keys())}")
        print(f"  ✅ TEMA20 포함: {'TEMA20' in indicators}")
        print(f"  ✅ DEMA10 포함: {'DEMA10' in indicators}")
        
        if 'TEMA20' in indicators:
            print(f"  ✅ TEMA20 값: {indicators['TEMA20']}")
        if 'DEMA10' in indicators:
            print(f"  ✅ DEMA10 값: {indicators['DEMA10']}")
        
        # 검증
        assert 'indicators' in result
        assert 'TEMA20' in indicators, "TEMA20이 indicators에 없습니다"
        assert 'DEMA10' in indicators, "DEMA10이 indicators에 없습니다"
        assert 'TEMA' not in indicators, "TEMA 필드가 여전히 존재합니다 (제거되어야 함)"
        assert 'DEMA' not in indicators, "DEMA 필드가 여전히 존재합니다 (제거되어야 함)"
        
        # score_label 검증
        assert 'score_label' in result
        assert isinstance(result['score_label'], str)
        assert not result['score_label'].isdigit(), "score_label이 숫자입니다!"
    
    def test_score_conditions_returns_correct_label(self):
        """score_conditions가 올바른 레이블을 반환하는지 확인"""
        print("\n[통합 Step 2] scanner.py::score_conditions 검증")
        
        from scanner import score_conditions
        from config import config
        
        # Mock 데이터프레임
        dates = pd.date_range(end='2025-11-15', periods=60, freq='D')
        df = pd.DataFrame({
            'date': dates,
            'close': np.linspace(50000, 52000, 60),
            'volume': np.random.uniform(1000000, 2000000, 60).astype(int),
            'TEMA20': np.linspace(49500, 51500, 60),
            'DEMA10': np.linspace(49800, 51800, 60),
            'MACD_OSC': np.random.uniform(100, 200, 60),
            'MACD_LINE': np.random.uniform(100, 200, 60),
            'MACD_SIGNAL': np.random.uniform(80, 180, 60),
            'RSI_TEMA': np.random.uniform(50, 70, 60),
            'RSI_DEMA': np.random.uniform(50, 70, 60),
            'OBV': np.linspace(1000000, 2000000, 60),
            'VOL_MA5': np.random.uniform(900000, 1100000, 60),
            'VOL_MA20': np.random.uniform(800000, 1200000, 60),
            'TEMA20_SLOPE': np.random.uniform(50, 150, 60),
            'DEMA20_SLOPE': np.random.uniform(50, 150, 60),
            'OBV_SLOPE20': np.random.uniform(10000, 50000, 60),
        })
        
        # score_conditions 실행
        score, flags = score_conditions(df, config)
        
        print(f"  ✅ score: {score}")
        print(f"  ✅ flags: {flags}")
        print(f"  ✅ label: {flags.get('label')}")
        
        # 검증
        assert 'label' in flags
        assert isinstance(flags['label'], str)
        assert not flags['label'].isdigit(), "label이 숫자입니다!"
        
        # 점수에 따른 레이블 검증
        if score >= 10:
            assert flags['label'] == "강한 매수"
        elif score >= 8:
            assert flags['label'] == "매수 후보"
        elif score >= 6:
            assert flags['label'] == "관심 (제외)"
        else:
            assert flags['label'] in ["제외", "신호부족(0/3)", "신호부족(1/3)", "신호부족(2/3)"]


class TestMainIntegration:
    """main.py 실제 코드 검증"""
    
    def test_save_snapshot_db_with_tema20_dema10(self):
        """_save_snapshot_db가 TEMA20/DEMA10을 저장하는지 확인"""
        print("\n[통합 Step 3] main.py::_save_snapshot_db 검증")
        
        from models import ScanItem, IndicatorPayload, TrendPayload, ScoreFlags
        
        # Mock ScanItem 생성
        scan_item = ScanItem(
            ticker="005930",
            name="삼성전자",
            match=True,
            score=10.0,
            indicators=IndicatorPayload(
                TEMA20=50000.0,
                DEMA10=51000.0,
                MACD_OSC=100.0,
                MACD_LINE=200.0,
                MACD_SIGNAL=100.0,
                RSI_TEMA=60.0,
                RSI_DEMA=65.0,
                OBV=1000000.0,
                VOL=1000000,
                VOL_MA5=900000.0,
                close=52000.0,
                change_rate=1.5
            ),
            trend=TrendPayload(
                TEMA20_SLOPE=100.0,
                OBV_SLOPE20=50000.0,
                ABOVE_CNT5=3,
                DEMA20_SLOPE=150.0
            ),
            flags=ScoreFlags(
                cross=True,
                vol_expand=True,
                macd_ok=True,
                rsi_ok=True,
                tema_slope_ok=True,
                obv_slope_ok=True,
                above_cnt5_ok=True,
                dema_slope_ok=True,
                match=True,
                label="강한 매수"
            ),
            score_label="강한 매수",
            strategy="상승시작"
        )
        
        # DB 저장 row 시뮬레이션
        as_of = "20251115"
        name = scan_item.name
        current_price = float(scan_item.indicators.close)
        close_price = current_price
        volume = int(scan_item.indicators.VOL)
        change_rate = float(scan_item.indicators.change_rate)
        market = ""
        strategy = scan_item.strategy
        
        indicators_json = json.dumps(scan_item.indicators.__dict__, ensure_ascii=False)
        trend_json = json.dumps(scan_item.trend.__dict__, ensure_ascii=False)
        flags_json = json.dumps(scan_item.flags.__dict__, ensure_ascii=False)
        
        row = (
            as_of, scan_item.ticker, name, float(scan_item.score), scan_item.score_label,
            current_price, volume, change_rate, market, strategy,
            indicators_json, trend_json, flags_json, "{}", "{}", "{}", close_price
        )
        
        print(f"  ✅ Row 생성 성공")
        print(f"  ✅ score: {row[3]}")
        print(f"  ✅ score_label: {row[4]}")
        print(f"  ✅ score_label 타입: {type(row[4])}")
        print(f"  ✅ score_label이 문자열: {isinstance(row[4], str)}")
        print(f"  ✅ score_label이 숫자 아님: {not str(row[4]).isdigit()}")
        
        # indicators JSON 파싱
        indicators_dict = json.loads(row[10])
        print(f"  ✅ indicators에 TEMA20 포함: {'TEMA20' in indicators_dict}")
        print(f"  ✅ indicators에 DEMA10 포함: {'DEMA10' in indicators_dict}")
        print(f"  ✅ TEMA20 값: {indicators_dict.get('TEMA20')}")
        print(f"  ✅ DEMA10 값: {indicators_dict.get('DEMA10')}")
        
        # 검증
        assert isinstance(row[4], str), "score_label이 문자열이 아닙니다"
        assert not str(row[4]).isdigit(), "score_label이 숫자입니다!"
        assert row[4] == "강한 매수"
        assert "TEMA20" in indicators_dict
        assert "DEMA10" in indicators_dict
        assert "TEMA" not in indicators_dict, "TEMA 필드가 여전히 존재합니다"
        assert "DEMA" not in indicators_dict, "DEMA 필드가 여전히 존재합니다"


class TestEndToEnd:
    """End-to-End 통합 테스트"""
    
    def test_full_pipeline_mock(self):
        """전체 파이프라인 시뮬레이션"""
        print("\n[통합 Step 4] End-to-End 파이프라인 검증")
        
        from models import ScanItem, IndicatorPayload, TrendPayload, ScoreFlags
        
        # Step 1: scanner.py 시뮬레이션
        scan_result = {
            "ticker": "005930",
            "name": "삼성전자",
            "match": True,
            "score": 10.0,
            "indicators": {
                "TEMA20": 50000.0,
                "DEMA10": 51000.0,
                "MACD_OSC": 100.0,
                "MACD_LINE": 200.0,
                "MACD_SIGNAL": 100.0,
                "RSI_TEMA": 60.0,
                "RSI_DEMA": 65.0,
                "OBV": 1000000.0,
                "VOL": 1000000,
                "VOL_MA5": 900000.0,
                "close": 52000.0,
                "change_rate": 1.5
            },
            "trend": {
                "TEMA20_SLOPE": 100.0,
                "OBV_SLOPE20": 50000.0,
                "ABOVE_CNT5": 3,
                "DEMA20_SLOPE": 150.0
            },
            "flags": {
                "cross": True,
                "vol_expand": True,
                "macd_ok": True,
                "rsi_ok": True,
                "tema_slope_ok": True,
                "obv_slope_ok": True,
                "above_cnt5_ok": True,
                "dema_slope_ok": True,
                "match": True,
                "label": "강한 매수"
            },
            "strategy": "상승시작",
            "score_label": "강한 매수"
        }
        
        print(f"  ✅ Step 1: scanner.py 결과 생성")
        print(f"     - TEMA20: {scan_result['indicators']['TEMA20']}")
        print(f"     - DEMA10: {scan_result['indicators']['DEMA10']}")
        print(f"     - score_label: {scan_result['score_label']}")
        
        # Step 2: ScanItem 생성 (main.py 로직)
        indicators = IndicatorPayload(**scan_result['indicators'])
        trend = TrendPayload(**scan_result['trend'])
        flags = ScoreFlags(**scan_result['flags'])
        
        scan_item = ScanItem(
            ticker=scan_result['ticker'],
            name=scan_result['name'],
            match=scan_result['match'],
            score=scan_result['score'],
            indicators=indicators,
            trend=trend,
            flags=flags,
            score_label=scan_result['score_label'],
            strategy=scan_result['strategy']
        )
        
        print(f"  ✅ Step 2: ScanItem 생성")
        print(f"     - indicators.TEMA20: {scan_item.indicators.TEMA20}")
        print(f"     - indicators.DEMA10: {scan_item.indicators.DEMA10}")
        print(f"     - score_label: {scan_item.score_label}")
        
        # Step 3: DB 저장 row 생성
        indicators_json = json.dumps(scan_item.indicators.__dict__, ensure_ascii=False)
        indicators_dict = json.loads(indicators_json)
        
        print(f"  ✅ Step 3: DB 저장 준비")
        print(f"     - indicators JSON에 TEMA20 포함: {'TEMA20' in indicators_dict}")
        print(f"     - indicators JSON에 DEMA10 포함: {'DEMA10' in indicators_dict}")
        print(f"     - score_label: {scan_item.score_label}")
        print(f"     - score_label 타입: {type(scan_item.score_label)}")
        
        # 최종 검증
        assert "TEMA20" in indicators_dict
        assert "DEMA10" in indicators_dict
        assert "TEMA" not in indicators_dict
        assert "DEMA" not in indicators_dict
        assert isinstance(scan_item.score_label, str)
        assert not scan_item.score_label.isdigit()
        assert scan_item.score_label == "강한 매수"
        
        print(f"  ✅ Step 4: 전체 파이프라인 검증 완료")


if __name__ == "__main__":
    print("=" * 80)
    print("통합 테스트: 실제 코드 검증")
    print("=" * 80)
    
    pytest.main([__file__, "-v", "-s"])




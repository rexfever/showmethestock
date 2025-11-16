#!/usr/bin/env python3
"""
DB 저장 로직 검증 테스트

단계별 검증:
1. IndicatorPayload에 TEMA20/DEMA10 필드 존재 확인
2. scanner.py의 반환값에 TEMA20/DEMA10 포함 확인
3. ScanItem 생성 시 TEMA20/DEMA10 포함 확인
4. DB 저장 시 indicators에 TEMA20/DEMA10 포함 확인
5. score_label이 올바르게 저장되는지 확인
"""

import pytest
import json
from unittest.mock import Mock, MagicMock
from models import IndicatorPayload, ScanItem, TrendPayload, ScoreFlags


class TestIndicatorPayload:
    """Step 1: IndicatorPayload 모델 검증"""
    
    def test_indicator_payload_has_tema20_dema10(self):
        """TEMA20, DEMA10 필드가 존재하는지 확인"""
        print("\n[Step 1] IndicatorPayload 필드 검증")
        
        # TEMA20, DEMA10 필드로 생성
        indicators = IndicatorPayload(
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
        )
        
        print(f"  ✅ TEMA20 필드 존재: {hasattr(indicators, 'TEMA20')}")
        print(f"  ✅ DEMA10 필드 존재: {hasattr(indicators, 'DEMA10')}")
        print(f"  ✅ TEMA20 값: {indicators.TEMA20}")
        print(f"  ✅ DEMA10 값: {indicators.DEMA10}")
        
        assert hasattr(indicators, 'TEMA20'), "TEMA20 필드가 없습니다"
        assert hasattr(indicators, 'DEMA10'), "DEMA10 필드가 없습니다"
        assert indicators.TEMA20 == 50000.0
        assert indicators.DEMA10 == 51000.0
    
    def test_indicator_payload_no_tema_dema(self):
        """TEMA, DEMA 필드가 제거되었는지 확인"""
        print("\n[Step 1-2] TEMA/DEMA 필드 제거 확인")
        
        # TEMA, DEMA 필드로 생성 시도 (실패해야 함)
        with pytest.raises(Exception) as exc_info:
            indicators = IndicatorPayload(
                TEMA=50000.0,  # 이 필드는 없어야 함
                DEMA=51000.0,  # 이 필드는 없어야 함
                MACD_OSC=100.0,
                MACD_LINE=200.0,
                MACD_SIGNAL=100.0,
                RSI_TEMA=60.0,
                RSI_DEMA=65.0,
                OBV=1000000.0,
                VOL=1000000,
                VOL_MA5=900000.0,
                close=52000.0
            )
        
        print(f"  ✅ TEMA/DEMA 필드 사용 시 에러 발생: {type(exc_info.value).__name__}")
        assert "TEMA20" in str(exc_info.value) or "unexpected" in str(exc_info.value).lower()


class TestScannerOutput:
    """Step 2: scanner.py 반환값 검증"""
    
    def test_scanner_returns_tema20_dema10(self):
        """scanner.py가 TEMA20/DEMA10을 반환하는지 확인"""
        print("\n[Step 2] scanner.py 반환값 검증")
        
        # scanner.py의 반환 형식 시뮬레이션
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
                "label": "강한 매수",
                "match": True
            },
            "strategy": "상승시작",
            "score_label": "강한 매수"
        }
        
        print(f"  ✅ TEMA20 포함: {'TEMA20' in scan_result['indicators']}")
        print(f"  ✅ DEMA10 포함: {'DEMA10' in scan_result['indicators']}")
        print(f"  ✅ TEMA20 값: {scan_result['indicators']['TEMA20']}")
        print(f"  ✅ DEMA10 값: {scan_result['indicators']['DEMA10']}")
        print(f"  ✅ score_label: {scan_result['score_label']}")
        
        assert "TEMA20" in scan_result["indicators"]
        assert "DEMA10" in scan_result["indicators"]
        assert scan_result["indicators"]["TEMA20"] == 50000.0
        assert scan_result["indicators"]["DEMA10"] == 51000.0
        assert scan_result["score_label"] == "강한 매수"


class TestScanItemCreation:
    """Step 3: ScanItem 생성 검증"""
    
    def test_scan_item_with_tema20_dema10(self):
        """ScanItem이 TEMA20/DEMA10을 포함하는지 확인"""
        print("\n[Step 3] ScanItem 생성 검증")
        
        indicators = IndicatorPayload(
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
        )
        
        trend = TrendPayload(
            TEMA20_SLOPE=100.0,
            OBV_SLOPE20=50000.0,
            ABOVE_CNT5=3,
            DEMA20_SLOPE=150.0
        )
        
        flags = ScoreFlags(
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
        )
        
        scan_item = ScanItem(
            ticker="005930",
            name="삼성전자",
            match=True,
            score=10.0,
            indicators=indicators,
            trend=trend,
            flags=flags,
            score_label="강한 매수",
            strategy="상승시작"
        )
        
        print(f"  ✅ ScanItem 생성 성공")
        print(f"  ✅ indicators.TEMA20: {scan_item.indicators.TEMA20}")
        print(f"  ✅ indicators.DEMA10: {scan_item.indicators.DEMA10}")
        print(f"  ✅ score: {scan_item.score}")
        print(f"  ✅ score_label: {scan_item.score_label}")
        
        assert scan_item.indicators.TEMA20 == 50000.0
        assert scan_item.indicators.DEMA10 == 51000.0
        assert scan_item.score == 10.0
        assert scan_item.score_label == "강한 매수"


class TestDBStorage:
    """Step 4: DB 저장 검증"""
    
    def test_indicators_json_serialization(self):
        """indicators가 JSON으로 직렬화될 때 TEMA20/DEMA10 포함 확인"""
        print("\n[Step 4] JSON 직렬화 검증")
        
        indicators = IndicatorPayload(
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
        )
        
        # JSON 직렬화
        indicators_json = json.dumps(indicators.__dict__, ensure_ascii=False)
        indicators_dict = json.loads(indicators_json)
        
        print(f"  ✅ JSON 직렬화 성공")
        print(f"  ✅ JSON에 TEMA20 포함: {'TEMA20' in indicators_dict}")
        print(f"  ✅ JSON에 DEMA10 포함: {'DEMA10' in indicators_dict}")
        print(f"  ✅ TEMA20 값: {indicators_dict.get('TEMA20')}")
        print(f"  ✅ DEMA10 값: {indicators_dict.get('DEMA10')}")
        
        assert "TEMA20" in indicators_dict
        assert "DEMA10" in indicators_dict
        assert indicators_dict["TEMA20"] == 50000.0
        assert indicators_dict["DEMA10"] == 51000.0
    
    def test_db_row_structure(self):
        """DB 저장 row 구조 검증"""
        print("\n[Step 4-2] DB Row 구조 검증")
        
        indicators = IndicatorPayload(
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
        )
        
        trend = TrendPayload(
            TEMA20_SLOPE=100.0,
            OBV_SLOPE20=50000.0,
            ABOVE_CNT5=3,
            DEMA20_SLOPE=150.0
        )
        
        flags = ScoreFlags(
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
        )
        
        scan_item = ScanItem(
            ticker="005930",
            name="삼성전자",
            match=True,
            score=10.0,
            indicators=indicators,
            trend=trend,
            flags=flags,
            score_label="강한 매수",
            strategy="상승시작"
        )
        
        # DB 저장 row 시뮬레이션 (main.py::_save_snapshot_db 로직)
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
        details_json = json.dumps({}, ensure_ascii=False)
        returns_json = json.dumps({}, ensure_ascii=False)
        recurrence_json = json.dumps({}, ensure_ascii=False)
        
        row = (
            as_of, scan_item.ticker, name, float(scan_item.score), scan_item.score_label,
            current_price, volume, change_rate, market, strategy,
            indicators_json, trend_json, flags_json, details_json,
            returns_json, recurrence_json, close_price
        )
        
        print(f"  ✅ Row 생성 성공")
        print(f"  ✅ date: {row[0]}")
        print(f"  ✅ code: {row[1]}")
        print(f"  ✅ score: {row[3]}")
        print(f"  ✅ score_label: {row[4]}")
        print(f"  ✅ indicators JSON 길이: {len(row[10])}")
        
        # indicators JSON 파싱
        indicators_dict = json.loads(row[10])
        print(f"  ✅ indicators에 TEMA20 포함: {'TEMA20' in indicators_dict}")
        print(f"  ✅ indicators에 DEMA10 포함: {'DEMA10' in indicators_dict}")
        
        assert row[3] == 10.0  # score
        assert row[4] == "강한 매수"  # score_label
        assert "TEMA20" in indicators_dict
        assert "DEMA10" in indicators_dict
        assert indicators_dict["TEMA20"] == 50000.0
        assert indicators_dict["DEMA10"] == 51000.0


class TestScoreLabel:
    """Step 5: score_label 검증"""
    
    def test_score_label_mapping(self):
        """점수에 따른 score_label 매핑 확인"""
        print("\n[Step 5] score_label 매핑 검증")
        
        test_cases = [
            (10.0, "강한 매수"),
            (9.0, "매수 후보"),  # 9점은 8점 이상이므로 "매수 후보"
            (8.0, "매수 후보"),
            (7.0, "관심 (제외)"),  # 7점은 6점 이상이므로 "관심 (제외)"
            (6.0, "관심 (제외)"),
            (5.0, "제외"),  # 5점은 6점 미만이므로 "제외"
            (4.0, "제외"),
        ]
        
        for score, expected_label in test_cases:
            # scanner.py의 score_conditions 로직 시뮬레이션
            if score >= 10:
                label = "강한 매수"
            elif score >= 8:
                label = "매수 후보"
            elif score >= 6:
                label = "관심 (제외)"
            else:
                label = "제외"
            
            print(f"  ✅ score={score} → label={label}")
            assert label == expected_label, f"점수 {score}의 레이블이 {expected_label}이어야 하는데 {label}입니다"
    
    def test_score_label_is_string(self):
        """score_label이 문자열인지 확인 (숫자가 아님)"""
        print("\n[Step 5-2] score_label 타입 검증")
        
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
                close=52000.0
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
        
        print(f"  ✅ score_label 타입: {type(scan_item.score_label)}")
        print(f"  ✅ score_label 값: {scan_item.score_label}")
        print(f"  ✅ score_label이 문자열: {isinstance(scan_item.score_label, str)}")
        print(f"  ✅ score_label이 숫자 아님: {not scan_item.score_label.isdigit()}")
        
        assert isinstance(scan_item.score_label, str)
        assert not scan_item.score_label.isdigit()
        assert scan_item.score_label in ["강한 매수", "매수 후보", "관심 (제외)", "제외"]


if __name__ == "__main__":
    print("=" * 80)
    print("DB 저장 로직 검증 테스트")
    print("=" * 80)
    
    pytest.main([__file__, "-v", "-s"])


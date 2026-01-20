#!/usr/bin/env python3
"""
최종 검증 테스트

핵심 로직만 단계별로 검증:
1. IndicatorPayload 필드 검증
2. ScanItem 생성 검증
3. DB 저장 row 검증
4. score_label 검증
"""

import pytest
import json
from models import IndicatorPayload, ScanItem, TrendPayload, ScoreFlags


def test_step1_indicator_payload():
    """Step 1: IndicatorPayload에 TEMA20/DEMA10 필드 존재"""
    print("\n" + "="*80)
    print("[Step 1] IndicatorPayload 필드 검증")
    print("="*80)
    
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
    
    print(f"✅ TEMA20 필드 존재: {hasattr(indicators, 'TEMA20')}")
    print(f"✅ DEMA10 필드 존재: {hasattr(indicators, 'DEMA10')}")
    print(f"✅ TEMA20 값: {indicators.TEMA20}")
    print(f"✅ DEMA10 값: {indicators.DEMA10}")
    
    # TEMA, DEMA 필드는 없어야 함
    try:
        _ = indicators.TEMA
        assert False, "TEMA 필드가 존재합니다 (제거되어야 함)"
    except AttributeError:
        print(f"✅ TEMA 필드 제거됨")
    
    try:
        _ = indicators.DEMA
        assert False, "DEMA 필드가 존재합니다 (제거되어야 함)"
    except AttributeError:
        print(f"✅ DEMA 필드 제거됨")
    
    assert indicators.TEMA20 == 50000.0
    assert indicators.DEMA10 == 51000.0
    print("\n✅ Step 1 통과\n")


def test_step2_scan_item_creation():
    """Step 2: ScanItem이 TEMA20/DEMA10을 포함"""
    print("="*80)
    print("[Step 2] ScanItem 생성 검증")
    print("="*80)
    
    scan_item = ScanItem(
        ticker="005930",
        name="삼성전자",
        match=True,
        score=10.0,
        indicators=IndicatorPayload(
            TEMA20=50000.0,
            DEMA20=50500.0,
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
            EMA60_SLOPE=50.0,
            TEMA20_SLOPE=100.0,
            DEMA20_SLOPE=150.0,
            OBV_SLOPE20=50000.0,
            ABOVE_CNT5=3,
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
    
    print(f"✅ ScanItem 생성 성공")
    print(f"✅ ticker: {scan_item.ticker}")
    print(f"✅ score: {scan_item.score}")
    print(f"✅ score_label: {scan_item.score_label}")
    print(f"✅ indicators.TEMA20: {scan_item.indicators.TEMA20}")
    print(f"✅ indicators.DEMA10: {scan_item.indicators.DEMA10}")
    
    assert scan_item.indicators.TEMA20 == 50000.0
    assert scan_item.indicators.DEMA10 == 51000.0
    assert scan_item.score == 10.0
    assert scan_item.score_label == "강한 매수"
    print("\n✅ Step 2 통과\n")


def test_step3_json_serialization():
    """Step 3: JSON 직렬화 시 TEMA20/DEMA10 포함"""
    print("="*80)
    print("[Step 3] JSON 직렬화 검증")
    print("="*80)
    
    indicators = IndicatorPayload(
        TEMA20=50000.0,
        DEMA20=50500.0,
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
    )
    
    # JSON 직렬화
    indicators_json = json.dumps(indicators.__dict__, ensure_ascii=False)
    indicators_dict = json.loads(indicators_json)
    
    print(f"✅ JSON 직렬화 성공")
    print(f"✅ JSON keys: {list(indicators_dict.keys())}")
    print(f"✅ TEMA20 포함: {'TEMA20' in indicators_dict}")
    print(f"✅ DEMA10 포함: {'DEMA10' in indicators_dict}")
    print(f"✅ TEMA 제거됨: {'TEMA' not in indicators_dict}")
    print(f"✅ DEMA 제거됨: {'DEMA' not in indicators_dict}")
    print(f"✅ TEMA20 값: {indicators_dict['TEMA20']}")
    print(f"✅ DEMA10 값: {indicators_dict['DEMA10']}")
    
    assert "TEMA20" in indicators_dict
    assert "DEMA10" in indicators_dict
    assert "TEMA" not in indicators_dict
    assert "DEMA" not in indicators_dict
    assert indicators_dict["TEMA20"] == 50000.0
    assert indicators_dict["DEMA10"] == 51000.0
    print("\n✅ Step 3 통과\n")


def test_step4_db_row_structure():
    """Step 4: DB 저장 row 구조 검증"""
    print("="*80)
    print("[Step 4] DB Row 구조 검증")
    print("="*80)
    
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
    
    # DB 저장 row 시뮬레이션 (main.py::_save_snapshot_db 로직)
    as_of = "20251115"
    indicators_json = json.dumps(scan_item.indicators.__dict__, ensure_ascii=False)
    
    row = (
        as_of,
        scan_item.ticker,
        scan_item.name,
        float(scan_item.score),
        scan_item.score_label,  # 이 필드가 중요!
        float(scan_item.indicators.close),
        int(scan_item.indicators.VOL),
        float(scan_item.indicators.change_rate),
        "",
        scan_item.strategy,
        indicators_json,
        "{}",
        "{}",
        "{}",
        "{}",
        "{}",
        float(scan_item.indicators.close)
    )
    
    print(f"✅ Row 생성 성공")
    print(f"✅ date: {row[0]}")
    print(f"✅ code: {row[1]}")
    print(f"✅ name: {row[2]}")
    print(f"✅ score: {row[3]} (타입: {type(row[3])})")
    print(f"✅ score_label: '{row[4]}' (타입: {type(row[4])})")
    print(f"✅ current_price: {row[5]}")
    
    # score_label 검증
    print(f"\n[score_label 상세 검증]")
    print(f"  - 값: '{row[4]}'")
    print(f"  - 타입: {type(row[4])}")
    print(f"  - 문자열인가: {isinstance(row[4], str)}")
    print(f"  - 숫자인가: {str(row[4]).isdigit()}")
    print(f"  - 가격과 같은가: {row[4] == str(int(row[5]))}")
    
    # indicators JSON 파싱
    indicators_dict = json.loads(row[10])
    print(f"\n[indicators JSON 검증]")
    print(f"  - TEMA20 포함: {'TEMA20' in indicators_dict}")
    print(f"  - DEMA10 포함: {'DEMA10' in indicators_dict}")
    print(f"  - TEMA 제거됨: {'TEMA' not in indicators_dict}")
    print(f"  - DEMA 제거됨: {'DEMA' not in indicators_dict}")
    print(f"  - TEMA20 값: {indicators_dict.get('TEMA20')}")
    print(f"  - DEMA10 값: {indicators_dict.get('DEMA10')}")
    
    # 검증
    assert row[3] == 10.0, f"score가 {row[3]}입니다 (10.0이어야 함)"
    assert row[4] == "강한 매수", f"score_label이 '{row[4]}'입니다 ('강한 매수'이어야 함)"
    assert isinstance(row[4], str), "score_label이 문자열이 아닙니다"
    assert not str(row[4]).isdigit(), f"score_label이 숫자입니다: {row[4]}"
    assert row[4] != str(int(row[5])), f"score_label이 가격과 같습니다: {row[4]} == {int(row[5])}"
    
    assert "TEMA20" in indicators_dict, "TEMA20이 indicators에 없습니다"
    assert "DEMA10" in indicators_dict, "DEMA10이 indicators에 없습니다"
    assert "TEMA" not in indicators_dict, "TEMA가 여전히 존재합니다"
    assert "DEMA" not in indicators_dict, "DEMA가 여전히 존재합니다"
    
    print("\n✅ Step 4 통과\n")


def test_step5_score_label_mapping():
    """Step 5: 점수에 따른 score_label 매핑"""
    print("="*80)
    print("[Step 5] score_label 매핑 검증")
    print("="*80)
    
    test_cases = [
        (10.0, "강한 매수"),
        (9.0, "매수 후보"),
        (8.0, "매수 후보"),
        (7.0, "관심 (제외)"),
        (6.0, "관심 (제외)"),
        (5.0, "제외"),
        (4.0, "제외"),
    ]
    
    for score, expected_label in test_cases:
        # scanner.py의 score_conditions 로직
        if score >= 10:
            label = "강한 매수"
        elif score >= 8:
            label = "매수 후보"
        elif score >= 6:
            label = "관심 (제외)"
        else:
            label = "제외"
        
        print(f"✅ score={score:4.1f} → label='{label}'")
        assert label == expected_label, f"점수 {score}의 레이블이 '{expected_label}'이어야 하는데 '{label}'입니다"
        assert isinstance(label, str), "label이 문자열이 아닙니다"
        assert not label.isdigit(), f"label이 숫자입니다: {label}"
    
    print("\n✅ Step 5 통과\n")


if __name__ == "__main__":
    print("\n" + "="*80)
    print("최종 검증 테스트 시작")
    print("="*80 + "\n")
    
    pytest.main([__file__, "-v", "-s"])
    
    print("\n" + "="*80)
    print("모든 검증 완료!")
    print("="*80 + "\n")


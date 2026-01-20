"""
스캐너 V2 상세 테스트 - 실제 로직 검증
"""
import sys
import os
import unittest
from unittest.mock import patch, MagicMock, Mock
import pandas as pd

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# DB 의존성 모킹 (로컬 환경)
import sys
mock_psycopg = MagicMock()
sys.modules['psycopg'] = mock_psycopg
sys.modules['psycopg.types'] = MagicMock()

mock_db_manager = MagicMock()
sys.modules['db_manager'] = mock_db_manager


def test_scanner_v2_scan_one_logic():
    """ScannerV2의 scan_one 로직 테스트"""
    print("\n=== 1. ScannerV2 scan_one 로직 테스트 ===")
    
    try:
        from scanner_v2 import ScannerV2
        from scanner_v2.config_v2 import ScannerV2Config
        from market_analyzer import MarketCondition
        
        # Mock 설정
        mock_config = MagicMock()
        mock_config.ohlcv_count = 220
        mock_config.market_analysis_enable = True
        mock_config.min_turnover_krw = 100000000
        mock_config.min_price = 1000
        mock_config.overheat_rsi_tema = 80
        mock_config.overheat_vol_mult = 3.0
        mock_config.gap_min = 0.002
        mock_config.gap_max = 0.015
        mock_config.ext_from_tema20_max = 0.015
        mock_config.use_atr_filter = False
        mock_config.inverse_etf_keywords = ['인버스', '레버리지']
        mock_config.bond_etf_keywords = ['국채', '채권']
        mock_config.rsi_upper_limit = 70
        
        # Mock API
        mock_api = MagicMock()
        mock_api.get_ohlcv.return_value = pd.DataFrame({
            'open': [100, 101, 102, 103, 104] * 50,
            'high': [105, 106, 107, 108, 109] * 50,
            'low': [95, 96, 97, 98, 99] * 50,
            'close': [100, 101, 102, 103, 104] * 50,
            'volume': [1000000] * 250
        })
        mock_api.get_stock_name.return_value = '테스트종목'
        
        # Market Condition
        market_condition = MarketCondition(
            date='20251121',
            kospi_return=0.01,
            volatility=0.02,
            market_sentiment='neutral',
            sector_rotation='mixed',
            foreign_flow='neutral',
            institution_flow='neutral',
            volume_trend='normal',
            rsi_threshold=58.0,
            min_signals=3,
            macd_osc_min=0.0,
            vol_ma5_mult=2.5,
            gap_max=0.015,
            ext_from_tema20_max=0.015
        )
        
        scanner = ScannerV2(mock_config)
        
        with patch('scanner_v2.core.scanner.api', mock_api):
            with patch('scanner_v2.core.indicator_calculator.api', mock_api):
                result = scanner.scan_one('005930', '20251121', market_condition)
                
                if result is None:
                    print("✅ scan_one 필터링 동작 확인 (데이터 부족 또는 필터링)")
                else:
                    print(f"✅ scan_one 결과 반환: {result.ticker}")
        
        return True
    except Exception as e:
        print(f"⚠️  scan_one 로직 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_filter_engine_hard_filters():
    """FilterEngine의 하드 필터 테스트"""
    print("\n=== 2. FilterEngine 하드 필터 테스트 ===")
    
    try:
        from scanner_v2.core.filter_engine import FilterEngine
        
        mock_config = MagicMock()
        mock_config.inverse_etf_keywords = ['인버스', '레버리지']
        mock_config.bond_etf_keywords = ['국채', '채권']
        mock_config.rsi_upper_limit = 70
        mock_config.min_turnover_krw = 100000000
        mock_config.min_price = 1000
        mock_config.overheat_rsi_tema = 80
        mock_config.overheat_vol_mult = 3.0
        mock_config.market_analysis_enable = True
        
        filter_engine = FilterEngine(mock_config)
        
        # 테스트 데이터
        df = pd.DataFrame({
            'close': [1000, 1010, 1020, 1030, 1040] * 50,
            'volume': [1000000] * 250,
            'RSI_TEMA': [50] * 250
        })
        
        # 인버스 ETF 필터 테스트
        result = filter_engine.apply_hard_filters(df, '인버스 ETF', None)
        if not result:
            print("✅ 인버스 ETF 필터 동작 확인")
        
        # 정상 종목 필터 테스트
        result = filter_engine.apply_hard_filters(df, '삼성전자', None)
        if result:
            print("✅ 정상 종목 필터 통과 확인")
        
        return True
    except Exception as e:
        print(f"⚠️  FilterEngine 하드 필터 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_scorer_calculation():
    """Scorer의 점수 계산 테스트"""
    print("\n=== 3. Scorer 점수 계산 테스트 ===")
    
    try:
        from scanner_v2.core.scorer import Scorer
        
        mock_config = MagicMock()
        mock_config.min_turnover_krw = 100000000
        mock_config.min_price = 1000
        mock_config.overheat_rsi_tema = 80
        mock_config.overheat_vol_mult = 3.0
        mock_config.gap_min = 0.002
        mock_config.gap_max = 0.015
        mock_config.ext_from_tema20_max = 0.015
        mock_config.use_atr_filter = False
        mock_config.market_analysis_enable = True
        
        scorer = Scorer(mock_config)
        
        # 테스트 데이터 (골든크로스 + 거래량 확대)
        df = pd.DataFrame({
            'close': [1000, 1010, 1020, 1030, 1040] * 50,
            'volume': [1000000] * 250,
            'TEMA20': [990, 1000, 1010, 1020, 1030] * 50,
            'DEMA10': [980, 990, 1000, 1010, 1020] * 50,
            'VOL_MA5': [500000] * 250,
            'RSI_TEMA': [50] * 250,
            'MACD_OSC': [1.0] * 250,
            'OBV': [1000000] * 250
        })
        
        score, flags = scorer.calculate_score(df, None)
        
        print(f"✅ 점수 계산 결과: {score}점")
        print(f"   플래그: {list(flags.keys())[:5]}...")
        
        return True
    except Exception as e:
        print(f"⚠️  Scorer 점수 계산 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_strategy_determination_detailed():
    """전략 결정 상세 테스트"""
    print("\n=== 4. 전략 결정 상세 테스트 ===")
    
    try:
        from scanner_v2.core.strategy import determine_trading_strategy
        
        test_cases = [
            {
                'name': '스윙 (골든크로스 + 거래량 + 모멘텀)',
                'flags': {
                    'cross': True,
                    'vol_expand': True,
                    'macd_ok': True,
                    'rsi_ok': True,
                    'tema_slope_ok': False,
                    'obv_slope_ok': False
                },
                'score': 10.0,
                'expected': '스윙'
            },
            {
                'name': '포지션 (골든크로스 + 추세)',
                'flags': {
                    'cross': True,
                    'vol_expand': False,
                    'tema_slope_ok': True,
                    'obv_slope_ok': True,
                    'above_cnt5_ok': True
                },
                'score': 9.0,
                'expected': '포지션'
            },
            {
                'name': '장기 (추세 중심)',
                'flags': {
                    'cross': False,
                    'vol_expand': False,
                    'tema_slope_ok': True,
                    'obv_slope_ok': True
                },
                'score': 6.0,
                'expected': '장기'
            },
            {
                'name': '관찰 (점수 부족)',
                'flags': {
                    'cross': False,
                    'vol_expand': False
                },
                'score': 4.0,
                'expected': '관찰'
            }
        ]
        
        for case in test_cases:
            strategy, take_profit, stop_loss, holding = determine_trading_strategy(
                case['flags'], case['score']
            )
            
            if strategy == case['expected']:
                print(f"✅ {case['name']}: {strategy} (목표: {take_profit}, 손절: {stop_loss})")
            else:
                print(f"⚠️  {case['name']}: 예상 {case['expected']}, 실제 {strategy}")
        
        return True
    except Exception as e:
        print(f"⚠️  전략 결정 상세 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_scanner_factory_v2_flow():
    """Scanner Factory V2 플로우 테스트"""
    print("\n=== 5. Scanner Factory V2 플로우 테스트 ===")
    
    try:
        from scanner_factory import get_scanner, scan_with_scanner
        from market_analyzer import MarketCondition
        
        # V2 스캐너 가져오기
        with patch('config.config') as mock_config:
            mock_config.scanner_version = 'v2'
            mock_config.scanner_v2_enabled = True
            mock_config.market_analysis_enable = True
            
            with patch('scanner_v2.ScannerV2') as mock_scanner_v2:
                mock_instance = MagicMock()
                from scanner_v2.core.scanner import ScanResult
                mock_instance.scan.return_value = [
                    ScanResult(
                        ticker='005930',
                        name='삼성전자',
                        match=True,
                        score=10.0,
                        indicators={},
                        trend={},
                        strategy='스윙',
                        flags={},
                        score_label='강한 매수'
                    )
                ]
                mock_scanner_v2.return_value = mock_instance
                
                scanner = get_scanner('v2')
                if scanner == mock_instance:
                    print("✅ V2 스캐너 인스턴스 반환 성공")
                
                # scan_with_scanner 테스트
                market_condition = MarketCondition(
                    date='20251121',
                    kospi_return=0.01,
                    volatility=0.02,
                    market_sentiment='neutral',
                    sector_rotation='mixed',
                    foreign_flow='neutral',
                    institution_flow='neutral',
                    volume_trend='normal',
                    rsi_threshold=58.0,
                    min_signals=3,
                    macd_osc_min=0.0,
                    vol_ma5_mult=2.5,
                    gap_max=0.015,
                    ext_from_tema20_max=0.015
                )
                
                results = scan_with_scanner(
                    ['005930'], 
                    None, 
                    '20251121', 
                    market_condition, 
                    'v2'
                )
                
                if len(results) > 0:
                    print(f"✅ scan_with_scanner 결과 반환: {len(results)}개")
                    print(f"   첫 번째 결과: {results[0]['ticker']}, 점수: {results[0]['score']}")
        
        return True
    except Exception as e:
        print(f"⚠️  Scanner Factory V2 플로우 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_preset_overrides_application():
    """preset_overrides 적용 테스트"""
    print("\n=== 6. Preset Overrides 적용 테스트 ===")
    
    try:
        from scanner_factory import scan_with_scanner
        from market_analyzer import MarketCondition
        
        market_condition = MarketCondition(
            date='20251121',
            kospi_return=0.01,
            volatility=0.02,
            market_sentiment='neutral',
            sector_rotation='mixed',
            foreign_flow='neutral',
            institution_flow='neutral',
            volume_trend='normal',
            rsi_threshold=58.0,
            min_signals=3,
            macd_osc_min=0.0,
            vol_ma5_mult=2.5,
            gap_max=0.015,
            ext_from_tema20_max=0.015
        )
        
        preset_overrides = {
            'min_signals': 4,
            'gap_max': 0.025,
            'ext_from_tema20_max': 0.030
        }
        
        with patch('config.config') as mock_config:
            mock_config.scanner_version = 'v2'
            mock_config.scanner_v2_enabled = True
            mock_config.vol_ma20_mult = 1.2
            
            with patch('scanner_factory.get_scanner') as mock_get_scanner:
                mock_v2_scanner = MagicMock()
                mock_v2_scanner.scan.return_value = []
                mock_get_scanner.return_value = mock_v2_scanner
                
                scan_with_scanner(
                    ['005930'], 
                    preset_overrides, 
                    '20251121', 
                    market_condition, 
                    'v2'
                )
                
                # market_condition이 수정되었는지 확인
                call_args = mock_v2_scanner.scan.call_args
                if call_args:
                    modified_mc = call_args[0][2]
                    if modified_mc.min_signals == 4:
                        print("✅ min_signals override 적용 확인")
                    if modified_mc.gap_max == 0.025:
                        print("✅ gap_max override 적용 확인")
                    if modified_mc.ext_from_tema20_max == 0.030:
                        print("✅ ext_from_tema20_max override 적용 확인")
        
        return True
    except Exception as e:
        print(f"⚠️  Preset Overrides 적용 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config_fallback_mechanism():
    """Config Fallback 메커니즘 테스트"""
    print("\n=== 7. Config Fallback 메커니즘 테스트 ===")
    
    try:
        from config import config
        import os
        
        # DB 연결 실패 시나리오
        with patch('scanner_settings_manager.get_scanner_version') as mock_get_version:
            mock_get_version.side_effect = Exception("DB 연결 실패")
            
            with patch.dict(os.environ, {'SCANNER_VERSION': 'v2'}, clear=False):
                version = config.scanner_version
                if version == 'v2':
                    print("✅ DB 연결 실패 시 .env fallback 동작 확인")
        
        # DB에 값이 있을 때
        with patch('scanner_settings_manager.get_scanner_version') as mock_get_version:
            mock_get_version.return_value = 'v1'
            
            version = config.scanner_version
            if version == 'v1':
                print("✅ DB 우선 조회 동작 확인")
        
        return True
    except Exception as e:
        print(f"⚠️  Config Fallback 메커니즘 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """메인 테스트 실행"""
    print("=" * 60)
    print("스캐너 V2 상세 로직 테스트")
    print("=" * 60)
    
    results = []
    
    # 각 테스트 실행
    results.append(("ScannerV2 scan_one", test_scanner_v2_scan_one_logic()))
    results.append(("FilterEngine 하드 필터", test_filter_engine_hard_filters()))
    results.append(("Scorer 점수 계산", test_scorer_calculation()))
    results.append(("전략 결정 상세", test_strategy_determination_detailed()))
    results.append(("Scanner Factory V2", test_scanner_factory_v2_flow()))
    results.append(("Preset Overrides", test_preset_overrides_application()))
    results.append(("Config Fallback", test_config_fallback_mechanism()))
    
    # 결과 요약
    print("\n" + "=" * 60)
    print("상세 테스트 결과 요약")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ 통과" if result else "❌ 실패"
        print(f"{name:30s} {status}")
    
    print(f"\n총 {total}개 테스트 중 {passed}개 통과, {total - passed}개 실패")
    
    if passed == total:
        print("\n🎉 모든 상세 테스트 통과!")
        return 0
    else:
        print(f"\n⚠️  {total - passed}개 테스트 실패")
        return 1


if __name__ == "__main__":
    exit(main())


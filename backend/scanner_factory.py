"""
스캐너 팩토리 - 버전별 스캐너 생성
"""
from typing import Optional
from market_analyzer import MarketAnalyzer


def get_scanner(version: str = None, market_analyzer: Optional[MarketAnalyzer] = None):
    """
    스캐너 버전에 따라 적절한 스캐너 반환
    
    Args:
        version: 스캐너 버전 ('v1' 또는 'v2'), None이면 config에서 읽음
        market_analyzer: 시장 분석기 (선택)
    
    Returns:
        스캐너 인스턴스
    """
    from config import config
    
    # 버전 결정
    if version is None:
        version = getattr(config, 'scanner_version', 'v1')
    
    # v2 활성화 여부 확인
    if version == 'v2':
        v2_enabled = getattr(config, 'scanner_v2_enabled', False)
        if not v2_enabled:
            print("⚠️ 스캐너 v2가 비활성화되어 있습니다. v1을 사용합니다.")
            version = 'v1'
    
    if version == 'v2':
        # V2 스캐너 사용
        from scanner_v2 import ScannerV2
        from scanner_v2.config_v2 import scanner_v2_config
        
        # scanner_v2_config에 market_analysis_enable 추가
        scanner_v2_config.market_analysis_enable = config.market_analysis_enable
        
        return ScannerV2(scanner_v2_config, market_analyzer)
    else:
        # V1 스캐너 사용 (기존 방식)
        from scanner import scan_with_preset
        return scan_with_preset


def scan_with_scanner(universe_codes: list, preset_overrides: dict = None, 
                     base_date: str = None, market_condition=None, version: str = None):
    """
    스캐너 버전에 따라 스캔 실행
    
    Args:
        universe_codes: 종목 코드 리스트
        preset_overrides: 프리셋 오버라이드 (V1에서만 사용, V2는 market_condition에 반영)
        base_date: 스캔 날짜
        market_condition: 시장 조건
        version: 스캐너 버전
    
    Returns:
        스캔 결과 리스트
    """
    from config import config
    
    # 버전 결정
    if version is None:
        version = getattr(config, 'scanner_version', 'v1')
    
    # v2 활성화 여부 확인
    if version == 'v2':
        v2_enabled = getattr(config, 'scanner_v2_enabled', False)
        if not v2_enabled:
            version = 'v1'
    
    if version == 'v2':
        # V2 스캐너: preset_overrides를 market_condition에 반영
        scanner = get_scanner(version)
        
        # preset_overrides가 있으면 market_condition에 반영
        if preset_overrides and market_condition:
            from copy import deepcopy
            market_condition = deepcopy(market_condition)
            if 'min_signals' in preset_overrides:
                market_condition.min_signals = preset_overrides['min_signals']
            if 'vol_ma5_mult' in preset_overrides:
                market_condition.vol_ma5_mult = preset_overrides['vol_ma5_mult']
            if 'vol_ma20_mult' in preset_overrides:
                market_condition.vol_ma20_mult = preset_overrides.get('vol_ma20_mult', getattr(market_condition, 'vol_ma20_mult', config.vol_ma20_mult))
            if 'gap_max' in preset_overrides:
                market_condition.gap_max = preset_overrides['gap_max']
            if 'ext_from_tema20_max' in preset_overrides:
                market_condition.ext_from_tema20_max = preset_overrides['ext_from_tema20_max']
        
        results = scanner.scan(universe_codes, base_date, market_condition)
        # ScanResult를 dict로 변환
        return [{
            "ticker": r.ticker,
            "name": r.name,
            "match": r.match,
            "score": r.score,
            "indicators": r.indicators,
            "trend": r.trend,
            "strategy": r.strategy,
            "flags": r.flags,
            "score_label": r.score_label,
        } for r in results]
    else:
        # V1 스캐너 (기존 방식)
        scanner = get_scanner(version)
        return scanner(universe_codes, preset_overrides or {}, base_date, market_condition)


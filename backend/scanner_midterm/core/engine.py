"""
Scanner Midterm 엔진 - 중기 추세 기반 스캔
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def run_daily_scan(date: str, universe: List[str], top_n: int = 10) -> Dict[str, Any]:
    """
    일일 스캔 실행 (중기 추세 기반)
    
    Args:
        date: 스캔 날짜 (YYYYMMDD)
        universe: 유니버스 종목 리스트
        top_n: 상위 N개 반환
        
    Returns:
        {
            "candidates": [...],
            "diagnostics": {...},
            "cache_stats": {...}
        }
    """
    try:
        from scanner_v2.core.scanner import ScannerV2
        from scanner_v2.config_v2 import ScannerV2Config
        from market_analyzer import market_analyzer
        from scanner_settings_manager import get_regime_version
        
        # V2 스캐너를 중기 전략으로 사용 (임시)
        # TODO: 실제 midterm 전용 로직 구현 필요
        config = ScannerV2Config()
        scanner = ScannerV2(config, market_analyzer)
        
        # 레짐 분석
        regime_version = get_regime_version()
        market_condition = market_analyzer.analyze_market_condition(date, regime_version=regime_version)
        
        # 스캔 실행
        candidates = []
        for code in universe:
            try:
                result = scanner.scan_one(code, date, market_condition)
                if result and result.match:
                    candidates.append({
                        "code": result.ticker,
                        "score": result.score,
                        "rank": None,  # rank는 나중에 설정
                        "indicators": result.indicators,
                        "meta": {
                            "match": result.match,
                            "strategy": result.strategy,
                            "flags": result.flags,
                            "trend": result.trend
                        }
                    })
            except Exception as e:
                logger.debug(f"종목 {code} 스캔 실패: {e}")
                continue
        
        # 점수 기준 정렬 및 상위 N개 선택
        candidates.sort(key=lambda x: x.get("score", 0), reverse=True)
        candidates = candidates[:top_n]
        
        # rank 설정
        for idx, candidate in enumerate(candidates, 1):
            candidate["rank"] = idx
        
        return {
            "candidates": candidates,
            "diagnostics": {
                "total_scanned": len(universe),
                "matched": len(candidates),
                "date": date
            },
            "cache_stats": {}
        }
        
    except Exception as e:
        logger.error(f"Midterm 스캔 실행 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "candidates": [],
            "diagnostics": {"error": str(e)},
            "cache_stats": {}
        }


"""
Scanner V3 엔진 - midterm + v2-lite 조합
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ScannerV3:
    """
    Scanner V3 - 중기(midterm) + 단기(v2-lite) 조합 엔진
    
    운영 원칙:
    1. midterm은 항상 실행
    2. v2-lite는 neutral/normal 레짐에서만 실행
    3. 두 엔진의 결과는 절대 병합하지 않음
    4. 두 엔진은 서로의 fallback, ranking, score, filter에 영향을 주지 않음
    """
    
    def __init__(self):
        """Scanner V3 초기화"""
        pass
    
    def scan(
        self,
        universe: List[str],
        date: str = None,
        market_condition: Any = None
    ) -> Dict[str, Any]:
        """
        V3 스캔 실행
        
        Args:
            universe: 유니버스 종목 리스트
            date: 스캔 날짜 (YYYYMMDD)
            market_condition: 시장 조건 (레짐 분석 결과)
        
        Returns:
            {
                "engine_version": "v3",
                "date": "YYYYMMDD",
                "regime": {
                    "final": "...",
                    "risk": "..."
                },
                "results": {
                    "midterm": {
                        "enabled": true,
                        "candidates": [...]
                    },
                    "v2_lite": {
                        "enabled": true | false,
                        "candidates": [...] | []
                    }
                }
            }
        """
        scan_date = date or datetime.now().strftime('%Y%m%d')
        
        # Step 1: 레짐 판정
        final_regime, risk_label = self._determine_regime(market_condition, scan_date)
        
        # Step 2: midterm 실행 (항상)
        midterm_result = self._run_midterm(universe, scan_date)
        
        # Step 3: v2-lite 실행 (neutral/normal일 때만)
        v2_lite_enabled = (final_regime == "neutral" and risk_label == "normal")
        v2_lite_result = None
        if v2_lite_enabled:
            v2_lite_result = self._run_v2_lite(universe, scan_date)
        else:
            v2_lite_result = {
                "enabled": False,
                "candidates": []
            }
        
        # Step 4: 결과 분리 반환
        return {
            "engine_version": "v3",
            "date": scan_date,
            "regime": {
                "final": final_regime,
                "risk": risk_label
            },
            "results": {
                "midterm": {
                    "enabled": True,
                    "candidates": midterm_result.get("candidates", [])
                },
                "v2_lite": {
                    "enabled": v2_lite_result.get("enabled", False),
                    "candidates": v2_lite_result.get("candidates", [])
                }
            }
        }
    
    def _determine_regime(self, market_condition: Any, date: str) -> tuple:
        """
        레짐 판정
        
        Args:
            market_condition: 시장 조건 객체
            date: 스캔 날짜
        
        Returns:
            (final_regime, risk_label) 튜플
        """
        # market_condition이 없으면 레짐 분석 실행
        if market_condition is None:
            try:
                from market_analyzer import market_analyzer
                from scanner_settings_manager import get_regime_version
                
                regime_version = get_regime_version()
                market_condition = market_analyzer.analyze_market_condition(date, regime_version=regime_version)
            except Exception as e:
                logger.warning(f"레짐 분석 실패, 기본값 사용: {e}")
                return ("neutral", "normal")
        
        # 레짐 정보 추출 (기존 로직 재사용)
        from scanner_v2.regime_policy import _extract_final_regime, _extract_risk_label
        
        final_regime = _extract_final_regime(market_condition)
        risk_label = _extract_risk_label(market_condition)
        
        return (final_regime, risk_label)
    
    def _run_midterm(self, universe: List[str], date: str) -> Dict[str, Any]:
        """
        Midterm 엔진 실행
        
        Args:
            universe: 유니버스 종목 리스트
            date: 스캔 날짜
        
        Returns:
            midterm 스캔 결과
        """
        try:
            from scanner_midterm.core.engine import run_daily_scan
            from scanner_midterm.config import DEFAULT_TOP_N
            
            result = run_daily_scan(date, universe, top_n=DEFAULT_TOP_N)
            
            # candidates를 표준 형식으로 변환
            candidates = []
            for candidate in result.get("candidates", []):
                # midterm meta에 매매 가이드 정보 추가 (중기 전략: 10% 목표, 15일 보유)
                meta = candidate.get("meta", {})
                if not isinstance(meta, dict):
                    meta = {}
                
                flags = meta.get("flags", {})
                if not isinstance(flags, dict):
                    flags = {}
                
                flags.update({
                    "target_profit": 0.10,  # 10% 목표 수익률 (중기 전략)
                    "stop_loss": 0.07,  # 7% 손절 기준 (max_drawdown_level 참고)
                    "holding_period": 15  # 15일 보유 기간 (중간값)
                })
                
                meta["flags"] = flags
                
                candidates.append({
                    "code": candidate.get("code"),
                    "name": None,  # midterm은 name을 반환하지 않음
                    "score": candidate.get("score"),
                    "rank": candidate.get("rank"),
                    "indicators": candidate.get("indicators", {}),
                    "meta": meta,  # 매매 가이드 정보가 추가된 meta
                    "engine": "midterm"
                })
            
            return {
                "candidates": candidates,
                "diagnostics": result.get("diagnostics", {}),
                "cache_stats": result.get("cache_stats", {})
            }
        except Exception as e:
            logger.error(f"Midterm 엔진 실행 실패: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "candidates": [],
                "diagnostics": {},
                "cache_stats": {},
                "error": str(e)
            }
    
    def _run_v2_lite(self, universe: List[str], date: str) -> Dict[str, Any]:
        """
        V2-Lite 엔진 실행
        
        Args:
            universe: 유니버스 종목 리스트
            date: 스캔 날짜
        
        Returns:
            v2-lite 스캔 결과
        """
        try:
            # scanner_v2_lite는 lazy import를 사용하므로 직접 경로에서 import
            from scanner_v2_lite.core.scanner import ScannerV2Lite
            from scanner_v2_lite.config_v2_lite import ScannerV2LiteConfig
            
            config = ScannerV2LiteConfig()
            scanner = ScannerV2Lite(config)
            
            # v2-lite는 market_condition 없이 실행 (레짐 분석 미사용)
            results = scanner.scan(universe, date)
            
            # ScanResultLite를 표준 형식으로 변환
            candidates = []
            for result in results:
                # v2_lite flags에 매매 가이드 정보 추가 (눌림목 전략: 2주 이내 +5%)
                flags = result.flags.copy() if hasattr(result, 'flags') and isinstance(result.flags, dict) else {}
                flags.update({
                    "target_profit": 0.05,  # 5% 목표 수익률
                    "stop_loss": 0.02,  # 2% 손절 기준
                    "holding_period": 14  # 2주 보유 기간
                })
                
                candidates.append({
                    "code": result.ticker,
                    "name": result.name,
                    "score": None,  # v2-lite는 score 미사용
                    "rank": None,
                    "indicators": result.indicators if hasattr(result, 'indicators') else {},
                    "meta": {
                        "match": result.match,
                        "strategy": result.strategy,
                        "trend": result.trend,
                        "flags": flags,  # 매매 가이드 정보가 추가된 flags
                        "score_label": result.score_label
                    },
                    "engine": "v2_lite"
                })
            
            return {
                "enabled": True,
                "candidates": candidates
            }
        except Exception as e:
            logger.error(f"V2-Lite 엔진 실행 실패: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "enabled": True,  # 실행 시도는 했지만 실패
                "candidates": [],
                "error": str(e)
            }






















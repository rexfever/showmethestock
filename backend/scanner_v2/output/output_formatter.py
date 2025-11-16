from __future__ import annotations

"""
scanner_v2.output.output_formatter

market_integrator 결과를 최종 사용자/외부 API에서 사용하기 쉬운 형태로 정리.
"""

from typing import Any, Dict, List


def format_scan_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    market_integrator에서 나온 결과 dict를 그대로 혹은 약간 정리하여 반환.

    각 후보는 다음 필드를 갖도록 정리한다:
      - symbol
      - horizon
      - score
      - risk_score
      - reason (초기에는 빈 문자열, 나중에 설명 문자열 추가 가능)
    """
    date = result.get("date")
    sentiment = result.get("market_sentiment", "neutral")

    def _wrap(horizon: str, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        wrapped: List[Dict[str, Any]] = []
        for x in items:
            if horizon == "swing":
                score_val = float(x.get("swing_score", 0.0))
            elif horizon == "position":
                score_val = float(x.get("position_score", 0.0))
            else:
                score_val = float(x.get("longterm_score", 0.0))
            wrapped.append(
                {
                    "symbol": x.get("symbol"),
                    "horizon": horizon,
                    "score": score_val,
                    "risk_score": float(x.get("risk_score", 0.0)),
                    "reason": "",
                }
            )
        return wrapped

    swing = _wrap("swing", result.get("swing_candidates", []))
    position = _wrap("position", result.get("position_candidates", []))
    longterm = _wrap("longterm", result.get("longterm_candidates", []))

    return {
        "date": date,
        "market_sentiment": sentiment,
        "swing_candidates": swing,
        "position_candidates": position,
        "longterm_candidates": longterm,
    }



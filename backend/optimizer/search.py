"""
Random search optimizer for the ScreenerV2 parameters.
"""
from __future__ import annotations

import random
from typing import Dict, List, Optional, Sequence

from backtester.engine import calculate_metrics, run_backtest_for_universe
from screener_v2 import ScreenerParams

PARAM_SPACE = {
    "min_turnover_krw": (1_000_000_000, 5_000_000_000),
    "min_price": (1_000, 5_000),
    "overheat_rsi_tema": (70, 85),
    "overheat_vol_mult": (2.0, 4.0),
    "atr_pct_min": (1.0, 3.0),
    "atr_pct_max": (10.0, 15.0),
    "min_signals": (2, 4),
    "step0_min_score": (8, 10),
    "step2_min_score": (6, 8),
}


def _sample_param(name: str, bounds: Sequence[float], rng: random.Random) -> float:
    low, high = bounds
    if name in {"min_signals"}:
        return rng.randint(int(low), int(high))
    if name in {"step0_min_score", "step2_min_score", "min_price"}:
        return float(rng.randint(int(low), int(high)))
    return rng.uniform(float(low), float(high))


def sample_parameters(rng: Optional[random.Random] = None) -> Dict[str, float]:
    rng = rng or random.Random()
    params = {name: _sample_param(name, bounds, rng) for name, bounds in PARAM_SPACE.items()}
    if params["atr_pct_min"] >= params["atr_pct_max"]:
        params["atr_pct_min"], params["atr_pct_max"] = sorted([params["atr_pct_min"], params["atr_pct_max"]])
    return params


def random_search(
    universe: Sequence[str],
    start_date: str,
    end_date: str,
    *,
    price_cache: Optional[Dict[str, "pd.DataFrame"]] = None,
    samples: int = 20,
    hold_days: int = 5,
    exit_mode: str = "close",
    seed: Optional[int] = None,
) -> List[Dict]:
    """
    Run random search over the parameter space.
    """
    rng = random.Random(seed)
    candidates: List[Dict] = []

    for idx in range(samples):
        params_dict = sample_parameters(rng)
        params = ScreenerParams(
            min_turnover_krw=params_dict["min_turnover_krw"],
            min_price=params_dict["min_price"],
            overheat_rsi_tema=params_dict["overheat_rsi_tema"],
            overheat_vol_mult=params_dict["overheat_vol_mult"],
            atr_pct_min=params_dict["atr_pct_min"],
            atr_pct_max=params_dict["atr_pct_max"],
            min_signals=int(params_dict["min_signals"]),
            step0_min_score=params_dict["step0_min_score"],
            step2_min_score=params_dict["step2_min_score"],
        )

        trades = run_backtest_for_universe(
            universe,
            params,
            start_date,
            end_date,
            price_cache=price_cache,
            hold_days=hold_days,
            exit_mode=exit_mode,
        )
        metrics = calculate_metrics(trades)
        candidates.append(
            {
                "sample_index": idx + 1,
                "params": params.to_dict(),
                "metrics": metrics,
                "trade_count": metrics.get("total_trades", 0),
            }
        )

    candidates.sort(key=lambda x: x["metrics"].get("sharpe", 0), reverse=True)
    return candidates



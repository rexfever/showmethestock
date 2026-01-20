"""
End-to-end parameter optimization pipeline for ScreenerV2.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from backtester.engine import calculate_metrics, run_backtest_for_universe
from data_loader import load_price_data, load_price_panel, load_universe
from optimizer.search import PARAM_SPACE, random_search
from screener_v2 import ScreenerParams

RESULT_DIR = Path(__file__).resolve().parents[1] / "results" / "optimization"


def build_price_cache(
    universe: List[str],
    start_date: str,
    end_date: str,
) -> Dict[str, pd.DataFrame]:
    print(f"📥 Loading price data for {len(universe)} symbols...")
    cache = load_price_panel(universe, start_date, end_date)
    print(f"✅ Loaded {len(cache)} symbols with usable price history.")
    return cache


def select_best_candidate(candidates: List[Dict]) -> Optional[Dict]:
    for cand in candidates:
        metrics = cand["metrics"]
        if metrics.get("cagr", 0) >= 0.10 and metrics.get("mdd", 0) >= -35:
            return cand
    return candidates[0] if candidates else None


def export_results(
    candidates: List[Dict],
    best_candidate: Dict,
    test_metrics: Dict[str, float],
) -> None:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)

    rows = []
    for cand in candidates:
        row = {
            "sample_index": cand["sample_index"],
            **{f"param_{k}": v for k, v in cand["params"].items()},
            **{f"metric_{k}": v for k, v in cand["metrics"].items()},
        }
        rows.append(row)
    pd.DataFrame(rows).to_csv(RESULT_DIR / "all_candidates.csv", index=False)

    with open(RESULT_DIR / "best_parameters.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "params": best_candidate["params"],
                "train_metrics": best_candidate["metrics"],
                "test_metrics": test_metrics,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    md_lines = [
        "# Optimization Summary",
        "",
        "## Best Parameter Set",
        "",
        "```json",
        json.dumps(best_candidate["params"], indent=2),
        "```",
        "",
        "## Performance",
        "",
        "| Period | CAGR | Sharpe | MDD | Trades | Win Rate |",
        "| --- | --- | --- | --- | --- | --- |",
        f"| Train | {best_candidate['metrics']['cagr']:.2%} | {best_candidate['metrics']['sharpe']:.2f} | "
        f"{best_candidate['metrics']['mdd']:.2f}% | {best_candidate['metrics']['total_trades']} | "
        f"{best_candidate['metrics']['win_rate']:.2f}% |",
        f"| Test | {test_metrics['cagr']:.2%} | {test_metrics['sharpe']:.2f} | "
        f"{test_metrics['mdd']:.2f}% | {test_metrics['total_trades']} | "
        f"{test_metrics['win_rate']:.2f}% |",
        "",
        "## Notes",
        "",
        "- Optimization method: Random Search",
        "- Parameter space:",
        "```json",
        json.dumps(PARAM_SPACE, indent=2),
        "```",
    ]
    (RESULT_DIR / "final_summary.md").write_text("\n".join(md_lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Parameter optimization pipeline")
    parser.add_argument("--samples", type=int, default=20, help="Number of random samples")
    parser.add_argument("--universe-limit", type=int, default=200, help="Limit per market when loading universe")
    parser.add_argument("--exit-mode", choices=["close", "next_open"], default="close")
    parser.add_argument("--hold-days", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    train_start = "2022-11-01"
    train_end = "2024-12-31"
    test_start = "2025-01-01"
    test_end = "2025-10-31"

    print("📊 Loading universe...")
    universe = load_universe(limit_per_market=args.universe_limit)
    if not universe:
        raise RuntimeError("Universe is empty. Check data source.")
    print(f"✅ Universe size: {len(universe)} symbols")

    global_cache = build_price_cache(universe, train_start, test_end)

    print("🚀 Running random search...")
    candidates = random_search(
        universe,
        train_start,
        train_end,
        price_cache=global_cache,
        samples=args.samples,
        hold_days=args.hold_days,
        exit_mode=args.exit_mode,
        seed=args.seed,
    )
    if not candidates:
        raise RuntimeError("No candidates were generated.")

    best_candidate = select_best_candidate(candidates)
    if best_candidate is None:
        raise RuntimeError("Unable to select a best candidate.")

    best_params = ScreenerParams(**best_candidate["params"])
    print("📈 Evaluating best parameters on the test period...")
    test_trades = run_backtest_for_universe(
        universe,
        best_params,
        test_start,
        test_end,
        price_cache=global_cache,
        hold_days=args.hold_days,
        exit_mode=args.exit_mode,
    )
    test_metrics = calculate_metrics(test_trades)

    export_results(candidates, best_candidate, test_metrics)
    print(f"✅ Results saved to {RESULT_DIR}")


if __name__ == "__main__":
    main()



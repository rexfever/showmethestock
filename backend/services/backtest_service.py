"""
Backtest service for scanner performance evaluation.
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from date_helper import is_trading_day_kr, yyyymmdd_to_date
from kiwoom_api import api
from config import config
from services.recommendation_service import get_nth_trading_day_after

logger = logging.getLogger(__name__)

HOLDING_WINDOWS = [5, 10, 20, 30]


def _get_trading_days(start_date: str, end_date: str) -> List[str]:
    start = yyyymmdd_to_date(start_date)
    end = yyyymmdd_to_date(end_date)
    days = []
    current = start
    while current <= end:
        if is_trading_day_kr(current.strftime("%Y%m%d")):
            days.append(current.strftime("%Y%m%d"))
        current += timedelta(days=1)
    return days


def _get_universe() -> List[str]:
    kospi = api.get_top_codes("KOSPI", config.universe_kospi)
    kosdaq = api.get_top_codes("KOSDAQ", config.universe_kosdaq)
    return [*kospi, *kosdaq]


def _get_ohlcv_strict(ticker: str, count: int, base_dt: str) -> Dict:
    df = api.get_ohlcv(ticker, count, base_dt)
    leak_detected = bool(getattr(api, "_last_ohlcv_leak", False))
    if not df.empty and "date" in df.columns:
        df["date_str"] = df["date"].astype(str).str.replace("-", "").str[:8]
        df = df[df["date_str"] <= base_dt].copy()
        df = df.sort_values("date_str").reset_index(drop=True)
        df = df.drop(columns=["date_str"])
    return {"df": df, "leak": leak_detected}


def _get_anchor_close(ticker: str, anchor_date: str) -> Optional[float]:
    result = _get_ohlcv_strict(ticker, 1, anchor_date)
    df = result["df"]
    if df.empty:
        return None
    return float(df.iloc[-1]["close"])


def _scan_v3(universe: List[str], scan_date: str, strategy_filter: Optional[str] = None) -> List[Dict]:
    from scanner_v3 import ScannerV3

    scanner = ScannerV3()
    v3_result = scanner.scan(universe, scan_date)
    items = []
    for candidate in v3_result.get("results", {}).get("midterm", {}).get("candidates", []):
        if strategy_filter and strategy_filter != "midterm":
            continue
        items.append({
            "ticker": candidate.get("code"),
            "strategy": "midterm"
        })
    for candidate in v3_result.get("results", {}).get("v2_lite", {}).get("candidates", []):
        if strategy_filter and strategy_filter != "v2_lite":
            continue
        items.append({
            "ticker": candidate.get("code"),
            "strategy": "v2_lite"
        })
    return items


def _scan_v2(universe: List[str], scan_date: str) -> List[Dict]:
    from scanner_factory import scan_with_scanner

    results = scan_with_scanner(universe, None, scan_date, None, version="v2")
    items = []
    for item in results:
        items.append({
            "ticker": item.get("ticker"),
            "strategy": item.get("strategy")
        })
    return items


def _get_prices_window(ticker: str, start_date: str, end_date: str) -> Dict:
    start = yyyymmdd_to_date(start_date)
    end = yyyymmdd_to_date(end_date)
    days = (end - start).days + 5
    result = _get_ohlcv_strict(ticker, max(days, 5), end_date)
    df = result["df"]
    if df.empty:
        return {"df": df, "leak": result["leak"]}
    df["date_str"] = df["date"].astype(str).str.replace("-", "").str[:8]
    df = df[(df["date_str"] >= start_date) & (df["date_str"] <= end_date)].copy()
    df = df.sort_values("date_str").reset_index(drop=True)
    df = df.drop(columns=["date_str"])
    return {"df": df, "leak": result["leak"]}


def _evaluate_v2(items: List[Dict]) -> Dict:
    results = {}
    leak_samples = []
    for item in items:
        ticker = item.get("ticker")
        strategy = item.get("strategy") or "unknown"
        scan_date = item.get("scan_date")
        if not ticker:
            continue
        if not scan_date:
            continue
        anchor_close = _get_anchor_close(ticker, scan_date)
        if anchor_close is None or anchor_close <= 0:
            continue
        if strategy not in results:
            results[strategy] = {window: {"count": 0, "max_returns": [], "min_returns": []} for window in HOLDING_WINDOWS}
        for window in HOLDING_WINDOWS:
            end_date = get_nth_trading_day_after(scan_date, window)
            if not end_date:
                continue
            window_data = _get_prices_window(ticker, scan_date, end_date)
            if window_data["leak"]:
                leak_samples.append({"ticker": ticker, "date": end_date})
            df = window_data["df"]
            if df.empty:
                continue
            closes = df["close"].astype(float).tolist()
            max_return = ((max(closes) - anchor_close) / anchor_close) * 100
            min_return = ((min(closes) - anchor_close) / anchor_close) * 100
            bucket = results[strategy][window]
            bucket["count"] += 1
            bucket["max_returns"].append(round(max_return, 2))
            bucket["min_returns"].append(round(min_return, 2))
    summary = {}
    for strategy, windows in results.items():
        summary[strategy] = {}
        for window, data in windows.items():
            if data["count"] == 0:
                summary[strategy][str(window)] = {"count": 0}
                continue
            summary[strategy][str(window)] = {
                "count": data["count"],
                "avg_max_return": round(sum(data["max_returns"]) / data["count"], 2),
                "avg_min_return": round(sum(data["min_returns"]) / data["count"], 2),
                "max_of_max": max(data["max_returns"]),
                "min_of_min": min(data["min_returns"]),
            }
    return {"summary": summary, "leak_samples": leak_samples}


def _get_v3_policy(strategy: str) -> Dict:
    if strategy == "v2_lite":
        return {"ttl_days": 15, "stop_loss": 0.02}
    if strategy == "midterm":
        return {"ttl_days": 25, "stop_loss": 0.07}
    return {"ttl_days": 20, "stop_loss": 0.02}


def _evaluate_v3(items: List[Dict]) -> Dict:
    results = {}
    leak_samples = []
    for item in items:
        ticker = item.get("ticker")
        strategy = item.get("strategy") or "unknown"
        scan_date = item.get("scan_date")
        if not ticker:
            continue
        if not scan_date:
            continue
        policy = _get_v3_policy(strategy)
        ttl_days = policy["ttl_days"]
        stop_loss_pct = -abs(float(policy["stop_loss"]) * 100)
        ttl_expiry = get_nth_trading_day_after(scan_date, ttl_days)
        if not ttl_expiry:
            continue
        anchor_close = _get_anchor_close(ticker, scan_date)
        if anchor_close is None or anchor_close <= 0:
            continue
        window_data = _get_prices_window(ticker, scan_date, ttl_expiry)
        if window_data["leak"]:
            leak_samples.append({"ticker": ticker, "date": ttl_expiry})
        df = window_data["df"]
        if df.empty:
            continue
        broken = False
        max_return = None
        min_return = None
        final_return = None
        for _, row in df.iterrows():
            day_close = float(row["close"])
            day_return = ((day_close - anchor_close) / anchor_close) * 100
            if max_return is None or day_return > max_return:
                max_return = day_return
            if min_return is None or day_return < min_return:
                min_return = day_return
            if day_return <= stop_loss_pct:
                broken = True
                break
        if not broken:
            final_return = ((float(df.iloc[-1]["close"]) - anchor_close) / anchor_close) * 100
        if strategy not in results:
            results[strategy] = {
                "broken_count": 0,
                "non_broken_count": 0,
                "non_broken_max_returns": [],
                "non_broken_min_returns": [],
                "non_broken_final_returns": []
            }
        if broken:
            results[strategy]["broken_count"] += 1
        else:
            results[strategy]["non_broken_count"] += 1
            results[strategy]["non_broken_max_returns"].append(round(max_return, 2))
            results[strategy]["non_broken_min_returns"].append(round(min_return, 2))
            results[strategy]["non_broken_final_returns"].append(round(final_return, 2))
    summary = {}
    for strategy, data in results.items():
        non_broken_count = data["non_broken_count"]
        summary[strategy] = {
            "broken_count": data["broken_count"],
            "ttl_count": non_broken_count,
            "non_broken_count": non_broken_count
        }
        if non_broken_count > 0:
            summary[strategy].update({
                "avg_max_return": round(sum(data["non_broken_max_returns"]) / non_broken_count, 2),
                "avg_min_return": round(sum(data["non_broken_min_returns"]) / non_broken_count, 2),
                "avg_final_return": round(sum(data["non_broken_final_returns"]) / non_broken_count, 2),
                "max_of_max": max(data["non_broken_max_returns"]),
                "min_of_min": min(data["non_broken_min_returns"]),
            })
    return {"summary": summary, "leak_samples": leak_samples}


def run_backtest(scanner: str, start_date: str, end_date: str) -> Dict:
    trading_days = _get_trading_days(start_date, end_date)
    universe = _get_universe()
    all_items = []
    leak_samples = []
    for day in trading_days:
        if scanner in ["v3", "v3_midterm", "v3_v2_lite"]:
            strategy_filter = None
            if scanner == "v3_midterm":
                strategy_filter = "midterm"
            elif scanner == "v3_v2_lite":
                strategy_filter = "v2_lite"
            items = _scan_v3(universe, day, strategy_filter=strategy_filter)
        elif scanner == "v2":
            items = _scan_v2(universe, day)
        else:
            raise ValueError(f"unsupported scanner: {scanner}")
        for item in items:
            all_items.append({"ticker": item.get("ticker"), "strategy": item.get("strategy"), "scan_date": day})
    if scanner == "v2":
        v2_eval = _evaluate_v2(all_items)
        leak_samples.extend(v2_eval["leak_samples"])
        return {
            "scanner": scanner,
            "period": {"start_date": start_date, "end_date": end_date},
            "total_recommendations": len(all_items),
            "evaluation": {"v2": v2_eval["summary"]},
            "ohlcv_leak_detected": bool(leak_samples),
            "ohlcv_leak_samples": leak_samples
        }
    v3_eval = _evaluate_v3(all_items)
    leak_samples.extend(v3_eval["leak_samples"])
    return {
        "scanner": scanner,
        "period": {"start_date": start_date, "end_date": end_date},
        "total_recommendations": len(all_items),
        "evaluation": {"v3": v3_eval["summary"]},
        "ohlcv_leak_detected": bool(leak_samples),
        "ohlcv_leak_samples": leak_samples
    }


def write_backtest_report(scanner: str, start_date: str, end_date: str, output_path: str) -> str:
    report = run_backtest(scanner, start_date, end_date)
    report["generated_at"] = datetime.now().isoformat()
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return output_path

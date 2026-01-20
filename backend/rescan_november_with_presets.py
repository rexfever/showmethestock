#!/usr/bin/env python3
"""
Rescan for November 2025 using market-specific presets with REAL Kiwoom API.

This script rebuilds raw scan candidates for each trading day where we have
stored market conditions (2025-11-03, 06, 12, 13).  It uses the actual Kiwoom
REST API to fetch OHLCV data, captures every preset step (Step0~Step3), and
evaluates the resulting recommendations through 2025-11-15.

Outputs:
  - backend/rescan_outputs/rescan-YYYYMMDD.json : raw candidates per step
  - backend/rescan_outputs/summary-202511.json  : consolidated metrics
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any

import FinanceDataReader as fdr
import pandas as pd
import numpy as np
from datetime import datetime
import holidays

# --- Environment prep: ensure wide universe even on local profile -----------
os.environ.setdefault("SKIP_DB_PATCH", "1")
os.environ.setdefault("UNIVERSE_KOSPI", "100")
os.environ.setdefault("UNIVERSE_KOSDAQ", "100")

from config import config  # noqa: E402  (after env vars)
from db_manager import db_manager  # noqa: E402
from market_analyzer import MarketCondition  # noqa: E402
from scanner import scan_with_preset  # noqa: E402
import kiwoom_api  # noqa: E402

# --------------------------------------------------------------------------- #
# Constants

# 11월 전체 거래일 자동 생성
def get_november_trading_days():
    kr_holidays = holidays.SouthKorea()
    trading_days = []
    start = datetime(2025, 11, 1)
    end = datetime(2025, 11, 30)
    current = start
    while current <= end:
        # 주말(토일) 및 공휴일 제외
        if current.weekday() < 5 and current not in kr_holidays:
            trading_days.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    return trading_days

TARGET_DATES = get_november_trading_days()
TURNOVER_WINDOW = 20
KOSPI_POOL = 400
KOSDAQ_POOL = 400
DATA_START = "2024-12-01"
DATA_END = "2025-11-30"
ANALYSIS_END = "20251115"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "rescan_outputs")


# --------------------------------------------------------------------------- #
# Helpers

def ensure_output_dir() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)


class PriceCache:
    """Lazy OHLCV cache backed by FinanceDataReader with basic memoisation."""

    def __init__(self, start: str, end: str):
        self.start = start
        self.end = end
        self._data: Dict[str, pd.DataFrame] = {}

    def has(self, code: str) -> bool:
        return code in self._data

    def load(self, code: str) -> None:
        if code in self._data:
            return
        try:
            df = fdr.DataReader(code, self.start, self.end)
        except Exception as exc:  # pragma: no cover - external dependency
            print(f"⚠️  {code} FDR 조회 실패: {exc}")
            self._data[code] = pd.DataFrame()
            return

        if df.empty:
            self._data[code] = df
            return

        df = df.rename(
            columns={
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume",
            }
        )
        df = df[["open", "high", "low", "close", "volume"]].copy()
        df = df.dropna()
        df["date"] = df.index.strftime("%Y%m%d")
        df = df.reset_index(drop=True)
        self._data[code] = df

    def get(self, code: str) -> pd.DataFrame:
        if code not in self._data:
            self.load(code)
        return self._data.get(code, pd.DataFrame())


# OfflineKiwoomAPI 클래스 제거 - 실제 Kiwoom API 사용


def load_listing() -> pd.DataFrame:
    listing = fdr.StockListing("KRX")
    listing = listing[listing["Market"].isin(["KOSPI", "KOSDAQ"])].copy()
    listing = listing[listing["Code"].str.len() == 6]
    listing["Marcap"] = pd.to_numeric(listing["Marcap"], errors="coerce")
    listing = listing.dropna(subset=["Marcap"])
    return listing


def preselect_codes(listing: pd.DataFrame) -> Dict[str, List[str]]:
    pools = {"KOSPI": KOSPI_POOL, "KOSDAQ": KOSDAQ_POOL}
    selected: Dict[str, List[str]] = {}
    for market, pool in pools.items():
        subset = listing[listing["Market"] == market]
        top_codes = subset.nlargest(pool, "Marcap")["Code"].tolist()
        selected[market] = top_codes
    return selected


def warm_cache(codes: List[str], cache: PriceCache) -> None:
    for idx, code in enumerate(codes, start=1):
        cache.load(code)
        if idx % 50 == 0:
            print(f"  ↳ OHLCV 미리 로드 {idx}/{len(codes)}")


def build_universe(
    date_compact: str,
    market: str,
    candidate_codes: List[str],
    cache: PriceCache,
    top_n: int,
) -> List[str]:
    metrics: List[Tuple[str, float]] = []
    for code in candidate_codes:
        df = cache.get(code)
        if df.empty:
            continue
        window = df[df["date"] <= date_compact].tail(TURNOVER_WINDOW)
        if len(window) < TURNOVER_WINDOW:
            continue
        turnover = float((window["close"] * window["volume"]).mean())
        if turnover <= 0 or pd.isna(turnover):
            continue
        metrics.append((code, turnover))

    metrics.sort(key=lambda x: x[1], reverse=True)
    selected = [code for code, _ in metrics[:top_n]]
    print(
        f"  ↳ {market} 유니버스 {len(selected)}/{top_n} (후보 {len(candidate_codes)}) "
        f"평균 거래대금 상위"
    )
    return selected


def fetch_market_condition(date_compact: str) -> MarketCondition:
    query = """
        SELECT date, market_sentiment, kospi_return, volatility,
               rsi_threshold, min_signals, macd_osc_min, vol_ma5_mult,
               gap_max, ext_from_tema20_max, sector_rotation, foreign_flow,
               volume_trend, sentiment_score, trend_metrics, breadth_metrics,
               flow_metrics, sector_metrics, volatility_metrics,
               foreign_flow_label, volume_trend_label, adjusted_params,
               analysis_notes
        FROM market_conditions
        WHERE date = %s
    """
    with db_manager.get_cursor(commit=False) as cur:
        cur.execute(query, (date_compact,))
        row = cur.fetchone()
        cols = [desc.name for desc in cur.description]

    if not row:
        return MarketCondition(
            date=date_compact,
            kospi_return=0.0,
            volatility=0.03,
            market_sentiment="neutral",
            sector_rotation="mixed",
            foreign_flow="neutral",
            institution_flow="neutral",
            volume_trend="normal",
            rsi_threshold=config.rsi_threshold,
            min_signals=config.min_signals,
            macd_osc_min=config.macd_osc_min,
            vol_ma5_mult=config.vol_ma5_mult,
            gap_max=config.gap_max,
            ext_from_tema20_max=config.ext_from_tema20_max,
        )

    data = dict(zip(cols, row))
    flow_metrics = data.get("flow_metrics") or {}
    inst_flow = "neutral"
    if isinstance(flow_metrics, dict):
        inst_flow = flow_metrics.get("institution_flow_raw") or "neutral"

    return MarketCondition(
        date=date_compact,
        kospi_return=float(data.get("kospi_return") or 0.0),
        volatility=float(data.get("volatility") or 0.0),
        market_sentiment=(data.get("market_sentiment") or "neutral"),
        sector_rotation=data.get("sector_rotation") or "mixed",
        foreign_flow=data.get("foreign_flow") or "neutral",
        institution_flow=inst_flow,
        volume_trend=data.get("volume_trend") or "normal",
        rsi_threshold=float(data.get("rsi_threshold") or config.rsi_threshold),
        min_signals=int(data.get("min_signals") or config.min_signals),
        macd_osc_min=float(data.get("macd_osc_min") or config.macd_osc_min),
        vol_ma5_mult=float(data.get("vol_ma5_mult") or config.vol_ma5_mult),
        gap_max=float(data.get("gap_max") or config.gap_max),
        ext_from_tema20_max=float(
            data.get("ext_from_tema20_max") or config.ext_from_tema20_max
        ),
        sentiment_score=float(data.get("sentiment_score") or 0.0),
        trend_metrics=data.get("trend_metrics") or {},
        breadth_metrics=data.get("breadth_metrics") or {},
        flow_metrics=flow_metrics,
        sector_metrics=data.get("sector_metrics") or {},
        volatility_metrics=data.get("volatility_metrics") or {},
        foreign_flow_label=data.get("foreign_flow_label")
        or (data.get("foreign_flow") or "neutral"),
        institution_flow_label=inst_flow,
        volume_trend_label=data.get("volume_trend_label")
        or (data.get("volume_trend") or "normal"),
        adjusted_params=data.get("adjusted_params") or {},
        analysis_notes=data.get("analysis_notes"),
    )


def sanitize_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Convert numpy/pandas dtypes into native Python types for JSON dumps."""
    def _convert(value):
        if isinstance(value, (pd.Timestamp,)):
            return value.strftime("%Y-%m-%d")
        if isinstance(value, (pd.Series, pd.DataFrame)):
            return value.to_dict()
        if isinstance(value, np.generic):
            return value.item()
        if hasattr(value, "item"):
            try:
                return value.item()
            except Exception:  # pragma: no cover - fallback
                return value
        if isinstance(value, dict):
            return {k: _convert(v) for k, v in value.items()}
        if isinstance(value, list):
            return [_convert(v) for v in value]
        return value

    return {k: _convert(v) for k, v in item.items()}


def json_default(obj):
    if isinstance(obj, (pd.Timestamp, datetime)):
        return obj.strftime("%Y-%m-%d")
    if isinstance(obj, np.generic):
        return obj.item()
    if isinstance(obj, set):
        return list(obj)
    raise TypeError(f"Type {type(obj)} not serializable")


def scan_with_steps(
    universe: List[str],
    date_compact: str,
    market_condition: MarketCondition,
) -> Tuple[List[Dict[str, Any]], int, Dict[str, Dict[str, Any]]]:
    """Replicates execute_scan_with_fallback while capturing raw step outputs."""
    if market_condition and market_condition.market_sentiment == "crash":
        return [], None, {}

    profile = config.get_fallback_profile(
        market_condition.market_sentiment if market_condition else "neutral"
    )
    target_min = max(1, profile.get("target_min", config.fallback_target_min))
    target_max = max(target_min, profile.get("target_max", config.fallback_target_max))
    presets = profile.get("presets", config.fallback_presets)

    step_payloads: Dict[str, Dict[str, Any]] = {}

    def _record(step_idx: int, preset: Dict[str, Any], items: List[Dict[str, Any]]):
        step_payloads[str(step_idx)] = {
            "preset": preset or {},
            "items": [sanitize_item(it) for it in items],
        }

    # Step 0
    step0 = scan_with_preset(universe, {}, date_compact, market_condition)
    items_10 = [it for it in step0 if it.get("score", 0) >= 10]
    _record(0, {}, step0)
    if len(items_10) >= target_min:
        return items_10[: target_max], 0, step_payloads

    if len(presets) < 2:
        return [], None, step_payloads

    # Step 1 preset (indicator relax but still >=10점)
    step1 = scan_with_preset(universe, presets[1], date_compact, market_condition)
    _record(1, presets[1], step1)
    step1_10 = [it for it in step1 if it.get("score", 0) >= 10]
    if len(step1_10) >= target_min:
        return step1_10[: target_max], 1, step_payloads

    # Step 2: indicator relax + >=8점
    step1_8 = [it for it in step1 if it.get("score", 0) >= 8]
    step_payloads["2"] = {
        "preset": presets[1],
        "items": [sanitize_item(it) for it in step1_8],
    }
    if len(step1_8) >= target_min:
        return step1_8[: target_max], 2, step_payloads

    # Step 3: next preset (if available) + >=8점
    if len(presets) < 3:
        return [], None, step_payloads
    step3 = scan_with_preset(universe, presets[2], date_compact, market_condition)
    step3_8 = [it for it in step3 if it.get("score", 0) >= 8]
    _record(3, presets[2], step3)
    if len(step3_8) >= target_min:
        return step3_8[: target_max], 3, step_payloads

    return [], None, step_payloads


def evaluate_returns(
    final_items: List[Dict[str, Any]],
    price_cache: PriceCache,
    analysis_end: str,
) -> List[Dict[str, Any]]:
    """Attach return metrics using cached OHLCV data."""
    enriched = []
    for item in final_items:
        code = item["ticker"]
        date = item.get("date") or item.get("scan_date")
        if not date:
            continue
        df = price_cache.get(code)
        if df.empty:
            continue
        segment = df[(df["date"] >= date) & (df["date"] <= analysis_end)]
        if segment.empty:
            continue
        buy = segment.iloc[0]
        buy_price = float(buy["close"])
        current_close = float(segment.iloc[-1]["close"])
        max_high = float(segment["high"].max())
        min_low = float(segment["low"].min())
        days = len(segment)
        current_ret = (current_close - buy_price) / buy_price * 100
        max_ret = (max_high - buy_price) / buy_price * 100
        min_ret = (min_low - buy_price) / buy_price * 100

        enriched.append(
            {
                **item,
                "buy_price": round(buy_price, 2),
                "current_return": round(current_ret, 2),
                "max_return": round(max_ret, 2),
                "min_return": round(min_ret, 2),
                "days_elapsed": days,
            }
        )
    return enriched


def classify_status(entry: Dict[str, Any]) -> str:
    current = entry.get("current_return", 0) or 0.0
    max_ret = entry.get("max_return", 0) or 0.0
    min_ret = entry.get("min_return", 0) or 0.0
    days = entry.get("days_elapsed", 0) or 0

    if max_ret >= 3.0:
        return "take_profit"
    if days >= 5 and min_ret <= -7.0:
        return "stop_loss"
    if max_ret >= 1.5 and current <= 0:
        return "preserve"
    if days >= 45:
        return "expired"
    return "ongoing"


def main():
    ensure_output_dir()
    
    # 실제 Kiwoom API 사용 - 유니버스 구성을 위한 listing만 FDR 활용
    listing = load_listing()
    candidate_pool = preselect_codes(listing)
    
    # Kiwoom API는 그대로 사용 (패치 없음)
    print("✅ 실제 Kiwoom REST API 사용")

    summary_rows = []
    enriched_overall: List[Dict[str, Any]] = []

    for date_str in TARGET_DATES:
        date_compact = date_str.replace("-", "")
        print(f"\n🗓️  {date_str} 스캔 시작")
        mc = fetch_market_condition(date_compact)
        print(f"   시장 센티먼트: {mc.market_sentiment}")

        # Kiwoom API로 직접 유니버스 구성
        from kiwoom_api import api as real_api
        kospi_universe = real_api.get_top_codes("KOSPI", config.universe_kospi)
        kosdaq_universe = real_api.get_top_codes("KOSDAQ", config.universe_kosdaq)
        universe = kospi_universe + kosdaq_universe
        print(f"  ↳ KOSPI {len(kospi_universe)}개 + KOSDAQ {len(kosdaq_universe)}개 = 총 {len(universe)}개")

        final_items, chosen_step, step_payloads = scan_with_steps(
            universe, date_compact, mc
        )

        for it in final_items:
            it["date"] = date_compact

        # FinanceDataReader로 수익률 계산 (Kiwoom API는 과거 데이터 조회 제약)
        cache = PriceCache(DATA_START, DATA_END)
        for code in [it["ticker"] for it in final_items]:
            if not cache.has(code):
                cache.load(code)
        enriched_final = evaluate_returns(final_items, cache, ANALYSIS_END)
        for entry in enriched_final:
            entry["status"] = classify_status(entry)
        enriched_overall.extend(enriched_final)

        payload = {
            "date": date_compact,
            "market_sentiment": mc.market_sentiment,
            "fallback_profile": config.get_fallback_profile(mc.market_sentiment),
            "chosen_step": chosen_step,
            "universe_count": len(universe),
            "steps": step_payloads,
            "final_items": [sanitize_item(it) for it in final_items],
            "enriched_final": enriched_final,
        }

        output_path = os.path.join(OUTPUT_DIR, f"rescan-{date_compact}.json")
        with open(output_path, "w", encoding="utf-8") as fp:
            json.dump(payload, fp, ensure_ascii=False, indent=2, default=json_default)
        print(f"   ✅ 저장 완료: {output_path}")

        summary_rows.append(
            {
                "date": date_compact,
                "sentiment": mc.market_sentiment,
                "universe": len(universe),
                "final_count": len(final_items),
                "chosen_step": chosen_step,
            }
        )

    # Aggregate performance
    total = len(enriched_overall)
    win = sum(1 for e in enriched_overall if e["status"] in ("take_profit", "preserve"))
    avg_return = (
        sum(e["current_return"] for e in enriched_overall) / total if total else 0.0
    )
    status_counts = {}
    for e in enriched_overall:
        status_counts[e["status"]] = status_counts.get(e["status"], 0) + 1

    summary = {
        "generated_at": datetime.now().isoformat(),
        "analysis_end": ANALYSIS_END,
        "total_picks": total,
        "win_rate": round((win / total * 100) if total else 0.0, 2),
        "avg_current_return": round(avg_return, 2),
        "status_counts": status_counts,
        "daily": summary_rows,
    }

    summary_path = os.path.join(OUTPUT_DIR, "summary-202511.json")
    with open(summary_path, "w", encoding="utf-8") as fp:
        json.dump(summary, fp, ensure_ascii=False, indent=2, default=json_default)
    print(f"\n📊 요약 저장: {summary_path}")
    print(
        f"총 {total}건 | 승률 {summary['win_rate']}% | 평균 수익률 {summary['avg_current_return']}%"
    )


if __name__ == "__main__":
    main()


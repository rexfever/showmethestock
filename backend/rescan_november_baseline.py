#!/usr/bin/env python3
"""
Baseline rescan for November 2025 WITHOUT market-specific presets.

This script runs the scanner with default config settings only (no fallback),
to see how many stocks would be selected under the original tight conditions.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any

import FinanceDataReader as fdr
import pandas as pd
import numpy as np
import holidays

# --- Environment prep
os.environ.setdefault("SKIP_DB_PATCH", "1")
os.environ.setdefault("UNIVERSE_KOSPI", "100")
os.environ.setdefault("UNIVERSE_KOSDAQ", "100")

from config import config  # noqa: E402
from db_manager import db_manager  # noqa: E402
from market_analyzer import MarketCondition  # noqa: E402
from scanner import scan_with_preset  # noqa: E402

# --------------------------------------------------------------------------- #
# Constants

def get_november_trading_days():
    kr_holidays = holidays.SouthKorea()
    trading_days = []
    start = datetime(2025, 11, 1)
    end = datetime(2025, 11, 30)
    current = start
    while current <= end:
        if current.weekday() < 5 and current not in kr_holidays:
            trading_days.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    return trading_days

TARGET_DATES = get_november_trading_days()
DATA_START = "2024-12-01"
DATA_END = "2025-11-30"
ANALYSIS_END = "20251115"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "rescan_outputs_baseline_200")


# --------------------------------------------------------------------------- #
# Helpers

def ensure_output_dir() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)


class PriceCache:
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
        except Exception as exc:
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


def fetch_market_condition(date_compact: str) -> MarketCondition:
    query = """
        SELECT date, market_sentiment, kospi_return, volatility,
               rsi_threshold, min_signals, macd_osc_min, vol_ma5_mult,
               gap_max, ext_from_tema20_max, sector_rotation, foreign_flow,
               volume_trend
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
    return MarketCondition(
        date=date_compact,
        kospi_return=float(data.get("kospi_return") or 0.0),
        volatility=float(data.get("volatility") or 0.0),
        market_sentiment=(data.get("market_sentiment") or "neutral"),
        sector_rotation=data.get("sector_rotation") or "mixed",
        foreign_flow=data.get("foreign_flow") or "neutral",
        institution_flow="neutral",
        volume_trend=data.get("volume_trend") or "normal",
        rsi_threshold=float(data.get("rsi_threshold") or config.rsi_threshold),
        min_signals=int(data.get("min_signals") or config.min_signals),
        macd_osc_min=float(data.get("macd_osc_min") or config.macd_osc_min),
        vol_ma5_mult=float(data.get("vol_ma5_mult") or config.vol_ma5_mult),
        gap_max=float(data.get("gap_max") or config.gap_max),
        ext_from_tema20_max=float(
            data.get("ext_from_tema20_max") or config.ext_from_tema20_max
        ),
    )


def sanitize_item(item: Dict[str, Any]) -> Dict[str, Any]:
    def _convert(value):
        if isinstance(value, (np.integer, np.floating)):
            return value.item()
        if hasattr(value, "item"):
            try:
                return value.item()
            except Exception:
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


def evaluate_returns(
    final_items: List[Dict[str, Any]],
    price_cache: PriceCache,
    analysis_end: str,
) -> List[Dict[str, Any]]:
    enriched = []
    for item in final_items:
        code = item["ticker"]
        date = item.get("date") or item.get("scan_date")
        if not date:
            continue
        df = price_cache.get(code)
        if df.empty:
            continue

        buy_row = df[df["date"] == date]
        if buy_row.empty:
            continue
        buy_price = float(buy_row.iloc[0]["close"])

        future = df[df["date"] > date]
        if future.empty:
            continue

        current_close = float(future.iloc[-1]["close"])
        max_high = float(future["high"].max())
        min_low = float(future["low"].min())
        days_elapsed = len(future)

        current_return = round((current_close - buy_price) / buy_price * 100, 2)
        max_return = round((max_high - buy_price) / buy_price * 100, 2)
        min_return = round((min_low - buy_price) / buy_price * 100, 2)

        enriched.append({
            **item,
            "buy_price": buy_price,
            "current_return": current_return,
            "max_return": max_return,
            "min_return": min_return,
            "days_elapsed": days_elapsed,
        })

    return enriched


def classify_status(entry: Dict[str, Any]) -> str:
    days = entry.get("days_elapsed", 0) or 0
    max_ret = entry.get("max_return", 0) or 0
    min_ret = entry.get("min_return", 0) or 0
    current = entry.get("current_return", 0) or 0

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
    
    print("✅ 기본 조건 + 8점 이상 Fallback (유니버스 200개)")
    print(f"   - KOSPI: {config.universe_kospi}개")
    print(f"   - KOSDAQ: {config.universe_kosdaq}개")
    print(f"   - min_signals: {config.min_signals}")
    print(f"   - vol_ma5_mult: {config.vol_ma5_mult}")
    print(f"   - 선정 기준: 10점 우선 → 없으면 8점 이상")

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

        # 기본 조건만으로 스캔 (프리셋 없음)
        items = scan_with_preset(universe, {}, date_compact, mc)
        
        # 점수 필터링: 10점 우선, 없으면 8점 이상 (Fallback 로직 반영)
        items_10 = [it for it in items if it.get("score", 0) >= 10]
        items_8 = [it for it in items if it.get("score", 0) >= 8]
        
        if items_10:
            final_items = items_10[:5]  # 10점 이상이 있으면 최대 5개
            selection_note = f"{len(items_10)}개 (10점 이상)"
        elif items_8:
            final_items = items_8[:5]  # 10점이 없으면 8점 이상으로 Fallback
            selection_note = f"{len(items_8)}개 (8점 이상 Fallback)"
        else:
            final_items = []
            selection_note = "0개"
        
        print(f"📊 스캔 결과: {len(items)}개 전체 매칭 → {selection_note} 최종 선정")

        for it in final_items:
            it["date"] = date_compact

        # FinanceDataReader로 수익률 계산
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
            "baseline_config": {
                "min_signals": config.min_signals,
                "vol_ma5_mult": config.vol_ma5_mult,
                "score_level_strong": config.score_level_strong,
                "score_level_watch": config.score_level_watch,
            },
            "universe_count": len(universe),
            "matched_count": len(items),
            "final_count": len(final_items),
            "all_matched": [sanitize_item(it) for it in items],
            "final_items": [sanitize_item(it) for it in final_items],
            "enriched_final": enriched_final,
        }

        output_path = os.path.join(OUTPUT_DIR, f"baseline-{date_compact}.json")
        with open(output_path, "w", encoding="utf-8") as fp:
            json.dump(payload, fp, ensure_ascii=False, indent=2, default=json_default)
        print(f"   ✅ 저장 완료: {output_path}")

        summary_rows.append(
            {
                "date": date_compact,
                "sentiment": mc.market_sentiment,
                "universe": len(universe),
                "matched_count": len(items),
                "final_count": len(final_items),
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
        "baseline_config": {
            "min_signals": config.min_signals,
            "vol_ma5_mult": config.vol_ma5_mult,
            "score_level_strong": config.score_level_strong,
            "score_level_watch": config.score_level_watch,
        },
        "total_picks": total,
        "win_rate": round((win / total * 100) if total else 0.0, 2),
        "avg_current_return": round(avg_return, 2),
        "status_counts": status_counts,
        "daily": summary_rows,
    }

    summary_path = os.path.join(OUTPUT_DIR, "summary-baseline-202511.json")
    with open(summary_path, "w", encoding="utf-8") as fp:
        json.dump(summary, fp, ensure_ascii=False, indent=2, default=json_default)
    print(f"\n📊 요약 저장: {summary_path}")
    print(
        f"총 {total}건 | 승률 {summary['win_rate']}% | 평균 수익률 {summary['avg_current_return']}%"
    )


if __name__ == "__main__":
    main()


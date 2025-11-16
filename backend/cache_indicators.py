"""
Pre-compute indicator cache for the current OHLCV history.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta

import pandas as pd

from config import config
from data_loader import (
    load_indicator_cache,
    load_price_data,
    load_universe,
    save_indicator_cache,
)
from scanner import compute_indicators


def _default_dates(days: int = 500) -> tuple[str, str]:
    end_dt = datetime.utcnow()
    start_dt = end_dt - timedelta(days=days)
    return start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d")


def build_indicator_cache(
    universe_limit: int,
    start_date: str,
    end_date: str,
    *,
    force_refresh: bool = False,
) -> None:
    universe = load_universe(limit_per_market=universe_limit, use_cache=True)
    if not universe:
        print("⚠️  유니버스가 비어 있습니다.")
        return

    print(f"📦 캐시 구축 시작 - 유니버스 {len(universe)}개, 기간 {start_date}~{end_date}")

    for idx, symbol in enumerate(universe, start=1):
        existing = load_indicator_cache(symbol)
        if (
            not force_refresh
            and not existing.empty
            and existing["date"].min() <= pd.to_datetime(start_date)
            and existing["date"].max() >= pd.to_datetime(end_date)
        ):
            print(f"  ⏭️  {symbol}: 캐시가 최신입니다. 건너뜀 ({idx}/{len(universe)})")
            continue

        ohlcv = load_price_data(symbol, start_date, end_date, cache=True)
        if ohlcv.empty or len(ohlcv) < config.ohlcv_count:
            print(f"  ⚠️  {symbol}: OHLCV 부족, 캐시 생략 ({idx}/{len(universe)})")
            continue

        indicators = compute_indicators(ohlcv)
        save_indicator_cache(symbol, indicators)
        print(f"  ✅ {symbol}: 캐시 저장 완료 ({idx}/{len(universe)})")

    print("🎉 캐시 구축 완료")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="지표 캐시 사전 계산기")
    parser.add_argument("--limit-per-market", type=int, default=100, help="시장별 유니버스 제한")
    parser.add_argument("--start-date", type=str, help="시작일 (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, help="종료일 (YYYY-MM-DD)")
    parser.add_argument("--force-refresh", action="store_true", help="기존 캐시 무시 후 재계산")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.start_date and args.end_date:
        start, end = args.start_date, args.end_date
    else:
        start, end = _default_dates()
    build_indicator_cache(
        args.limit_per_market,
        start,
        end,
        force_refresh=args.force_refresh,
    )


if __name__ == "__main__":
    main()



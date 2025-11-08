"""Kiwoom REST API 기반 단기 상승주 분석 스크립트.

- 거래대금 상위 종목을 대상으로 지정한 날짜(복수 가능)의 일간 수익률 계산
- 상승 폭이 큰 종목을 정렬하여 주요 특성(거래량, 변동성, 추세) 요약

사용 예)
    python analyze_top_gainers.py --dates 20251106 20251107 --per-market 150 --top 30 --export output.json
"""
import argparse
import json
import math
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from kiwoom_api import api


@dataclass
class GainerRecord:
    code: str
    name: str
    market: str
    date: str
    change_pct: float
    close: float
    prev_close: float
    high: float
    low: float
    volume: int
    volume_ratio: float
    intraday_range_pct: float
    close_position: float
    five_day_trend_pct: float
    twenty_day_trend_pct: float
    comment: str


def _round_or_nan(value: float, digits: int = 4, default: Optional[float] = None) -> float:
    if value is None:
        return default if default is not None else math.nan
    try:
        if math.isnan(value):
            return default if default is not None else math.nan
    except TypeError:
        return default if default is not None else math.nan
    return round(float(value), digits)


def _safe_mean(series: pd.Series) -> float:
    if series is None or series.empty:
        return 0.0
    return float(series.mean())


def _build_comment(change_pct: float, volume_ratio: float, intraday_range_pct: float, five_day_trend_pct: float) -> str:
    tags: List[str] = []

    if change_pct >= 10:
        tags.append("장대 양봉")
    elif change_pct >= 5:
        tags.append("강한 상승")
    elif change_pct >= 3:
        tags.append("완만한 상승")

    if volume_ratio >= 3:
        tags.append("거래량 급증")
    elif volume_ratio >= 1.5:
        tags.append("거래량 증가")

    if intraday_range_pct >= 8:
        tags.append("변동성 큼")
    elif intraday_range_pct <= 3:
        tags.append("변동성 낮음")

    if five_day_trend_pct >= 5:
        tags.append("단기 추세 우상향")
    elif five_day_trend_pct <= -2:
        tags.append("단기 추세 약화")

    if not tags:
        return "특징 미약"
    return ", ".join(tags)


def analyze_daily_gainers(target_dates: List[str], per_market: int = 150, top_n: int = 30) -> Dict[str, List[GainerRecord]]:
    target_dates = sorted(set(target_dates))
    max_base_dt = max(target_dates)

    markets = ["KOSPI", "KOSDAQ"]
    universe_codes: Dict[str, List[str]] = {}
    for market in markets:
        try:
            universe_codes[market] = api.get_top_codes(market, per_market)
        except Exception as exc:
            print(f"⚠️ {market} 거래대금 상위 코드 조회 실패: {exc}")
            universe_codes[market] = []

    results: Dict[str, List[GainerRecord]] = defaultdict(list)
    seen_codes: set[str] = set()

    for market in markets:
        for code in universe_codes.get(market, []):
            if not code or not code.isdigit() or code in seen_codes:
                continue

            df = api.get_ohlcv(code, count=120, base_dt=max_base_dt)
            if df.empty:
                continue

            df = df.sort_values("date").reset_index(drop=True)
            df["date"] = df["date"].astype(str)

            for target in target_dates:
                indices = df.index[df["date"] == target].tolist()
                if not indices:
                    continue
                idx = indices[0]
                if idx == 0:
                    continue

                row = df.loc[idx]
                prev_row = df.loc[idx - 1]

                close = float(row["close"])
                prev_close = float(prev_row["close"])
                if close <= 0 or prev_close <= 0:
                    continue

                change_pct = (close - prev_close) / prev_close * 100.0
                if change_pct <= 0:
                    continue

                volume = int(row.get("volume", 0))
                recent_volumes = df.loc[max(0, idx - 5): idx - 1, "volume"]
                volume_avg5 = _safe_mean(recent_volumes)
                volume_ratio = (volume / volume_avg5) if volume_avg5 > 0 else float("inf")

                high = float(row.get("high", close))
                low = float(row.get("low", close))
                intraday_range_pct = (high - low) / low * 100.0 if low > 0 else 0.0
                close_position = (close - low) / (high - low) if high != low else 0.0

                five_day_trend_pct = 0.0
                if idx >= 5:
                    ref_close5 = float(df.loc[idx - 5, "close"])
                    if ref_close5 > 0:
                        five_day_trend_pct = (close - ref_close5) / ref_close5 * 100.0

                twenty_day_trend_pct = 0.0
                if idx >= 20:
                    ref_close20 = float(df.loc[idx - 20, "close"])
                    if ref_close20 > 0:
                        twenty_day_trend_pct = (close - ref_close20) / ref_close20 * 100.0

                name = api.get_stock_name(code)
                comment = _build_comment(change_pct, volume_ratio, intraday_range_pct, five_day_trend_pct)

                record = GainerRecord(
                    code=code,
                    name=name,
                    market=market,
                    date=target,
                    change_pct=_round_or_nan(change_pct, digits=2),
                    close=_round_or_nan(close, digits=2),
                    prev_close=_round_or_nan(prev_close, digits=2),
                    high=_round_or_nan(high, digits=2),
                    low=_round_or_nan(low, digits=2),
                    volume=volume,
                    volume_ratio=_round_or_nan(volume_ratio, digits=2),
                    intraday_range_pct=_round_or_nan(intraday_range_pct, digits=2),
                    close_position=_round_or_nan(close_position, digits=2, default=0.0),
                    five_day_trend_pct=_round_or_nan(five_day_trend_pct, digits=2),
                    twenty_day_trend_pct=_round_or_nan(twenty_day_trend_pct, digits=2),
                    comment=comment,
                )
                results[target].append(record)
            seen_codes.add(code)

    for target, recs in results.items():
        recs.sort(key=lambda r: r.change_pct, reverse=True)
        results[target] = recs[:top_n]
    return results


def export_results(results: Dict[str, List[GainerRecord]], export_path: Optional[Path]) -> None:
    if not export_path:
        return
    data = {date: [asdict(rec) for rec in records] for date, records in results.items()}
    export_path.parent.mkdir(parents=True, exist_ok=True)
    with export_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"📁 결과를 {export_path} 에 저장했습니다.")


def print_summary(results: Dict[str, List[GainerRecord]]) -> None:
    for date in sorted(results.keys()):
        print("=" * 80)
        print(f"📅 {date} 상승 상위 종목 ({len(results[date])} 종목)")
        print("=" * 80)
        for idx, rec in enumerate(results[date], start=1):
            print(
                f"[{idx:02d}] {rec.name} ({rec.code}, {rec.market})\n"
                f"    등락률: {rec.change_pct:.2f}% | 종가: {rec.close:,.0f} | 거래량: {rec.volume:,}\n"
                f"    전일: {rec.prev_close:,.0f} → {rec.close:,.0f} | 거래량 배수: {rec.volume_ratio:.2f}x\n"
                f"    변동폭: {rec.intraday_range_pct:.2f}% | 종가 위치: {rec.close_position:.2f}\n"
                f"    5영업일 추세: {rec.five_day_trend_pct:.2f}% | 20영업일 추세: {rec.twenty_day_trend_pct:.2f}%\n"
                f"    코멘트: {rec.comment}\n"
            )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Kiwoom REST API를 활용한 상승 상위 종목 분석")
    parser.add_argument("--dates", nargs="+", required=True, help="분석할 기준 일자 (YYYYMMDD, 복수 지정 가능)")
    parser.add_argument("--per-market", type=int, default=150, help="시장별 거래대금 상위 조회 개수 (기본 150)")
    parser.add_argument("--top", type=int, default=30, help="일자별 상위 N개 결과만 출력 (기본 30)")
    parser.add_argument("--export", type=str, default=None, help="결과를 저장할 JSON 경로 (선택)")
    return parser.parse_args()


def _validate_dates(dates: List[str]) -> List[str]:
    validated: List[str] = []
    for dt in dates:
        dt = dt.strip()
        try:
            datetime.strptime(dt, "%Y%m%d")
        except ValueError:
            raise ValueError(f"날짜 형식이 잘못되었습니다: {dt} (YYYYMMDD 필요)")
        validated.append(dt)
    if not validated:
        raise ValueError("유효한 날짜가 없습니다.")
    return validated


def main() -> None:
    args = _parse_args()
    dates = _validate_dates(args.dates)
    results = analyze_daily_gainers(dates, per_market=args.per_market, top_n=args.top)
    print_summary(results)
    if args.export:
        export_results(results, Path(args.export))


if __name__ == "__main__":
    main()

"""상승 상위 종목을 기존 스캔 로직으로 검증하는 스크립트.

사용법:
    python evaluate_gainers_against_scanner.py --dates 20251106 20251107 \
        --source data/top_gainers_20251106_20251107.json --top 10
"""
import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

from config import config
from indicators import atr, linreg_slope
from kiwoom_api import api
from market_analyzer import market_analyzer
from scanner import compute_indicators


@dataclass
class EvaluationResult:
    code: str
    name: str
    market: str
    date: str
    matched: bool
    signals_true: int
    min_signals: int
    score: Optional[int]
    reasons: List[str]
    metrics: Dict[str, float]


def load_candidates(source: Optional[Path], dates: List[str], top: int) -> Dict[str, List[Dict]]:
    """JSON 결과 등에서 날짜별 후보 목록 로드."""
    candidates: Dict[str, List[Dict]] = {d: [] for d in dates}
    if source and source.exists():
        with source.open("r", encoding="utf-8") as f:
            data = json.load(f)
        for date in dates:
            date_records = data.get(date, [])
            candidates[date] = date_records[:top]
    else:
        # JSON이 없으면 analyze_top_gainers 재사용
        from analyze_top_gainers import analyze_daily_gainers

        gainers = analyze_daily_gainers(dates, per_market=150, top_n=top)
        for date in dates:
            candidates[date] = [
                {
                    "code": rec.code,
                    "name": rec.name,
                    "market": rec.market,
                }
                for rec in gainers.get(date, [])
            ]
    return candidates


def _calc_turnover(df: pd.DataFrame, window: int = 20) -> float:
    if len(df) < window:
        return 0.0
    return float((df["close"].iloc[-window:] * df["volume"].iloc[-window:]).mean())


def _format_pct(value: float) -> float:
    return round(float(value) * 100.0, 2)


def evaluate_symbol(code: str, date: str, market: str) -> EvaluationResult:
    df = api.get_ohlcv(code, count=220, base_dt=date)
    if df.empty:
        return EvaluationResult(
            code=code,
            name=api.get_stock_name(code),
            market=market,
            date=date,
            matched=False,
            signals_true=0,
            min_signals=config.min_signals,
            score=None,
            reasons=["데이터 없음"],
            metrics={},
        )

    df = df.sort_values("date").reset_index(drop=True)
    df["date"] = df["date"].astype(str)
    df = df[df["date"] <= date].copy()
    if len(df) < 21 or df.iloc[-1]["date"] != date:
        return EvaluationResult(
            code=code,
            name=api.get_stock_name(code),
            market=market,
            date=date,
            matched=False,
            signals_true=0,
            min_signals=config.min_signals,
            score=None,
            reasons=["해당 일자 데이터 부족"],
            metrics={},
        )

    df = compute_indicators(df)
    df["TEMA20_SLOPE20"] = linreg_slope(df["TEMA20"], getattr(config, "trend_slope_lookback", 20))
    df["OBV_SLOPE20"] = linreg_slope(df["OBV"], getattr(config, "trend_slope_lookback", 20))
    df["DEMA10_SLOPE20"] = linreg_slope(df["DEMA10"], getattr(config, "trend_slope_lookback", 20))

    cur = df.iloc[-1]
    prev = df.iloc[-2]

    market_condition = None
    if config.market_analysis_enable:
        try:
            market_condition = market_analyzer.analyze_market_condition(date)
        except Exception:
            market_condition = None

    if market_condition:
        rsi_threshold = market_condition.rsi_threshold
        min_signals = market_condition.min_signals
        macd_osc_min = market_condition.macd_osc_min
        vol_ma5_mult = market_condition.vol_ma5_mult
        gap_max = market_condition.gap_max
        ext_from_tema20_max = market_condition.ext_from_tema20_max
    else:
        rsi_threshold = config.rsi_threshold
        min_signals = config.min_signals
        macd_osc_min = config.macd_osc_min
        vol_ma5_mult = config.vol_ma5_mult
        gap_max = config.gap_max
        ext_from_tema20_max = config.ext_from_tema20_max

    reasons: List[str] = []

    avg_turnover = _calc_turnover(df, 20)
    if avg_turnover < config.min_turnover_krw:
        reasons.append(f"유동성 부족(20일 평균 {avg_turnover:,.0f} < {config.min_turnover_krw:,.0f})")

    if cur.close < config.min_price:
        reasons.append(f"저가 종목(현재가 {cur.close:,.0f} < {config.min_price:,.0f})")

    if cur.VOL_MA5 and cur.volume and cur.VOL_MA5 > 0:
        vol_ratio = float(cur.volume) / float(cur.VOL_MA5)
    else:
        vol_ratio = None

    overheat = (
        cur.RSI_TEMA >= config.overheat_rsi_tema
        and cur.VOL_MA5
        and cur.volume >= config.overheat_vol_mult * cur.VOL_MA5
    )
    if overheat:
        reasons.append("과열(RSI/VOL)")

    gap_now = (cur.TEMA20 - cur.DEMA10) / cur.close if cur.close else 0.0
    ext_pct = (cur.close - cur.TEMA20) / cur.TEMA20 if cur.TEMA20 else 0.0
    gap_ok = (max(gap_now, 0.0) >= config.gap_min) and (gap_now <= gap_max)
    ext_ok = ext_pct <= ext_from_tema20_max
    if not (gap_ok and ext_ok):
        reasons.append(
            f"갭/이격 초과(gap={gap_now:.4f}, ext={ext_pct:.4f}, max gap {gap_max}, max ext {ext_from_tema20_max})"
        )

    atr_pct = None
    if config.use_atr_filter:
        _atr_val = atr(df["high"], df["low"], df["close"], 14).iloc[-1]
        atr_pct = _atr_val / cur.close if cur.close else None
        if atr_pct is not None and not (config.atr_pct_min <= atr_pct <= config.atr_pct_max):
            reasons.append(f"ATR 범위 밖({atr_pct:.4f})")

    slope_lb = getattr(config, "trend_above_lookback", 5)
    above_cnt = int((df["TEMA20"] > df["DEMA10"]).tail(slope_lb).sum()) if len(df) >= slope_lb else 0

    lookback = min(5, len(df) - 1)
    crossed_recently = False
    for i in range(lookback):
        prev_row = df.iloc[-2 - i]
        curr_row = df.iloc[-1 - i]
        if (prev_row.TEMA20 <= prev_row.DEMA10) and (curr_row.TEMA20 > curr_row.DEMA10):
            crossed_recently = True
            break

    cond_gc = (crossed_recently or (cur.TEMA20 > cur.DEMA10)) and (df.iloc[-1]["TEMA20_SLOPE20"] > 0)
    cond_macd = (cur.MACD_LINE > cur.MACD_SIGNAL) or (cur.MACD_OSC > macd_osc_min)
    rsi_momentum = (cur.RSI_TEMA > cur.RSI_DEMA) or (abs(cur.RSI_TEMA - cur.RSI_DEMA) < 3 and cur.RSI_TEMA > rsi_threshold)
    cond_rsi = rsi_momentum
    cond_vol = cur.VOL_MA5 and cur.volume >= vol_ma5_mult * cur.VOL_MA5
    trend_ok = (
        df.iloc[-1]["TEMA20_SLOPE20"] > 0
        and df.iloc[-1]["OBV_SLOPE20"] > 0
        and above_cnt >= 3
    )
    if config.require_dema_slope == "required":
        trend_ok = trend_ok and (df.iloc[-1]["DEMA10_SLOPE20"] > 0)

    signals_true = sum([bool(cond_gc), bool(cond_macd), bool(cond_rsi), bool(cond_vol)])
    matched = not reasons and trend_ok and signals_true >= min_signals
    if not trend_ok:
        reasons.append("추세 부족(TEMA/OBV/DEMA 조건 미충족)")
    if signals_true < min_signals:
        reasons.append(f"신호 부족({signals_true}/{min_signals})")

    def _safe_export_float(value: Optional[float], digits: int = None) -> Optional[float]:
        if value is None:
            return None
        try:
            value = float(value)
        except (TypeError, ValueError):
            return None
        if not pd.notna(value):
            return None
        if digits is not None:
            value = round(value, digits)
        if not pd.notna(value):
            return None
        return float(value)

    metrics = {
        "close": _safe_export_float(cur.close, 2),
        "volume": _safe_export_float(cur.volume, 0),
        "volume_ratio": _safe_export_float(vol_ratio, 2),
        "gap_pct": _safe_export_float(gap_now, 4),
        "ext_pct": _safe_export_float(ext_pct, 4),
        "RSI_TEMA": _safe_export_float(cur.RSI_TEMA, 2),
        "RSI_DEMA": _safe_export_float(cur.RSI_DEMA, 2),
        "MACD_OSC": _safe_export_float(cur.MACD_OSC, 4),
        "MACD_LINE": _safe_export_float(cur.MACD_LINE, 4),
        "MACD_SIGNAL": _safe_export_float(cur.MACD_SIGNAL, 4),
        "TEMA20_SLOPE20": _safe_export_float(df.iloc[-1]["TEMA20_SLOPE20"], 6),
        "OBV_SLOPE20": _safe_export_float(df.iloc[-1]["OBV_SLOPE20"], 6),
        "DEMA10_SLOPE20": _safe_export_float(df.iloc[-1]["DEMA10_SLOPE20"], 6),
        "above_cnt5": int(above_cnt),
    }
    if atr_pct is not None:
        metrics["ATR_pct"] = round(float(atr_pct), 4)

    return EvaluationResult(
        code=code,
        name=api.get_stock_name(code),
        market=market,
        date=date,
        matched=matched,
        signals_true=int(signals_true),
        min_signals=int(min_signals),
        score=None,
        reasons=reasons,
        metrics=metrics,
    )


def run_evaluation(dates: List[str], source: Optional[Path], top: int) -> Dict[str, List[EvaluationResult]]:
    candidates = load_candidates(source, dates, top)
    evaluations: Dict[str, List[EvaluationResult]] = {}

    for date, symbols in candidates.items():
        evaluations[date] = []
        for entry in symbols:
            code = entry.get("code")
            market = entry.get("market", "")
            if not code:
                continue
            result = evaluate_symbol(code, date, market)
            evaluations[date].append(result)
    return evaluations


def print_report(results: Dict[str, List[EvaluationResult]]) -> None:
    for date in sorted(results.keys()):
        print("=" * 100)
        print(f"📅 {date} 상승 상위 종목 스캐너 적합성 평가")
        print("=" * 100)
        for res in results[date]:
            status = "✅ 매칭" if res.matched else "❌ 미매칭"
            print(f"[{status}] {res.name} ({res.code}, {res.market}) | 신호 {res.signals_true}/{res.min_signals}")
            print(
                f"    RSI_TEMA: {res.metrics.get('RSI_TEMA')} | MACD_OSC: {res.metrics.get('MACD_OSC')} | "
                f"거래량배수: {res.metrics.get('volume_ratio')}x | gap: {res.metrics.get('gap_pct')} | ext: {res.metrics.get('ext_pct')}"
            )
            if res.reasons:
                print(f"    사유: {', '.join(res.reasons)}")
            print()


def export_report(results: Dict[str, List[EvaluationResult]], export_path: Optional[Path]) -> None:
    if not export_path:
        return
    export_data = {}
    for date, items in results.items():
        export_data[date] = [
            {
                "code": res.code,
                "name": res.name,
                "market": res.market,
                "matched": bool(res.matched),
                "signals_true": int(res.signals_true),
                "min_signals": int(res.min_signals),
                "reasons": list(res.reasons),
                "metrics": res.metrics,
            }
            for res in items
        ]
    export_path.parent.mkdir(parents=True, exist_ok=True)
    with export_path.open("w", encoding="utf-8") as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)
    print(f"📁 평가 결과를 {export_path} 에 저장했습니다.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="상승주를 스캐너 조건과 비교 평가")
    parser.add_argument("--dates", nargs="+", required=True, help="평가할 날짜 (YYYYMMDD)")
    parser.add_argument("--source", type=str, default=None, help="상승주 JSON 경로 (선택)")
    parser.add_argument("--top", type=int, default=10, help="날짜별 상위 N개만 평가 (기본 10)")
    parser.add_argument("--export", type=str, default=None, help="평가 결과 저장 경로 (선택)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dates = sorted({d.strip() for d in args.dates})
    source_path = Path(args.source) if args.source else None
    results = run_evaluation(dates, source=source_path, top=args.top)
    print_report(results)
    if args.export:
        export_report(results, Path(args.export))


if __name__ == "__main__":
    main()


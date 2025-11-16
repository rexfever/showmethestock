from __future__ import annotations

"""
scanner_v2.scan_v2

신규 scanner_v2 엔진의 엔트리포인트.

v1 스캐너 코드와 완전히 독립된 경로로 동작하며,
동일 날짜/유니버스에 대해 v1과 v2 결과를 비교할 수 있도록 설계된다.
"""

import argparse
import logging
from typing import Any, Dict, List, Optional

import pandas as pd

from scanner_v2.universe.universe_builder import build_monthly_universe
from scanner_v2.indicators.indicator_loader import load_indicator_df
from scanner_v2.stage1.stage1_filter import stage1_filter
from scanner_v2.scoring import swing_scorer, position_scorer, longterm_scorer
from scanner_v2.integrator.market_condition_adapter import load_market_condition
from scanner_v2.integrator.market_integrator import integrate_scores
from scanner_v2.output.output_formatter import format_scan_result
from scanner_v2.repositories.scan_horizon_scores_repo import ScanHorizonScoresRepo
from scanner_v2.repositories.scan_final_output_repo import ScanFinalOutputRepo

logger = logging.getLogger(__name__)


def run_scan_v2(date: str, universe: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    scanner_v2 전체 파이프라인을 실행한다.

    1) 유니버스 로드/생성
    2) indicator_loader로 인디케이터 로딩
    3) Stage1 필터
    4) Horizon별 스코어 계산
    5) market_condition + integrator로 최종 후보 선정
    6) Repo 저장 및 결과 포맷팅
    """
    logger.info(f"[scanner_v2] run_scan_v2 start date={date}")

    # 1) 유니버스 준비
    if universe is None:
        universe = build_monthly_universe(date)
    symbols = list(dict.fromkeys(universe))
    logger.info(f"[scanner_v2] universe size={len(symbols)}")

    horizon_scores: List[Dict[str, Any]] = []

    # 2~4) 심볼별 indicator 로딩 → Stage1 → 3개 스코어러
    for symbol in symbols:
        try:
            df = load_indicator_df(symbol, end_date=date, lookback=120)
            if df.empty:
                continue

            # Stage1 필터
            if not stage1_filter(symbol, df):
                continue

            swing_dict = swing_scorer.score(symbol, df)
            position_dict = position_scorer.score(symbol, df)
            longterm_dict = longterm_scorer.score(symbol, df)

            # risk_score는 세 스코어러 중 최대값을 사용 (보수적으로)
            risk_scores = [
                swing_dict.get("risk_score", 0.0),
                position_dict.get("risk_score", 0.0),
                longterm_dict.get("risk_score", 0.0),
            ]
            risk_score = float(max(risk_scores))

            item = {
                "symbol": symbol,
                "swing_score": float(swing_dict.get("swing_score", 0.0)),
                "position_score": float(position_dict.get("position_score", 0.0)),
                "longterm_score": float(longterm_dict.get("longterm_score", 0.0)),
                "risk_score": risk_score,
            }
            horizon_scores.append(item)
        except Exception as exc:
            logger.warning(f"[scanner_v2] failed processing symbol={symbol}: {exc}")
            continue

    logger.info(f"[scanner_v2] Stage1+scoring completed: {len(horizon_scores)} items with scores")

    # 5) 시장 상황 로드 + 통합
    mc = load_market_condition(date)
    integrated = integrate_scores(date, mc, horizon_scores)
    formatted = format_scan_result(integrated)

    # 6) Repo 저장
    scores_repo = ScanHorizonScoresRepo()
    scores_repo.save_scores(date, horizon_scores)

    final_repo = ScanFinalOutputRepo()
    final_repo.save_output(date, formatted)

    logger.info(
        f"[scanner_v2] scan_v2 finished. "
        f"swing={len(formatted['swing_candidates'])}, "
        f"position={len(formatted['position_candidates'])}, "
        f"longterm={len(formatted['longterm_candidates'])}"
    )

    return formatted


def batch_test_position() -> None:
    """
    Position Horizon 튜닝 검증용 배치 테스트.

    지정된 날짜들에 대해 scanner_v2를 실행하고
    각 날짜별 Position 후보 수를 콘솔에 출력한다.
    """
    test_dates = ["20250723", "20250917", "20251022", "20250820", "20251105"]
    for d in test_dates:
        logger.info(f"[scanner_v2] batch_test_position start date={d}")
        result = run_scan_v2(d)
        pos_count = len(result.get("position_candidates", []))
        print(f"===== TEST {d} =====")
        print(f"Position candidates = {pos_count}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="scanner_v2 engine")
    parser.add_argument("--date", required=True, help="YYYYMMDD 형식의 스캔 기준일")
    parser.add_argument(
        "--universe",
        nargs="*",
        help="심볼 리스트 (생략 시 universe_builder로 자동 생성)",
    )
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s %(name)s - %(message)s",
    )
    args = _parse_args()
    result = run_scan_v2(args.date, args.universe)
    # CLI 실행 시 간단 요약만 출력
    print(
        f"[scanner_v2] {args.date} sentiment={result.get('market_sentiment')} "
        f"Swing={len(result.get('swing_candidates', []))}, "
        f"Position={len(result.get('position_candidates', []))}, "
        f"Longterm={len(result.get('longterm_candidates', []))}"
    )


if __name__ == "__main__":
    main()



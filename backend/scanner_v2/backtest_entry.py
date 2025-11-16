from __future__ import annotations

"""
scanner_v2.backtest_entry

scanner_v2 기반 백테스트 엔트리포인트.

사용 예:

    cd backend
    python -m scanner_v2.backtest_entry --start 20221101 --end 20251031 --horizon position
"""

import argparse

from backtest.backtest_runner import run_backtest
from backtest.report import print_summary, save_trades_csv, save_equity_curve_csv


def _parse_args() -> "argparse.Namespace":
    """CLI 인자를 파싱한다."""
    parser = argparse.ArgumentParser(description="scanner_v2 backtest runner")
    parser.add_argument("--start", required=True, help="백테스트 시작일 (YYYYMMDD)")
    parser.add_argument("--end", required=True, help="백테스트 종료일 (YYYYMMDD)")
    parser.add_argument(
        "--horizon",
        required=True,
        choices=["swing", "position", "longterm"],
        help="백테스트할 Horizon (swing / position / longterm)",
    )
    parser.add_argument(
        "--max-trades-per-day",
        type=int,
        default=None,
        help="하루 최대 트레이드 수 (옵션)",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    result = run_backtest(
        start_date=args.start,
        end_date=args.end,
        horizon=args.horizon,
        max_trades_per_day=args.max_trades_per_day,
    )

    # 요약 출력
    print_summary(result["horizon"], result["metrics"])

    # CSV 저장 (현재 작업 디렉토리에 저장)
    trades_filename = f"trades_{args.horizon}.csv"
    equity_filename = f"equity_{args.horizon}.csv"
    save_trades_csv(result["trades"], trades_filename)
    save_equity_curve_csv(result["equity_curve"], equity_filename)

    print(f"Saved trades to {trades_filename}")
    print(f"Saved equity curve to {equity_filename}")


if __name__ == "__main__":
    main()



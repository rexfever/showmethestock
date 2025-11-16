from __future__ import annotations

"""
scanner_v2.repositories.backtest_statistics_repo

백테스트 요약 통계(Sharpe, MDD, 승률 등)를 저장하기 위한 Repo 스텁.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict
import json


BASE_DIR = Path(__file__).resolve().parent.parent  # backend/scanner_v2
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class BacktestStatisticsRepo:
    """백테스트 요약 통계 저장/조회."""

    def _path_for_date(self, date: str) -> Path:
        return DATA_DIR / f"backtest_stats_{date}.json"

    def save_statistics(self, date: str, stats: Dict) -> None:
        path = self._path_for_date(date)
        with path.open("w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)

    def load_statistics(self, date: str) -> Dict:
        path = self._path_for_date(date)
        if not path.exists():
            return {}
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
            return {}
        except Exception:
            return {}



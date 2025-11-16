from __future__ import annotations

"""
scanner_v2.repositories.backtest_trades_repo

백테스트 결과(진입일, 청산일, 수익률, horizon 등)를 기록하기 위한 Repo 스텁.
초기에는 JSON 기반으로 두고, 추후 DB로 교체할 수 있도록 설계한다.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List
import json


BASE_DIR = Path(__file__).resolve().parent.parent  # backend/scanner_v2
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class BacktestTradesRepo:
    """백테스트 개별 트레이드 기록 저장/조회."""

    def _path_for_date(self, date: str) -> Path:
        return DATA_DIR / f"backtest_trades_{date}.json"

    def save_trades(self, date: str, trades: List[Dict]) -> None:
        path = self._path_for_date(date)
        with path.open("w", encoding="utf-8") as f:
            json.dump(trades, f, ensure_ascii=False, indent=2)

    def load_trades(self, date: str) -> List[Dict]:
        path = self._path_for_date(date)
        if not path.exists():
            return []
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
            return []
        except Exception:
            return []



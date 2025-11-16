from __future__ import annotations

"""
scanner_v2.repositories.scan_final_output_repo

최종 스캔 결과(date, symbol, horizon, score, risk_score, market_sentiment 등)를 저장.
초기에는 JSON 파일 기반 구현.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List
import json


BASE_DIR = Path(__file__).resolve().parent.parent  # backend/scanner_v2
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class ScanFinalOutputRepo:
    """시스템 전체 스캔 결과를 저장/조회하는 Repo."""

    def _path_for_date(self, date: str) -> Path:
        return DATA_DIR / f"final_output_{date}.json"

    def save_output(self, date: str, items: Dict) -> None:
        path = self._path_for_date(date)
        with path.open("w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)

    def load_output(self, date: str) -> Dict:
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



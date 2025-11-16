from __future__ import annotations

"""
scanner_v2.repositories.scan_horizon_scores_repo

날짜/심볼별 Horizon 스코어를 저장/조회하는 추상 레이어.

초기 구현은 파일/메모리 기반의 간단한 스텁으로 두고,
나중에 실제 DB 스키마에 연결하기 쉽게 설계한다.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List
import json

from config import config


BASE_DIR = Path(__file__).resolve().parent.parent  # backend/scanner_v2
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class ScanHorizonScoresRepo:
    """
    날짜/심볼별 swing/position/longterm score와 risk_score를 저장/조회하는 Repo.

    실제 운영에서는 DB에 매핑할 예정이지만, 초기에는 JSON 파일로 구현한다.
    """

    def _path_for_date(self, date: str) -> Path:
        return DATA_DIR / f"horizon_scores_{date}.json"

    def save_scores(self, date: str, items: List[Dict]) -> None:
        path = self._path_for_date(date)
        with path.open("w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)

    def load_scores(self, date: str) -> List[Dict]:
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



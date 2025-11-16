from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import pandas as pd

from config import config
from data_loader import load_price_data

logger = logging.getLogger(__name__)


BASE_DIR = Path(__file__).resolve().parent.parent  # backend/scanner_v2
UNIVERSE_DIR = BASE_DIR / "universe"
GLOBAL_SECTOR_MAP_PATH = UNIVERSE_DIR / "global_sector_map.json"
UNIVERSE_REBALANCE_LOG_PATH = UNIVERSE_DIR / "universe_rebalance_log.json"


@dataclass
class UniverseSnapshot:
    """한 번의 리밸런싱 때 생성된 유니버스 스냅샷."""

    as_of: str
    symbols: List[str]
    criteria: Dict


def _load_global_sector_map() -> Dict[str, str]:
    """
    심볼 → 글로벌 섹터 매핑을 로드한다.

    초기에는 파일이 없을 수 있으므로, 없으면 빈 매핑을 반환한다.
    구조만 맞춰두고, 나중에 실제 섹터 데이터를 채우도록 한다.
    """
    if not GLOBAL_SECTOR_MAP_PATH.exists():
        logger.info("global_sector_map.json not found. Using empty sector map.")
        return {}
    try:
        with GLOBAL_SECTOR_MAP_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return {str(k): str(v) for k, v in data.items()}
    except Exception as exc:
        logger.warning(f"Failed to load global_sector_map.json: {exc}")
        return {}


def _append_universe_rebalance_log(snapshot: UniverseSnapshot) -> None:
    """
    universe_rebalance_log.json에 스냅샷 기록 추가.
    """
    UNIVERSE_DIR.mkdir(parents=True, exist_ok=True)
    snapshots: List[Dict] = []
    if UNIVERSE_REBALANCE_LOG_PATH.exists():
        try:
            with UNIVERSE_REBALANCE_LOG_PATH.open("r", encoding="utf-8") as f:
                snapshots = json.load(f)
        except Exception:
            snapshots = []
    snapshots.append(asdict(snapshot))
    with UNIVERSE_REBALANCE_LOG_PATH.open("w", encoding="utf-8") as f:
        json.dump(snapshots, f, ensure_ascii=False, indent=2)


def _determine_month_start_end(target_date: str) -> tuple[str, str]:
    """target_date가 속한 월의 시작~끝 날짜(문자열)를 반환한다."""
    dt = datetime.strptime(target_date, "%Y%m%d")
    month_start = dt.replace(day=1)
    if month_start.month == 12:
        next_month_start = month_start.replace(year=month_start.year + 1, month=1, day=1)
    else:
        next_month_start = month_start.replace(month=month_start.month + 1, day=1)
    month_end = next_month_start - pd.Timedelta(days=1)
    return month_start.strftime("%Y-%m-%d"), month_end.strftime("%Y-%m-%d")


def build_monthly_universe(target_date: str) -> List[str]:
    """
    target_date(YYYYMMDD)가 속한 월에 대해,
    글로벌 섹터/유동성 기준으로 선정된 종목 코드 리스트를 반환한다.

    현재 구현:
      - data_loader.load_price_data를 사용해 최근 TURNOVER_MA20을 계산
      - TURNOVER_MA20 기준 내림차순 상위 N개 (기본 300개)
      - global_sector_map.json에 정의된 섹터 중 허용된 섹터만 포함
    """
    from kiwoom_api import api  # 지연 import: 서버 환경에서만 필요

    # 1) 유니버스 후보: KOSPI/KOSDAQ 상위 N개 (기존 설정 재사용)
    universe_kospi = getattr(config, "universe_kospi", 100)
    universe_kosdaq = getattr(config, "universe_kosdaq", 100)
    kospi_codes = api.get_top_codes("KOSPI", universe_kospi)
    kosdaq_codes = api.get_top_codes("KOSDAQ", universe_kosdaq)
    universe_codes = list(dict.fromkeys([*kospi_codes, *kosdaq_codes]))  # 중복 제거

    logger.info(
        f"[scanner_v2] building monthly universe for {target_date} "
        f"(base universe={len(universe_codes)})"
    )

    # 2) 섹터 필터 로딩
    sector_map = _load_global_sector_map()
    allowed_sectors = getattr(
        config, "scanner_v2_allowed_sectors", ["IT", "Energy", "Healthcare", "Consumer", "Financials"]
    )

    def _sector_ok(code: str) -> bool:
        sector = sector_map.get(code)
        if sector is None:
            # 섹터 정보가 없으면 일단 허용 (나중에 튜닝)
            return True
        return sector in allowed_sectors

    # 3) TURNOVER_MA20 기준 상위 N개
    month_start, month_end = _determine_month_start_end(target_date)
    end_date = min(month_end, datetime.strptime(target_date, "%Y%m%d").strftime("%Y-%m-%d"))
    lookback_days = 60  # TURNOVER_MA20 계산용
    start_dt = datetime.strptime(end_date, "%Y-%m-%d") - pd.Timedelta(days=lookback_days)
    start_date = start_dt.strftime("%Y-%m-%d")

    records = []
    for code in universe_codes:
        try:
            df = load_price_data(code, start_date, end_date, cache=True)
            if df.empty or len(df) < 20:
                continue
            df = df.sort_values("date").reset_index(drop=True)
            df["turnover"] = df["close"].astype(float) * df["volume"].astype(float)
            df["TURNOVER_MA20"] = df["turnover"].rolling(20).mean()
            last = df.iloc[-1]
            turnover_ma20 = float(last["TURNOVER_MA20"]) if pd.notna(last["TURNOVER_MA20"]) else 0.0
            records.append({"symbol": code, "TURNOVER_MA20": turnover_ma20})
        except Exception as exc:
            logger.debug(f"[scanner_v2] failed to compute TURNOVER_MA20 for {code}: {exc}")
            continue

    if not records:
        logger.warning("[scanner_v2] no records for monthly universe; returning empty list")
        return []

    df_liq = pd.DataFrame(records)
    df_liq = df_liq.sort_values("TURNOVER_MA20", ascending=False)

    # 상위 N개 (기본 300개, 설정 가능)
    target_size = int(getattr(config, "scanner_v2_universe_size", 300))
    df_liq = df_liq.head(target_size)

    # 섹터 필터 적용
    df_liq["sector_ok"] = df_liq["symbol"].apply(_sector_ok)
    df_liq = df_liq[df_liq["sector_ok"]]

    symbols = df_liq["symbol"].tolist()

    # 4) 리밸런싱 로그 기록
    snapshot = UniverseSnapshot(
        as_of=end_date,
        symbols=symbols,
        criteria={
            "base_universe_size": len(universe_codes),
            "target_size": target_size,
            "allowed_sectors": allowed_sectors,
            "lookback_days": lookback_days,
        },
    )
    _append_universe_rebalance_log(snapshot)

    logger.info(
        f"[scanner_v2] monthly universe built for {target_date}: {len(symbols)} symbols "
        f"(after sector/turnover filters)"
    )

    return symbols



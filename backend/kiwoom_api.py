import time
from datetime import datetime
import os
from typing import List, Dict
import requests
import pandas as pd
import numpy as np

from backend.auth import KiwoomAuth
from backend.config import config


class KiwoomAPI:
    """KIS OpenAPI v2 래퍼 (실데이터 기본, 필요 시 모의 폴백)"""

    def __init__(self):
        self.auth = KiwoomAuth()
        self._code_to_name: Dict[str, str] = {}
        self._name_to_code: Dict[str, str] = {}
        # 모의 데이터 세트는 항상 준비 (실패 시 폴백용)
        self._mock_kospi = [
            "005930",  # 삼성전자
            "000660",  # SK하이닉스
            "051910",  # LG화학
            "207940",  # 삼성바이오로직스
            "005380",  # 현대차
            "035420",  # NAVER
            "068270",  # 셀트리온
            "028260",  # 삼성물산
            "105560",  # KB금융
            "055550",  # 신한지주
        ]
        self._mock_kosdaq = [
            "091990",  # 셀트리온헬스케어
            "263750",  # 펄어비스
            "035720",  # 카카오게임즈
            "247540",  # 에코프로비엠
            "086520",  # 에코프로
            "293490",  # 카카오뱅크(코스피 실상이나 데모용)
        ]
        self._mock_names: Dict[str, str] = {
            "005930": "삼성전자",
            "000660": "SK하이닉스",
            "051910": "LG화학",
            "207940": "삼성바이오로직스",
            "005380": "현대차",
            "035420": "NAVER",
            "068270": "셀트리온",
            "028260": "삼성물산",
            "105560": "KB금융",
            "055550": "신한지주",
            "091990": "셀트리온헬스케어",
            "263750": "펄어비스",
            "035720": "카카오게임즈",
            "247540": "에코프로비엠",
            "086520": "에코프로",
            "293490": "카카오뱅크",
        }
        # 강제 모의 모드 플래그
        self.force_mock: bool = os.getenv("FORCE_MOCK", "").lower() in ("1", "true", "yes")
        if self.force_mock:
            for code, name in self._mock_names.items():
                self._code_to_name[code] = name
                self._name_to_code[name.replace(" ", "")] = code
        # 심볼 프리로드
        if (not self.force_mock) and config.preload_symbols:
            try:
                self._preload_symbols()
            except Exception:
                pass

    def _post(self, api_id: str, path: str, payload: dict, extra_headers: Dict[str, str] = None) -> dict:
        if self.force_mock:
            raise RuntimeError("mock mode active")
        headers = self.auth.auth_headers(api_id)
        if extra_headers:
            headers.update(extra_headers)
        url = f"{config.api_base}{path}"
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        # 레이트리밋 완충
        time.sleep(config.rate_limit_delay_ms / 1000.0)
        resp.raise_for_status()
        data = resp.json()
        # 응답 헤더를 함께 전달(페이지네이션 cont-yn/next-key)
        try:
            data["__headers__"] = {k.lower(): v for k, v in resp.headers.items()}
        except Exception:
            data["__headers__"] = {}
        return data

    def get_top_codes(self, market: str, limit: int) -> List[str]:
        """거래대금 상위 (예: ka10032) 호출 후 코드 리스트 반환
        market: 'KOSPI'|'KOSDAQ'
        """
        if self.force_mock:
            base = self._mock_kospi if market.upper() == "KOSPI" else self._mock_kosdaq
            return base[: max(0, min(len(base), limit))]
        # 실데이터: 환경설정에 고정 유니버스가 있으면 우선 사용
        if config.universe_codes:
            codes = [c.strip() for c in config.universe_codes.split(',') if c.strip()]
            return codes[:limit]
        # 거래대금 상위: ka10032 /api/dostk/krinfo
        api_id = config.kiwoom_tr_topvalue_id
        path = config.kiwoom_tr_topvalue_path
        # ka10032: mrkt_tp(001:코스피, 101:코스닥), 관리종목 포함 여부, 거래소 구분
        base_payload = {
            "mrkt_tp": "001" if market.upper() == "KOSPI" else "101",
            "mang_stk_incls": "0",
            "stex_tp": "1",
        }
        codes: List[str] = []
        next_key = None
        # 페이지네이션: cont-yn/next-key 헤더 사용
        while len(codes) < limit:
            headers = {"cont-yn": "Y", "next-key": next_key} if next_key else {"cont-yn": "N"}
            try:
                data = self._post(api_id, path, base_payload, extra_headers=headers)
            except Exception:
                break
            if data.get("rt_cd") not in ("0", 0) and data.get("return_code") not in (0, "0"):
                break
            output = data.get("trde_prica_upper", []) or data.get("output", []) or data.get("data", [])
            for item in output:
                code = item.get("stk_cd") or item.get("mksc_shrn_iscd") or item.get("stck_shrn_iscd") or item.get("code")
                if code:
                    codes.append(code)
                    if len(codes) >= limit:
                        break
            resp_headers = data.get("__headers__", {})
            cont = resp_headers.get("cont-yn", "N")
            next_key = resp_headers.get("next-key")
            if cont != "Y" or not next_key:
                break
        if not codes and config.universe_codes:
            tmp = [c.strip() for c in config.universe_codes.split(',') if c.strip()]
            return tmp[:limit]
        if not codes and config.use_mock_fallback:
            base = self._mock_kospi if market.upper() == "KOSPI" else self._mock_kosdaq
            return base[: max(0, min(len(base), limit))]
        return codes[:limit]

    def _preload_symbols(self) -> None:
        markets = [m.strip() for m in config.kiwoom_symbol_markets.split(',') if m.strip()]
        for m in markets:
            api_id = config.kiwoom_tr_stockinfo_id
            path = config.kiwoom_tr_stockinfo_path
            next_key = None
            while True:
                headers = {"cont-yn": "Y", "next-key": next_key} if next_key else {"cont-yn": "N"}
                payload = {"mrkt_tp": m}
                data = self._post(api_id, path, payload, extra_headers=headers)
                if data.get("rt_cd") not in ("0", 0) and data.get("return_code") not in (0, "0"):
                    break
                lst = data.get("list", []) or data.get("output", []) or data.get("data", [])
                for it in lst:
                    cd = it.get("code") or it.get("mksc_shrn_iscd") or it.get("stck_shrn_iscd")
                    nm = it.get("name") or it.get("prdt_abrv_name")
                    if cd and nm:
                        self._code_to_name[cd] = nm
                        self._name_to_code[nm.replace(" ", "")] = cd
                h = data.get("__headers__", {})
                if h.get("cont-yn") != "Y" or not h.get("next-key"):
                    break
                next_key = h.get("next-key")

    def get_ohlcv(self, code: str, count: int = 220) -> pd.DataFrame:
        """일봉 OHLCV DataFrame(date, open, high, low, close, volume) 반환"""
        if self.force_mock:
            return self._gen_mock_ohlcv(code, count)
        api_id = config.kiwoom_tr_ohlcv_id
        path = config.kiwoom_tr_ohlcv_path
        # ka10081: stk_cd, base_dt(YYYYMMDD), upd_stkpc_tp(0|1)
        params = {
            "stk_cd": code,
            # 스펙상 YYYYMMDD 필수: 당일(또는 전영업일) 기준으로 요청
            "base_dt": datetime.now().strftime("%Y%m%d"),
            "upd_stkpc_tp": "1",
        }
        try:
            data = self._post(api_id, path, params)
        except Exception:
            # 실패 시 폴백: 허용된 경우에만 모의 생성
            return self._gen_mock_ohlcv(code, count) if config.use_mock_fallback else pd.DataFrame()
        if data.get("rt_cd") != "0" and data.get("return_code") not in (0, "0"):
            return self._gen_mock_ohlcv(code, count) if config.use_mock_fallback else pd.DataFrame()
        rows = (
            data.get("stk_dt_pole_chart_qry", [])
            or data.get("output2", [])
            or data.get("data", [])
        )
        df = pd.DataFrame(
            [
                {
                    "date": r.get("dt") or r.get("date") or r.get("stck_bsop_date"),
                    "open": float(r.get("opn_prc") or r.get("open") or r.get("stck_oprc") or 0),
                    "high": float(r.get("hg_prc") or r.get("high") or r.get("stck_hgpr") or 0),
                    "low": float(r.get("lw_prc") or r.get("low") or r.get("stck_lwpr") or 0),
                    "close": float(r.get("cls_prc") or r.get("close") or r.get("stck_clpr") or 0),
                    "volume": int(r.get("trd_qty") or r.get("volume") or r.get("acml_vol") or 0),
                }
                for r in rows
            ]
        )
        if df.empty:
            return df
        # 날짜 오름차순 정렬 및 tail(count)
        df = df.sort_values("date").reset_index(drop=True).tail(count)
        return df

    def _gen_mock_ohlcv(self, code: str, count: int) -> pd.DataFrame:
        seed = int(code[-4:], 10) if code.isdigit() else 42
        rng = np.random.default_rng(seed)
        dates = pd.date_range(end=pd.Timestamp.today().normalize(), periods=count, freq="B")
        prices = np.cumsum(rng.normal(loc=0.2, scale=1.5, size=len(dates))) + 50000
        prices = np.clip(prices, a_min=1000, a_max=None)
        close = pd.Series(prices).astype(float)
        # 최근 30영업일에 상승 추세 및 마지막 날 추가 랠리 부여 (골든크로스/모멘텀 유도)
        tail_len = min(30, len(close))
        close.iloc[-tail_len:] = close.iloc[-tail_len:] + np.linspace(0, 1500, tail_len)
        close.iloc[-1] = close.iloc[-2] + max(200.0, abs(rng.normal(250.0, 80.0)))
        close = close.round(0)
        # 고저/시가/거래량 생성
        high = (close + rng.normal(50, 100, size=len(dates))).clip(lower=close)
        low = (close - rng.normal(50, 100, size=len(dates))).clip(lower=1000)
        open_ = close.shift(1).fillna(close.iloc[0])
        volume = rng.integers(100000, 5000000, size=len(dates)).astype(float)
        # 최근 5일은 점증, 마지막 날은 강한 스파이크 (거래확대 조건 유도)
        vol_tail = min(5, len(volume))
        for i in range(1, vol_tail + 1):
            volume[-i] *= 1.0 + (i - 1) * 0.2
        volume[-1] *= 3.0
        df = pd.DataFrame({
            "date": dates.strftime("%Y%m%d"),
            "open": open_.astype(float),
            "high": high.astype(float),
            "low": low.astype(float),
            "close": close.astype(float),
            "volume": volume.astype(int),
        })
        return df.reset_index(drop=True)

    def get_stock_name(self, code: str) -> str:
        """코드→이름 매핑 (캐시 우선). 실패 시 코드 그대로 반환"""
        if code in self._code_to_name:
            return self._code_to_name[code]
        if self.force_mock:
            name = self._mock_names.get(code, code)
            self._code_to_name[code] = name
            self._name_to_code[name.replace(" ", "")] = code
            return name
        # 캐시 미스 시 심볼 프리로드 재시도
        try:
            self._preload_symbols()
        except Exception:
            pass
        name = self._code_to_name.get(code, code)
        if name != code:
            self._name_to_code[name.replace(" ", "")] = code
        return name

    def get_code_by_name(self, name: str) -> str:
        """이름→코드 매핑. 1) 캐시 2) (모의/실제) 조회 3) 유니버스 후 역매핑"""
        key = name.replace(" ", "")
        if key in self._name_to_code:
            return self._name_to_code[key]

        if self.force_mock:
            # 부분 일치 허용
            for code, nm in self._mock_names.items():
                if key in nm.replace(" ", ""):
                    self._name_to_code[key] = code
                    self._code_to_name[code] = nm
                    return code
            return ""

        # 1) 캐시 내 부분 일치 검색
        for cd, nm in self._code_to_name.items():
            if key in nm.replace(" ", ""):
                self._name_to_code[key] = cd
                return cd
        # 2) 캐시가 비어 있을 수 있으니 프리로드 재시도 후 다시 검색
        try:
            self._preload_symbols()
            for cd, nm in self._code_to_name.items():
                if key in nm.replace(" ", ""):
                    self._name_to_code[key] = cd
                    return cd
        except Exception:
            pass

        # 2) 유니버스 상위 코드 조회 후 이름 역매핑 (보수적)
        codes = []
        try:
            codes += self.get_top_codes("KOSPI", min(200, config.universe_kospi))
            codes += self.get_top_codes("KOSDAQ", min(200, config.universe_kosdaq))
        except Exception:
            codes = []
        for cd in codes:
            nm = self.get_stock_name(cd)
            if name.replace(" ", "") in nm.replace(" ", ""):
                self._name_to_code[name.replace(" ", "")] = cd
                return cd
        # 실패 시 빈 문자열
        return ""



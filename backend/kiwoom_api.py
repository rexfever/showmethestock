import time
from typing import List
import requests
import pandas as pd

from auth import KiwoomAuth
from config import config


class KiwoomAPI:
    """키움 REST 호출 래퍼"""

    def __init__(self):
        self.auth = KiwoomAuth()
        self._code_to_name = {}
        self._name_to_code = {}

    def _get(self, api_id: str, path: str, params: dict) -> dict:
        headers = self.auth.auth_headers(api_id)
        url = f"{config.api_base}{path}"
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        # 레이트리밋 완충
        time.sleep(config.rate_limit_delay_ms / 1000.0)
        resp.raise_for_status()
        return resp.json()

    def get_top_codes(self, market: str, limit: int) -> List[str]:
        """거래대금 상위 (예: ka10032) 호출 후 코드 리스트 반환
        market: 'KOSPI'|'KOSDAQ'
        """
        # 실제 TR/파라미터 매핑 지점. 샘플 파라미터로 구성
        api_id = "KA10032"
        path = "/uapi/domestic-stock/v1/quotations/inquire-top-value"
        params = {
            "market": market,
            "limit": limit,
        }
        try:
            data = self._get(api_id, path, params)
        except Exception:
            return []
        if data.get("rt_cd") != "0" and data.get("return_code") not in (0, "0"):
            return []
        output = data.get("output", []) or data.get("data", [])
        codes = []
        for item in output:
            code = (
                item.get("mksc_shrn_iscd")
                or item.get("code")
                or item.get("stck_shrn_iscd")
            )
            if code:
                codes.append(code)
        return codes[:limit]

    def get_ohlcv(self, code: str, count: int = 220) -> pd.DataFrame:
        """일봉 OHLCV DataFrame(date, open, high, low, close, volume) 반환"""
        api_id = "FHKST03010100"
        path = "/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
        params = {
            "fid_cond_mrkt_div_code": "J",
            "fid_input_iscd": code,
            "fid_input_date_1": "",
            "fid_input_date_2": "",
            "fid_period_div_code": "D",
            "fid_org_adj_prc": "1",
        }
        try:
            data = self._get(api_id, path, params)
        except Exception:
            return pd.DataFrame()
        if data.get("rt_cd") != "0" and data.get("return_code") not in (0, "0"):
            return pd.DataFrame()
        rows = data.get("output2", []) or data.get("data", [])
        df = pd.DataFrame(
            [
                {
                    "date": r.get("stck_bsop_date"),
                    "open": float(r.get("stck_oprc", 0)),
                    "high": float(r.get("stck_hgpr", 0)),
                    "low": float(r.get("stck_lwpr", 0)),
                    "close": float(r.get("stck_clpr", 0)),
                    "volume": int(r.get("acml_vol", 0)),
                }
                for r in rows
            ]
        )
        if df.empty:
            return df
        # 날짜 오름차순 정렬 및 tail(count)
        df = df.sort_values("date").reset_index(drop=True).tail(count)
        return df

    def get_stock_name(self, code: str) -> str:
        """코드→이름 매핑 (캐시 포함). 실패 시 코드 그대로 반환"""
        if code in self._code_to_name:
            return self._code_to_name[code]
        # 추정 TR: 코드 정보 조회. 실패 시 기본값
        api_id = "CTPF1002R"
        path = "/uapi/domestic-stock/v1/quotations/search-stock-info"
        params = {
            "PRDT_TYPE_CD": "300",
            "MICR_DNVL_CNDC_1": code,
        }
        try:
            data = self._get(api_id, path, params)
        except Exception:
            name = code
        else:
            name = code
            output = data.get("output", []) or data.get("data", [])
            if output:
                cand = output[0]
                name = cand.get("prdt_abrv_name") or cand.get("name") or code
        self._code_to_name[code] = name
        # 역방향 캐시 (느슨하게)
        key = name.replace(" ", "")
        if key not in self._name_to_code:
            self._name_to_code[key] = code
        return name

    def get_code_by_name(self, name: str) -> str:
        """이름→코드 매핑. 1) 캐시 2) 검색 TR 시도 3) 유니버스 상위 조회 후 역매핑"""
        key = name.replace(" ", "")
        if key in self._name_to_code:
            return self._name_to_code[key]

        # 1) 검색 TR 시도 (키워드 기반) - 엔드포인트/파라미터는 실제 사양에 맞게 조정 필요
        api_id = "CTPF1002R"
        path = "/uapi/domestic-stock/v1/quotations/search-stock-info"
        params = {
            "PRDT_TYPE_CD": "300",
            "PRDT_ABRV_NAME": name,  # 가설 파라미터명 (추후 실제값으로 교체)
        }
        try:
            data = self._get(api_id, path, params)
            output = data.get("output", []) or data.get("data", [])
            for item in output:
                nm = item.get("prdt_abrv_name") or item.get("name")
                cd = item.get("mksc_shrn_iscd") or item.get("stck_shrn_iscd") or item.get("code")
                if nm and cd and name.replace(" ", "") in nm.replace(" ", ""):
                    self._name_to_code[name.replace(" ", "")] = cd
                    self._code_to_name[cd] = nm
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



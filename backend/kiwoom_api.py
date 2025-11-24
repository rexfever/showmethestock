import time
from datetime import datetime
import os
from typing import List, Dict, Optional, Tuple
import requests
import pandas as pd
import numpy as np

from auth import KiwoomAuth
from config import config


class KiwoomAPI:
    """KIS OpenAPI v2 래퍼 (실데이터 기본, 필요 시 모의 폴백)"""

    def __init__(self):
        self.auth = KiwoomAuth()
        self._code_to_name: Dict[str, str] = {}
        self._name_to_code: Dict[str, str] = {}
        # OHLCV 캐시: {(code, count, base_dt): (df, timestamp)}
        self._ohlcv_cache: Dict[Tuple[str, int, Optional[str]], Tuple[pd.DataFrame, float]] = {}
        self._cache_ttl = 300  # 기본 5분 (초) - 상황에 따라 동적으로 계산됨
        self._cache_maxsize = 1000  # 최대 캐시 항목 수
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
            # 1: KRX(코스피), 2: NXT(코스닥), 3: 통합
            "stex_tp": "1" if market.upper() == "KOSPI" else "2",
        }
        codes: List[str] = []
        next_key = None

        def _extract_codes(obj) -> List[str]:
            found: List[str] = []
            if isinstance(obj, dict):
                # 코드 후보 키
                for k in ("stk_cd", "mksc_shrn_iscd", "stck_shrn_iscd", "code"):
                    v = obj.get(k)
                    if isinstance(v, str):
                        # _NX 접미사 제거 후 6자리 숫자 확인
                        code = v.split('_')[0]
                        if len(code) == 6 and code.isdigit():
                            found.append(code)
                # 딕셔너리 내부 순회
                for v in obj.values():
                    found.extend(_extract_codes(v))
            elif isinstance(obj, list):
                for it in obj:
                    found.extend(_extract_codes(it))
            return found

        # 페이지네이션: 헤더 우선, 바디의 cont_yn/next_key 보조
        while len(codes) < limit:
            headers = {"cont-yn": "Y", "next-key": next_key} if next_key else {"cont-yn": "N"}
            try:
                data = self._post(api_id, path, base_payload, extra_headers=headers)
            except Exception:
                break
            # 상태코드가 명시된 경우에만 에러로 간주. 키가 없으면 통과
            rt_cd = data.get("rt_cd")
            return_code = data.get("return_code")
            # rt_cd가 None이거나 '0'이면 정상, return_code가 0이 아니면 오류
            if (rt_cd is not None and rt_cd not in ("0", 0)) or (return_code is not None and return_code not in (0, "0")):
                break
            # 출력 후보 전방위 탐색
            output_candidates = [
                data.get("trde_prica_upper"),
                data.get("output"),
                data.get("data"),
                data.get("list"),
            ]
            extracted: List[str] = []
            for cand in output_candidates:
                extracted.extend(_extract_codes(cand))
            # 중복 제거 순서 유지
            for cd in extracted:
                if cd not in codes:
                    codes.append(cd)
                    if len(codes) >= limit:
                        break

            # 페이지네이션 키 탐색(헤더→바디)
            resp_headers = data.get("__headers__", {})
            cont = resp_headers.get("cont-yn") or str(data.get("cont_yn") or data.get("cont-yn") or "N")
            next_key = resp_headers.get("next-key") or data.get("next_key") or data.get("next-key")
            if cont != "Y" or not next_key:
                break
        # 보조 플랜 1: .env 고정 유니버스
        if not codes and config.universe_codes:
            tmp = [c.strip() for c in config.universe_codes.split(',') if c.strip()]
            return tmp[:limit]
        # 보조 플랜 2: 종목정보(ka10099)로 시장별 전체 코드를 받아 상위 N개로 대체
        if not codes:
            try:
                api_id2 = config.kiwoom_tr_stockinfo_id
                path2 = config.kiwoom_tr_stockinfo_path
                headers2 = {"cont-yn": "N"}
                payload2 = {"mrkt_tp": "001" if market.upper() == "KOSPI" else "101"}
                data2 = self._post(api_id2, path2, payload2, extra_headers=headers2)
                lst = data2.get("list", []) or data2.get("output", []) or data2.get("data", [])
                found = []
                for it in lst:
                    cd = it.get("code") or it.get("mksc_shrn_iscd") or it.get("stck_shrn_iscd") or it.get("stk_cd")
                    if isinstance(cd, str) and len(cd) == 6 and cd.isdigit():
                        found.append(cd)
                if found:
                    return found[:limit]
            except Exception:
                pass
        if not codes and config.use_mock_fallback:
            base = self._mock_kospi if market.upper() == "KOSPI" else self._mock_kosdaq
            return base[: max(0, min(len(base), limit))]
        return codes[:limit]

    # 디버그용: 거래대금 상위 TR(ka10032) 1회 호출 원시 응답 반환
    def debug_call_topvalue_once(self, market: str) -> dict:
        if self.force_mock:
            return {"mock": True, "codes": self._mock_kospi if market.upper()=="KOSPI" else self._mock_kosdaq}
        api_id = config.kiwoom_tr_topvalue_id
        path = config.kiwoom_tr_topvalue_path
        payload = {
            "mrkt_tp": "001" if market.upper()=="KOSPI" else "101",
            "mang_stk_incls": "0",
            "stex_tp": "1",
        }
        try:
            return self._post(api_id, path, payload, extra_headers={"cont-yn": "N"})
        except Exception as e:
            return {"error": str(e)}

    # 디버그용: 종목정보 TR(ka10099) 1회 호출 원시 응답 반환
    def debug_call_stockinfo_once(self, market_tp: str = '001') -> dict:
        if self.force_mock:
            return {"mock": True, "market_tp": market_tp}
        api_id = config.kiwoom_tr_stockinfo_id
        path = config.kiwoom_tr_stockinfo_path
        try:
            return self._post(api_id, path, {"mrkt_tp": market_tp}, extra_headers={"cont-yn": "Y"})
        except Exception as e:
            return {"error": str(e)}

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
                rt = data.get("rt_cd"); rc = data.get("return_code")
                if (rt is not None and rt not in ("0", 0)) or (rc is not None and rc not in (0, "0")):
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

    def _get_cache_key(self, code: str, count: int, base_dt: Optional[str]) -> Tuple[str, int, Optional[str]]:
        """캐시 키 생성"""
        return (code, count, base_dt)
    
    def _calculate_ttl(self, base_dt: Optional[str]) -> int:
        """상황에 맞는 TTL 계산
        
        - 과거 날짜: 1년 (변경되지 않음)
        - 장중: 1분 (실시간성 필요)
        - 장 마감 후: 24시간 (다음 거래일까지)
        """
        if base_dt:
            try:
                from datetime import datetime
                base_date = datetime.strptime(base_dt, "%Y%m%d").date()
                now_date = datetime.now().date()
                if base_date < now_date:
                    # 과거 날짜: 1년 캐싱
                    return 365 * 24 * 3600
            except:
                pass
        
        # 현재 날짜: 장중 여부에 따라
        if self._is_market_open():
            return 60  # 장중: 1분
        else:
            return 24 * 3600  # 장 마감 후: 24시간
    
    def _is_market_open(self) -> bool:
        """장중 여부 확인 (09:00 ~ 15:30, 평일만)"""
        from datetime import datetime
        import pytz
        
        KST = pytz.timezone('Asia/Seoul')
        now = datetime.now(KST)
        
        # 주말 제외
        if now.weekday() >= 5:  # 토요일(5), 일요일(6)
            return False
        
        hour = now.hour
        minute = now.minute
        
        # 장중: 09:00 ~ 15:30
        return (9 <= hour < 15) or (hour == 15 and minute <= 30)
    
    def _get_cached_ohlcv(self, code: str, count: int, base_dt: Optional[str]) -> Optional[pd.DataFrame]:
        """캐시에서 OHLCV 데이터 조회"""
        cache_key = self._get_cache_key(code, count, base_dt)
        
        if cache_key not in self._ohlcv_cache:
            return None
        
        cached_df, timestamp = self._ohlcv_cache[cache_key]
        
        # 동적 TTL 계산
        ttl = self._calculate_ttl(base_dt)
        
        # TTL 확인
        if time.time() - timestamp > ttl:
            del self._ohlcv_cache[cache_key]
            return None
        
        # 복사본 반환 (원본 데이터 보호)
        return cached_df.copy()
    
    def _set_cached_ohlcv(self, code: str, count: int, base_dt: Optional[str], df: pd.DataFrame) -> None:
        """OHLCV 데이터를 캐시에 저장"""
        if df.empty:
            return
        
        cache_key = self._get_cache_key(code, count, base_dt)
        
        # 캐시 크기 제한 (LRU 방식)
        if len(self._ohlcv_cache) >= self._cache_maxsize:
            # 가장 오래된 항목 제거
            oldest_key = min(self._ohlcv_cache.items(), key=lambda x: x[1][1])[0]
            del self._ohlcv_cache[oldest_key]
        
        # 캐시 저장 (복사본 저장)
        self._ohlcv_cache[cache_key] = (df.copy(), time.time())
    
    def clear_ohlcv_cache(self, code: str = None) -> None:
        """OHLCV 캐시 클리어
        
        Args:
            code: 특정 종목 코드 (None이면 전체 캐시 클리어)
        """
        if code is None:
            self._ohlcv_cache.clear()
        else:
            # 특정 종목의 모든 캐시 항목 제거
            keys_to_remove = [
                key for key in self._ohlcv_cache.keys()
                if key[0] == code
            ]
            for key in keys_to_remove:
                del self._ohlcv_cache[key]
    
    def get_ohlcv_cache_stats(self) -> Dict:
        """캐시 통계 반환"""
        current_time = time.time()
        valid_count = sum(
            1 for _, (_, timestamp) in self._ohlcv_cache.items()
            if current_time - timestamp <= self._cache_ttl
        )
        expired_count = len(self._ohlcv_cache) - valid_count
        
        return {
            "total": len(self._ohlcv_cache),
            "valid": valid_count,
            "expired": expired_count,
            "maxsize": self._cache_maxsize,
            "ttl": self._cache_ttl
        }
    
    def get_ohlcv(self, code: str, count: int = 220, base_dt: str = None) -> pd.DataFrame:
        """일봉 OHLCV DataFrame(date, open, high, low, close, volume) 반환
        base_dt가 지정되면 해당 기준일을 마지막 행으로 하는 시계열을 우선 시도한다(YYYYMMDD).
        
        캐싱 적용: 같은 (code, count, base_dt) 조합은 5분간 캐시에서 반환
        """
        # 캐시 확인
        cached_df = self._get_cached_ohlcv(code, count, base_dt)
        if cached_df is not None:
            return cached_df
        
        # 캐시 미스: API 호출
        if self.force_mock:
            df = self._gen_mock_ohlcv(code, count, base_dt)
        else:
            df = self._fetch_ohlcv_from_api(code, count, base_dt)
        
        # 캐시 저장
        if not df.empty:
            self._set_cached_ohlcv(code, count, base_dt, df)
        
        return df
    
    def _fetch_ohlcv_from_api(self, code: str, count: int = 220, base_dt: str = None) -> pd.DataFrame:
        """API에서 OHLCV 데이터를 직접 가져오기 (캐싱 없음)"""
        api_id = config.kiwoom_tr_ohlcv_id
        path = config.kiwoom_tr_ohlcv_path
        # ka10081: stk_cd, base_dt(YYYYMMDD), upd_stkpc_tp(0|1)
        # 샘플 스펙에 따라 접두사 없이 6자리 코드를 기본 사용.
        # 1차: base_dt 미지정(서버 기본) → 2차: 직전 영업일 재시도
        def _request(bdt: str) -> list:
            payload = {"stk_cd": code, "base_dt": bdt or "", "upd_stkpc_tp": "1"}
            d = self._post(api_id, path, payload)
            if d.get("rt_cd") not in ("0", 0) and d.get("return_code") not in (0, "0"):
                return []
            return d.get("stk_dt_pole_chart_qry", []) or d.get("output2", []) or d.get("data", [])

        # 우선순위: 명시 base_dt → (기준일-1B) → (기준일-2B) ... → 오늘/전영업일
        tried = False
        rows = []
        if base_dt:
            try:
                rows = _request(base_dt)
                tried = True
            except Exception:
                rows = []
            # 기준일로부터 이전 영업일 다중 재시도(최대 4)
            if not rows:
                try:
                    base_ts = pd.to_datetime(base_dt)
                    for i in range(1, 5):
                        prev = (base_ts - pd.tseries.offsets.BDay(i)).strftime("%Y%m%d")
                        rows = _request(prev)
                        if rows:
                            break
                except Exception:
                    rows = []
        # 기준일 루트에서도 실패하면 오늘/전영업일로 보조 시도
        if not rows:
            rows = _request("")
        if not rows:
            prev = pd.bdate_range(end=pd.Timestamp.today(), periods=2)[0]
            rows = _request(prev.strftime("%Y%m%d"))
        # API 응답 디버깅: 실제 응답 구조 확인 (high/low가 0인 경우)
        # 디버깅 플래그가 활성화된 경우에만 로깅
        if rows and len(rows) > 0 and os.getenv("DEBUG_API_RESPONSE") == "1":
            sample_row = rows[0]
            print(f"🔍 API 응답 디버깅 (코드: {code}):")
            print(f"   사용 가능한 모든 키: {list(sample_row.keys())}")
            high_candidates = {k: sample_row.get(k) for k in ["high_prc", "hg_prc", "high", "stck_hgpr"] if k in sample_row}
            if high_candidates:
                print(f"   high 후보 필드: {high_candidates}")
            low_candidates = {k: sample_row.get(k) for k in ["low_prc", "lw_prc", "low", "stck_lwpr"] if k in sample_row}
            if low_candidates:
                print(f"   low 후보 필드: {low_candidates}")
            print(f"   샘플 응답: {str(sample_row)[:500]}")
        
        df = pd.DataFrame(
            [
                {
                    "date": r.get("dt") or r.get("date") or r.get("stck_bsop_date"),
                    # ka10081 API 실제 응답 필드명: open_pric, high_pric, low_pric, cur_prc, trde_qty
                    "open": float(r.get("open_pric") or r.get("opn_prc") or r.get("open_prc") or r.get("open") or r.get("stck_oprc") or 0),
                    "high": float(r.get("high_pric") or r.get("stck_hgpr") or r.get("high_prc") or r.get("hg_prc") or r.get("high") or 0),
                    "low": float(r.get("low_pric") or r.get("stck_lwpr") or r.get("low_prc") or r.get("lw_prc") or r.get("low") or 0),
                    # 종가 우선. 장중에는 cls_prc가 비거나 0일 수 있어 cur_prc를 보조로 사용
                    "close": float(r.get("cur_prc") or r.get("stck_clpr") or r.get("cls_prc") or r.get("close") or 0),
                    "volume": int(r.get("trde_qty") or r.get("acml_vol") or r.get("trd_qty") or r.get("volume") or 0),
                }
                for r in rows
            ]
        )
        if df.empty:
            return df
        # 유효 데이터만 필터(종가/거래량 0 제거)
        df = df[(df["close"] > 0) & (df["volume"] > 0)]
        if df.empty:
            return df
        # 날짜 오름차순 정렬 및 tail(count)
        df = df.sort_values("date").reset_index(drop=True).tail(count)
        return df

    def _gen_mock_ohlcv(self, code: str, count: int, base_dt: str = None) -> pd.DataFrame:
        seed = int(code[-4:], 10) if code.isdigit() else 42
        rng = np.random.default_rng(seed)
        
        # base_dt가 지정되면 해당 날짜를 기준으로 생성
        if base_dt:
            try:
                end_date = pd.to_datetime(base_dt, format='%Y%m%d').normalize()
            except:
                end_date = pd.Timestamp.today().normalize()
        else:
            end_date = pd.Timestamp.today().normalize()
            
        dates = pd.date_range(end=end_date, periods=count, freq="B")
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

    def get_stock_quote(self, code: str) -> dict:
        """종목의 현재가 정보 조회 (키움 REST API 반환값 사용)"""
        if self.force_mock:
            return {
                "current_price": 50000.0,
                "change_rate": 2.5,
                "volume": 1000000,
                "market_cap": 1000000000000
            }
        
        try:
            # 현재가 조회 API 호출 (ka10001 등)
            api_id = config.kiwoom_tr_quote_id if hasattr(config, 'kiwoom_tr_quote_id') else "ka10001"
            path = config.kiwoom_tr_quote_path if hasattr(config, 'kiwoom_tr_quote_path') else "/api/dostk/krinfo"
            
            payload = {
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_INPUT_ISCD": code
            }
            data = self._post(api_id, path, payload)
            
            # API 응답에서 필요한 데이터 추출
            output = data.get("output") or {}
            
            current_price = float(output.get("stck_prpr") or 0)
            change_rate = round(float(output.get("prdy_ctrt") or 0), 2)
            volume = int(output.get("acml_vol") or 0)
            market_cap = int(output.get("hts_avls") or 0)
            
            return {
                "current_price": current_price,
                "change_rate": change_rate,
                "volume": volume,
                "market_cap": market_cap
            }
                
        except Exception as e:
            print(f"⚠️ {code} 종목 정보 조회 실패: {e}")
            # API 실패 시 OHLCV 데이터로 폴백 (등락률 계산 없이)
            try:
                df = self.get_ohlcv(code, 1)
                if not df.empty:
                    latest = df.iloc[-1]
                    return {
                        "current_price": float(latest["close"]),
                        "change_rate": 0.0,  # 등락률은 계산하지 않음
                        "volume": int(latest["volume"]),
                        "market_cap": 0
                    }
            except:
                pass
            return {"error": str(e)}

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
        # 브랜드 약어/발음 표준화
        norm_map = {
            "sk": "에스케이",
            "lg": "엘지",
            "kt": "케이티",
            "cj": "씨제이",
            "posco": "포스코",
        }
        low = key.lower()
        for abbr, full in norm_map.items():
            if low.startswith(abbr):
                key = key.replace(key[:len(abbr)], full)
                break
        # 자주 쓰는 별칭
        alias = {
            "sk이노베이션": "096770",
            "에스케이이노베이션": "096770",
        }
        if key in alias:
            return alias[key]
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


# 전역 API 인스턴스
api = KiwoomAPI()



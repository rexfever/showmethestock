import time
from datetime import datetime
import os
from typing import List, Dict, Optional, Tuple
import requests
import pandas as pd
import numpy as np
import pickle
from pathlib import Path
import logging

from auth import KiwoomAuth
from config import config

logger = logging.getLogger(__name__)


class KiwoomAPI:
    """KIS OpenAPI v2 래퍼 (실데이터 기본, 필요 시 모의 폴백)"""

    def __init__(self):
        self.auth = KiwoomAuth()
        self._code_to_name: Dict[str, str] = {}
        self._name_to_code: Dict[str, str] = {}
        # OHLCV 캐시: {(code, count, base_dt, hour_key): (df, timestamp)}
        # hour_key: 장중일 때만 시간대 구분 (예: "15:00"), 장 마감 후는 None
        self._ohlcv_cache: Dict[Tuple[str, int, Optional[str], Optional[str]], Tuple[pd.DataFrame, float]] = {}
        self._cache_ttl = 300  # 기본 5분 (초) - 상황에 따라 동적으로 계산됨
        self._cache_maxsize = 1000  # 최대 캐시 항목 수
        
        # 디스크 캐시 설정
        self._disk_cache_dir = Path("cache/ohlcv")
        self._disk_cache_dir.mkdir(parents=True, exist_ok=True)
        self._disk_cache_enabled = True  # 디스크 캐시 활성화 여부
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

    def _get_cache_key(self, code: str, count: int, base_dt: Optional[str]) -> Tuple[str, int, Optional[str], Optional[str]]:
        """캐시 키 생성
        
        base_dt가 None인 경우, 시간대별로 구분하여 캐싱
        - 08:00 ~ 20:00: 시간별 구분 (애프터마켓 포함, 주가 변동 가능)
        - 20:00 ~ 08:00: 당일로 통합 (데이터 변경 없음)
        """
        # base_dt가 None인 경우
        if base_dt is None:
            from datetime import datetime
            import pytz
            KST = pytz.timezone('Asia/Seoul')
            now = datetime.now(KST)
            hour = now.hour
            
            # 08:00 ~ 20:00: 시간대별 구분 (애프터마켓 포함)
            if 8 <= hour < 20:
                hour_key = f"{now.hour:02d}:{now.minute // 10 * 10:02d}"  # 10분 단위
                return (code, count, base_dt, hour_key)
            # 20:00 ~ 08:00: 당일로 통합
            else:
                return (code, count, base_dt, None)
        
        # base_dt가 명시된 경우: 날짜만 사용
        return (code, count, base_dt, None)
    
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
        
        # 현재 날짜: 시간대에 따라
        from datetime import datetime
        import pytz
        KST = pytz.timezone('Asia/Seoul')
        now = datetime.now(KST)
        hour = now.hour
        
        # 08:00 ~ 20:00: 애프터마켓 포함, 주가 변동 가능
        if 8 <= hour < 20:
            return 60  # 1분
        # 20:00 ~ 08:00: 데이터 변경 없음
        else:
            return self._get_ttl_until_next_trading_day()
    
    def _get_ttl_until_next_trading_day(self) -> int:
        """다음 거래일 시작 전까지의 TTL 계산"""
        from datetime import datetime, timedelta
        import pytz
        
        KST = pytz.timezone('Asia/Seoul')
        now = datetime.now(KST)
        
        # 다음 거래일 찾기
        next_date = now.date() + timedelta(days=1)
        
        # 공휴일 체크 (holidays 모듈이 있으면 사용)
        try:
            import holidays
            kr_holidays = holidays.SouthKorea()
            # 주말과 공휴일 제외
            while next_date.weekday() >= 5 or next_date in kr_holidays:
                next_date += timedelta(days=1)
        except ImportError:
            # holidays 모듈이 없으면 주말만 체크
            while next_date.weekday() >= 5:
                next_date += timedelta(days=1)
        
        # 다음 거래일 09:00까지의 시간 계산
        next_trading_day_start = KST.localize(
            datetime.combine(next_date, datetime.min.time().replace(hour=9))
        )
        
        # 현재 시간부터 다음 거래일 09:00까지의 초
        ttl_seconds = int((next_trading_day_start - now).total_seconds())
        
        # 최소 1시간, 최대 72시간 (주말 건너뛰는 경우)
        return max(3600, min(ttl_seconds, 72 * 3600))
    
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
    
    def _is_aftermarket_hours(self) -> bool:
        """애프터마켓 시간대 확인 (08:00 ~ 20:00)"""
        from datetime import datetime
        import pytz
        
        KST = pytz.timezone('Asia/Seoul')
        now = datetime.now(KST)
        hour = now.hour
        
        # 애프터마켓: 08:00 ~ 20:00 (장전 시간외 + 장중 + 장후 시간외)
        return 8 <= hour < 20
    
    def _get_cached_ohlcv(self, code: str, count: int, base_dt: Optional[str]) -> Optional[pd.DataFrame]:
        """캐시에서 OHLCV 데이터 조회"""
        cache_key = self._get_cache_key(code, count, base_dt)
        
        if cache_key not in self._ohlcv_cache:
            return None
        
        cached_df, timestamp = self._ohlcv_cache[cache_key]
        
        # base_dt가 None인 경우, DataFrame의 실제 날짜 확인
        actual_date = base_dt
        if actual_date is None and not cached_df.empty and 'date' in cached_df.columns:
            try:
                # DataFrame의 마지막 날짜 추출
                last_date_str = str(cached_df.iloc[-1]['date'])
                # YYYYMMDD 형식인지 확인
                if len(last_date_str) == 8 and last_date_str.isdigit():
                    actual_date = last_date_str
            except:
                pass
        
        # 실제 날짜를 사용하여 TTL 계산
        ttl = self._calculate_ttl(actual_date)
        
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
        # 메모리 캐시 클리어
        if code is None:
            self._ohlcv_cache.clear()
        else:
            # 특정 종목의 모든 캐시 항목 제거
            keys_to_remove = [
                key for key in self._ohlcv_cache.keys()
                if key[0] == code  # key[0] = code
            ]
            for key in keys_to_remove:
                del self._ohlcv_cache[key]
        
        # 디스크 캐시 클리어
        if code is None:
            # 전체 디스크 캐시 삭제
            for cache_file in self._disk_cache_dir.glob("*.pkl"):
                cache_file.unlink()
        else:
            # 특정 종목의 디스크 캐시 삭제
            pattern = f"{code}_*.pkl"
            for cache_file in self._disk_cache_dir.glob(pattern):
                cache_file.unlink()
    
    def get_ohlcv_cache_stats(self) -> Dict:
        """캐시 통계 반환"""
        current_time = time.time()
        valid_count = sum(
            1 for _, (_, timestamp) in self._ohlcv_cache.items()
            if current_time - timestamp <= self._cache_ttl
        )
        expired_count = len(self._ohlcv_cache) - valid_count
        
        # 디스크 캐시 통계
        disk_cache_files = list(self._disk_cache_dir.glob("*.pkl")) if self._disk_cache_enabled else []
        disk_cache_size = sum(f.stat().st_size for f in disk_cache_files) if disk_cache_files else 0
        
        # 기존 형식 유지 (하위 호환성)
        stats = {
            "total": len(self._ohlcv_cache),
            "valid": valid_count,
            "expired": expired_count,
            "maxsize": self._cache_maxsize,
            "ttl": self._cache_ttl,
            # 디스크 캐시 정보 추가
            "disk": {
                "enabled": self._disk_cache_enabled,
                "total_files": len(disk_cache_files),
                "total_size_bytes": disk_cache_size,
                "total_size_mb": round(disk_cache_size / (1024 * 1024), 2),
                "cache_dir": str(self._disk_cache_dir)
            }
        }
        
        return stats
    
    def get_ohlcv(self, code: str, count: int = 220, base_dt: str = None) -> pd.DataFrame:
        """일봉 OHLCV DataFrame(date, open, high, low, close, volume) 반환
        base_dt가 지정되면 해당 기준일을 마지막 행으로 하는 시계열을 우선 시도한다(YYYYMMDD).
        
        캐싱 적용:
        - 메모리 캐시 우선 확인
        - base_dt가 있는 경우: 해당 base_dt의 디스크 캐시 확인
        - base_dt가 None인 경우: 최신 디스크 캐시 확인 후 증분 업데이트
        - 캐시 미스 시 API 호출 후 메모리 + 디스크 저장
        """
        # 1. 메모리 캐시 확인
        cached_df = self._get_cached_ohlcv(code, count, base_dt)
        if cached_df is not None:
            return cached_df
        
        # 2. 디스크 캐시 확인
        if self._disk_cache_enabled:
            if base_dt:
                # base_dt가 지정된 경우: 해당 base_dt의 캐시 확인
                cached_df = self._load_from_disk_cache(code, count, base_dt)
                if cached_df is not None:
                    # 메모리 캐시에도 저장
                    self._set_cached_ohlcv(code, count, base_dt, cached_df)
                    return cached_df
            else:
                # base_dt가 None인 경우: 최신 디스크 캐시 찾아서 증분 업데이트
                cached_df, latest_base_dt = self._find_latest_disk_cache(code, count)
                if cached_df is not None:
                    # 캐시의 최신 날짜 확인
                    if 'date' in cached_df.columns:
                        cached_df['date'] = pd.to_datetime(cached_df['date'])
                        latest_cache_date = cached_df['date'].max()
                    else:
                        # date가 인덱스인 경우
                        if isinstance(cached_df.index, pd.DatetimeIndex):
                            latest_cache_date = cached_df.index.max()
                        else:
                            latest_cache_date = None
                    
                    # 오늘 날짜
                    today = pd.Timestamp.now().normalize()
                    
                    # 캐시의 최신 날짜가 오늘보다 오래된 경우에만 당일 데이터 추가
                    if latest_cache_date is not None and latest_cache_date < today:
                        logger.debug(f"{code} 캐시가 오래됨 (최신: {latest_cache_date.date()}, 오늘: {today.date()}), 당일 데이터 추가")
                        # 당일 데이터만 API로 가져오기
                        today_data = self._fetch_today_data_from_api(code)
                        if not today_data.empty:
                            # 기존 데이터와 병합
                            combined = pd.concat([cached_df, today_data])
                            # 중복 제거 (최신 데이터 우선)
                            if 'date' in combined.columns:
                                combined = combined.drop_duplicates(subset=['date'], keep='last')
                                combined = combined.sort_values('date').reset_index(drop=True)
                            else:
                                combined = combined[~combined.index.duplicated(keep='last')]
                                combined = combined.sort_index()
                            
                            # count만큼만 반환
                            if len(combined) > count:
                                combined = combined.tail(count)
                            
                            # 메모리 캐시 저장
                            self._set_cached_ohlcv(code, count, base_dt, combined)
                            
                            # 디스크 캐시 업데이트
                            # combined의 최신 날짜를 base_dt로 사용
                            if 'date' in combined.columns:
                                combined_latest_date = pd.to_datetime(combined['date']).max()
                            elif isinstance(combined.index, pd.DatetimeIndex):
                                combined_latest_date = combined.index.max()
                            else:
                                combined_latest_date = None
                            
                            if combined_latest_date is not None:
                                # 과거 날짜인 경우만 디스크 캐시 저장
                                today = pd.Timestamp.now().normalize()
                                if combined_latest_date < today:
                                    combined_base_dt = combined_latest_date.strftime('%Y%m%d')
                                    self._save_to_disk_cache(code, count, combined_base_dt, combined)
                            
                            return combined
                    
                    # 캐시가 최신이면 그대로 반환
                    if len(cached_df) >= count:
                        result = cached_df.tail(count)
                        # 메모리 캐시에도 저장
                        self._set_cached_ohlcv(code, count, base_dt, result)
                        return result
        
        # 3. 캐시 미스: API 호출
        if self.force_mock:
            df = self._gen_mock_ohlcv(code, count, base_dt)
        else:
            try:
                df = self._fetch_ohlcv_from_api(code, count, base_dt)
            except RuntimeError as e:
                # 키움 API 인증 실패 시 디스크 캐시 재시도
                if "인증에 실패" in str(e) or "Token error" in str(e):
                    logger.warning(f"키움 API 인증 실패, 디스크 캐시 재시도: {code}")
                    if base_dt and self._disk_cache_enabled:
                        # base_dt가 있는 경우: 해당 base_dt의 캐시 재시도
                        cached_df = self._load_from_disk_cache(code, count, base_dt)
                        if cached_df is not None and not cached_df.empty:
                            logger.info(f"디스크 캐시에서 로드 성공: {code}, {base_dt}")
                            self._set_cached_ohlcv(code, count, base_dt, cached_df)
                            return cached_df
                    # base_dt가 None인 경우: 최신 디스크 캐시 재시도
                    if not base_dt and self._disk_cache_enabled:
                        cached_df, _ = self._find_latest_disk_cache(code, count)
                        if cached_df is not None and not cached_df.empty:
                            logger.info(f"최신 디스크 캐시에서 로드 성공: {code}")
                            result = cached_df.tail(count) if len(cached_df) >= count else cached_df
                            self._set_cached_ohlcv(code, count, base_dt, result)
                            return result
                    logger.error(f"디스크 캐시도 없음, API 인증 실패: {code}, {e}")
                raise
        
        # 4. 캐시 저장 (메모리 + 디스크)
        if not df.empty:
            self._set_cached_ohlcv(code, count, base_dt, df)
            # base_dt가 있는 경우 디스크에도 저장 (과거 날짜)
            if base_dt and self._disk_cache_enabled:
                self._save_to_disk_cache(code, count, base_dt, df)
            elif base_dt is None and self._disk_cache_enabled:
                # base_dt가 None인 경우: DataFrame의 최신 날짜를 base_dt로 사용
                if 'date' in df.columns:
                    latest_date = pd.to_datetime(df['date']).max()
                elif isinstance(df.index, pd.DatetimeIndex):
                    latest_date = df.index.max()
                else:
                    latest_date = None
                
                if latest_date is not None:
                    # 과거 날짜인 경우만 디스크 캐시 저장
                    today = pd.Timestamp.now().normalize()
                    if latest_date < today:
                        base_dt_str = latest_date.strftime('%Y%m%d')
                        self._save_to_disk_cache(code, count, base_dt_str, df)
        
        return df
    
    def _get_disk_cache_file_path(self, code: str, count: int, base_dt: str) -> Path:
        """디스크 캐시 파일 경로 생성
        
        Args:
            code: 종목 코드
            count: 데이터 개수
            base_dt: 기준일 (YYYYMMDD)
        
        Returns:
            캐시 파일 경로
        """
        # 파일명: {code}_{count}_{base_dt}.pkl
        filename = f"{code}_{count}_{base_dt}.pkl"
        return self._disk_cache_dir / filename
    
    def _load_from_disk_cache(self, code: str, count: int, base_dt: str) -> Optional[pd.DataFrame]:
        """디스크 캐시에서 OHLCV 데이터 로드
        
        Args:
            code: 종목 코드
            count: 데이터 개수
            base_dt: 기준일 (YYYYMMDD)
        
        Returns:
            DataFrame 또는 None (캐시 없음/만료)
        """
        if not self._disk_cache_enabled:
            return None
        
        cache_file = self._get_disk_cache_file_path(code, count, base_dt)
        
        if not cache_file.exists():
            return None
        
        try:
            # 파일에서 로드
            with open(cache_file, 'rb') as f:
                cached_data = pickle.load(f)
                df, timestamp = cached_data
            
            # TTL 확인 (과거 날짜는 1년)
            ttl = self._calculate_ttl(base_dt)
            if time.time() - timestamp > ttl:
                # 만료된 캐시 삭제
                cache_file.unlink()
                return None
            
            # 복사본 반환
            return df.copy()
        except Exception as e:
            # 로드 실패 시 파일 삭제
            try:
                cache_file.unlink()
            except:
                pass
            return None
    
    def _find_latest_disk_cache(self, code: str, count: int) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        """최신 디스크 캐시 찾기 (base_dt=None일 때 사용)
        
        Args:
            code: 종목 코드
            count: 데이터 개수
        
        Returns:
            (DataFrame, base_dt) 또는 (None, None)
        """
        if not self._disk_cache_enabled:
            return None, None
        
        try:
            # 캐시 디렉토리에서 해당 종목의 모든 캐시 파일 찾기
            pattern = f"{code}_{count}_*.pkl"
            cache_files = list(self._disk_cache_dir.glob(pattern))
            
            if not cache_files:
                return None, None
            
            # base_dt 기준으로 정렬 (최신 날짜 우선)
            cache_files_with_dt = []
            for cache_file in cache_files:
                try:
                    # 파일명에서 base_dt 추출: {code}_{count}_{base_dt}.pkl
                    base_dt = cache_file.stem.split('_')[-1]
                    if len(base_dt) == 8 and base_dt.isdigit():
                        cache_files_with_dt.append((cache_file, base_dt))
                except:
                    continue
            
            if not cache_files_with_dt:
                return None, None
            
            # base_dt 기준 내림차순 정렬 (최신 날짜 우선)
            cache_files_with_dt.sort(key=lambda x: x[1], reverse=True)
            
            # 최신 캐시 파일 로드 시도
            for cache_file, base_dt in cache_files_with_dt:
                try:
                    with open(cache_file, 'rb') as f:
                        cached_data = pickle.load(f)
                        df, timestamp = cached_data
                    
                    # TTL 확인 (과거 날짜는 1년)
                    ttl = self._calculate_ttl(base_dt)
                    if time.time() - timestamp > ttl:
                        # 만료된 캐시는 건너뛰기
                        continue
                    
                    # 복사본 반환
                    return df.copy(), base_dt
                except Exception as e:
                    logger.debug(f"{code} 캐시 파일 로드 실패: {cache_file}, {e}")
                    continue
            
            return None, None
        except Exception as e:
            logger.debug(f"{code} 최신 캐시 찾기 실패: {e}")
            return None, None
    
    def _fetch_today_data_from_api(self, code: str) -> pd.DataFrame:
        """당일 데이터만 API로 가져오기
        
        Args:
            code: 종목 코드
        
        Returns:
            DataFrame (당일 데이터만, 비어있을 수 있음)
        """
        try:
            # 최근 5일 데이터를 가져와서 당일 데이터만 필터링
            df = self._fetch_ohlcv_from_api(code, count=5, base_dt=None)
            if df.empty:
                return df
            
            # 오늘 날짜
            today = pd.Timestamp.now().normalize()
            
            # date 컬럼이 있는 경우
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                today_df = df[df['date'].dt.normalize() == today]
            # date가 인덱스인 경우
            elif isinstance(df.index, pd.DatetimeIndex):
                today_df = df[df.index.normalize() == today]
            else:
                # date 정보가 없으면 빈 DataFrame 반환
                return pd.DataFrame()
            
            return today_df
        except Exception as e:
            logger.warning(f"{code} 당일 데이터 가져오기 실패: {e}")
            return pd.DataFrame()
    
    def _save_to_disk_cache(self, code: str, count: int, base_dt: str, df: pd.DataFrame) -> None:
        """디스크 캐시에 OHLCV 데이터 저장
        
        Args:
            code: 종목 코드
            count: 데이터 개수
            base_dt: 기준일 (YYYYMMDD)
            df: DataFrame
        """
        if not self._disk_cache_enabled or df.empty:
            return
        
        # base_dt가 과거 날짜인 경우만 디스크 캐시 저장
        try:
            from datetime import datetime
            base_date = datetime.strptime(base_dt, "%Y%m%d").date()
            now_date = datetime.now().date()
            
            # 현재 날짜 또는 미래 날짜는 디스크 캐시 저장 안 함
            if base_date >= now_date:
                return
        except:
            # 날짜 파싱 실패 시 저장 안 함
            return
        
        cache_file = self._get_disk_cache_file_path(code, count, base_dt)
        
        try:
            # 디렉토리 생성 (이미 있지만 안전을 위해)
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 파일에 저장
            with open(cache_file, 'wb') as f:
                pickle.dump((df.copy(), time.time()), f)
        except Exception:
            # 저장 실패해도 계속 진행 (디스크 문제 등)
            pass
    
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

    def get_overseas_ohlcv(self, symbol: str, count: int = 220, base_dt: str = None) -> pd.DataFrame:
        """해외주식 일봉 OHLCV 조회 (미국 주식/ETF/지수)"""
        if self.force_mock:
            return self._gen_mock_overseas_ohlcv(symbol, count, base_dt)
        
        try:
            # 해외주식 일봉 조회 API (예: ka10082)
            api_id = getattr(config, 'kiwoom_tr_overseas_ohlcv_id', 'ka10082')
            path = getattr(config, 'kiwoom_tr_overseas_ohlcv_path', '/api/dostk/overseas')
            
            # 미국 주식 심볼 매핑
            symbol_map = {
                'SPY': 'SPY',
                'QQQ': 'QQQ', 
                '^VIX': 'VIX',
                'VIX': 'VIX',
                '^TNX': 'TNX',
                'TNX': 'TNX',
                'ES=F': 'ES',
                'NQ=F': 'NQ',
                'VX=F': 'VX',
                'KRW=X': 'USDKRW'
            }
            
            overseas_symbol = symbol_map.get(symbol, symbol)
            
            payload = {
                'symbol': overseas_symbol,
                'market': 'US',  # 미국 시장
                'period': 'D',   # 일봉
                'count': str(count)
            }
            
            if base_dt:
                payload['end_date'] = base_dt
            
            data = self._post(api_id, path, payload)
            
            # 응답 데이터 파싱
            rows = data.get('output', []) or data.get('data', []) or data.get('list', [])
            
            if not rows:
                return pd.DataFrame()
            
            df_data = []
            for row in rows:
                df_data.append({
                    'date': row.get('date') or row.get('dt') or row.get('trade_date'),
                    'open': float(row.get('open') or row.get('open_price') or 0),
                    'high': float(row.get('high') or row.get('high_price') or 0),
                    'low': float(row.get('low') or row.get('low_price') or 0),
                    'close': float(row.get('close') or row.get('close_price') or 0),
                    'volume': int(row.get('volume') or row.get('trade_volume') or 0)
                })
            
            df = pd.DataFrame(df_data)
            
            if df.empty:
                return df
            
            # 유효 데이터 필터링
            df = df[(df['close'] > 0) & (df['volume'] > 0)]
            
            # 날짜 정렬
            df = df.sort_values('date').reset_index(drop=True).tail(count)
            
            return df
            
        except Exception as e:
            # API 실패 시 모의 데이터로 fallback
            return self._gen_mock_overseas_ohlcv(symbol, count, base_dt)
    
    def _gen_mock_overseas_ohlcv(self, symbol: str, count: int, base_dt: str = None) -> pd.DataFrame:
        """해외주식 모의 데이터 생성"""
        import numpy as np
        
        # 시드 설정
        seed = hash(symbol) % 1000
        np.random.seed(seed)
        
        # 기준 날짜 설정
        if base_dt:
            try:
                end_date = pd.to_datetime(base_dt, format='%Y%m%d').normalize()
            except:
                end_date = pd.Timestamp.today().normalize()
        else:
            end_date = pd.Timestamp.today().normalize()
        
        # 영업일 기준 날짜 생성
        dates = pd.bdate_range(end=end_date, periods=count)
        
        # 심볼별 기본 가격 및 특성
        symbol_config = {
            'SPY': {'base_price': 450.0, 'volatility': 0.015, 'trend': 0.0005},
            'QQQ': {'base_price': 380.0, 'volatility': 0.020, 'trend': 0.0008},
            '^VIX': {'base_price': 20.0, 'volatility': 0.05, 'trend': -0.001, 'mean_revert': True},
            'VIX': {'base_price': 20.0, 'volatility': 0.05, 'trend': -0.001, 'mean_revert': True},
            '^TNX': {'base_price': 4.5, 'volatility': 0.02, 'trend': 0.0002},
            'TNX': {'base_price': 4.5, 'volatility': 0.02, 'trend': 0.0002},
            'ES=F': {'base_price': 4500.0, 'volatility': 0.018, 'trend': 0.0005},
            'NQ=F': {'base_price': 15000.0, 'volatility': 0.022, 'trend': 0.0008},
            'VX=F': {'base_price': 20.0, 'volatility': 0.05, 'trend': -0.001, 'mean_revert': True},
            'KRW=X': {'base_price': 1300.0, 'volatility': 0.008, 'trend': 0.0001}
        }
        
        config = symbol_config.get(symbol, {'base_price': 100.0, 'volatility': 0.015, 'trend': 0.0})
        
        # 가격 시계열 생성
        returns = np.random.normal(config['trend'], config['volatility'], len(dates))
        
        # VIX 계열은 평균 회귀 특성 적용
        if config.get('mean_revert'):
            for i in range(1, len(returns)):
                current_price = config['base_price'] * np.exp(returns[:i].sum())
                if current_price > 35:  # VIX 35 이상에서 하락 압력
                    returns[i] = -abs(returns[i])
                elif current_price < 12:  # VIX 12 이하에서 상승 압력
                    returns[i] = abs(returns[i])
        
        # 누적 수익률로 가격 계산
        prices = config['base_price'] * np.exp(np.cumsum(returns))
        
        # OHLCV 데이터 생성
        data = []
        for i, (date, close) in enumerate(zip(dates, prices)):
            daily_vol = np.random.uniform(0.005, 0.02)
            high = close * (1 + daily_vol)
            low = close * (1 - daily_vol)
            open_price = close * (1 + np.random.uniform(-0.01, 0.01))
            
            # 거래량 (심볼별 차등)
            if 'VIX' in symbol or 'VX' in symbol:
                volume = int(np.random.uniform(50000, 500000))  # VIX는 거래량 적음
            elif symbol in ['SPY', 'QQQ']:
                volume = int(np.random.uniform(10000000, 100000000))  # ETF는 거래량 많음
            else:
                volume = int(np.random.uniform(1000000, 10000000))
            
            data.append({
                'date': date.strftime('%Y%m%d'),
                'open': round(open_price, 2),
                'high': round(high, 2),
                'low': round(low, 2),
                'close': round(close, 2),
                'volume': volume
            })
        
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
        
        return df

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



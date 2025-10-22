"""
리팩토링된 스캔 서비스
main.py의 긴 scan 함수를 여러 개의 작은 함수로 분리
"""
import os
import json
import sqlite3
from typing import List, Optional, Dict
from datetime import datetime

from config import config
from kiwoom_api import KiwoomAPI
from models import ScanResponse, ScanItem, IndicatorPayload, TrendPayload, ScoreFlags
from services.scan_service import execute_scan_with_fallback
from services.returns_service import calculate_returns_batch


def _db_path() -> str:
    """데이터베이스 파일 경로 반환"""
    return os.path.join(os.path.dirname(__file__), 'snapshots.db')


def _parse_date(date_str: str) -> str:
    """날짜 문자열을 YYYY-MM-DD 형식으로 변환"""
    if not date_str:
        return datetime.now().strftime("%Y%m%d")
    
    try:
        if len(date_str) == 8 and date_str.isdigit():  # YYYYMMDD 형식
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        elif len(date_str) == 10 and date_str.count('-') == 2:  # YYYY-MM-DD 형식
            return date_str
        else:
            raise ValueError("날짜 형식이 올바르지 않습니다.")
    except Exception:
        return datetime.now().strftime("%Y%m%d")


def _get_universe(api: KiwoomAPI, kospi_limit: int, kosdaq_limit: int) -> List[str]:
    """유니버스 종목 리스트 가져오기"""
    kp = kospi_limit or config.universe_kospi
    kd = kosdaq_limit or config.universe_kosdaq
    kospi = api.get_top_codes('KOSPI', kp)
    kosdaq = api.get_top_codes('KOSDAQ', kd)
    return [*kospi, *kosdaq]


def _create_scan_items(items: List[Dict], returns_data: Optional[Dict], date: Optional[str]) -> List[ScanItem]:
    """스캔 결과를 ScanItem 객체 리스트로 변환"""
    scan_items: List[ScanItem] = []
    
    for item in items:
        try:
            ticker = item["ticker"]
            returns = returns_data.get(ticker) if date else None
            
            scan_item = ScanItem(
                ticker=ticker,
                name=item["name"],
                match=item["match"],
                score=item["score"],
                indicators=IndicatorPayload(
                    TEMA=item["indicators"]["TEMA"],
                    DEMA=item["indicators"]["DEMA"],
                    MACD_OSC=item["indicators"]["MACD_OSC"],
                    MACD_LINE=item["indicators"]["MACD_LINE"],
                    MACD_SIGNAL=item["indicators"]["MACD_SIGNAL"],
                    RSI_TEMA=item["indicators"]["RSI_TEMA"],
                    RSI_DEMA=item["indicators"]["RSI_DEMA"],
                    OBV=item["indicators"]["OBV"],
                    VOL=item["indicators"]["VOL"],
                    VOL_MA5=item["indicators"]["VOL_MA5"],
                    close=item["indicators"]["close"],
                ),
                trend=TrendPayload(
                    TEMA20_SLOPE20=item["trend"]["TEMA20_SLOPE20"],
                    OBV_SLOPE20=item["trend"]["OBV_SLOPE20"],
                    ABOVE_CNT5=item["trend"]["ABOVE_CNT5"],
                    DEMA10_SLOPE20=item["trend"]["DEMA10_SLOPE20"],
                ),
                flags=_as_score_flags(item["flags"]),
                score_label=item["score_label"],
                details={**item["flags"].get("details", {}), "close": item["indicators"]["close"]},
                strategy=item["strategy"],
                returns=returns,
            )
            scan_items.append(scan_item)
        except Exception as e:
            print(f"ScanItem 생성 오류 ({item.get('ticker', 'unknown')}): {e}")
            continue
    
    return scan_items


def _as_score_flags(flags_dict: Dict) -> ScoreFlags:
    """딕셔너리를 ScoreFlags 객체로 변환"""
    return ScoreFlags(
        cross=flags_dict.get("cross", False),
        vol_expand=flags_dict.get("vol_expand", False),
        macd_ok=flags_dict.get("macd_ok", False),
        rsi_dema_setup=flags_dict.get("rsi_dema_setup", False),
        rsi_tema_trigger=flags_dict.get("rsi_tema_trigger", False),
        rsi_dema_value=flags_dict.get("rsi_dema_value"),
        rsi_tema_value=flags_dict.get("rsi_tema_value"),
        overheated_rsi_tema=flags_dict.get("overheated_rsi_tema", False),
        tema_slope_ok=flags_dict.get("tema_slope_ok", False),
        obv_slope_ok=flags_dict.get("obv_slope_ok", False),
        above_cnt5_ok=flags_dict.get("above_cnt5_ok", False),
        dema_slope_ok=flags_dict.get("dema_slope_ok", False),
        details=flags_dict.get("details", {})
    )


def _create_scan_response(scan_items: List[ScanItem], universe: List[str], 
                         today_as_of: str, chosen_step: int, 
                         market_condition) -> ScanResponse:
    """ScanResponse 객체 생성"""
    return ScanResponse(
        as_of=today_as_of,
        universe_count=len(universe),
        matched_count=len(scan_items),
        rsi_mode="tema_dema",
        rsi_period=14,
        rsi_threshold=market_condition.rsi_threshold if market_condition else config.rsi_setup_min,
        items=scan_items,
        fallback_step=chosen_step if config.fallback_enable else None,
        score_weights=getattr(config, 'dynamic_score_weights')() if hasattr(config, 'dynamic_score_weights') else {},
        score_level_strong=config.score_level_strong,
        score_level_watch=config.score_level_watch,
        require_dema_slope=getattr(config, 'require_dema_slope', 'required'),
    )


def _save_snapshot_db(as_of: str, items: List[ScanItem], api: KiwoomAPI):
    """스캔 결과를 데이터베이스에 저장"""
    try:
        print(f"💾 데이터베이스 저장 시작: {as_of}, {len(items)}개 항목")
        conn = sqlite3.connect(_db_path())
        cur = conn.cursor()
        
        # 확장된 스키마로 테이블 생성
        cur.execute("""
            CREATE TABLE IF NOT EXISTS scan_rank(
                date TEXT, 
                code TEXT, 
                name TEXT, 
                score REAL, 
                score_label TEXT,
                current_price REAL,
                volume REAL,
                change_rate REAL,
                market TEXT,
                strategy TEXT,
                indicators TEXT,
                trend TEXT,
                flags TEXT,
                details TEXT,
                returns TEXT,
                recurrence TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(date, code)
            )
        """)
        
        # 기존 데이터 삭제 (같은 날짜)
        cur.execute("DELETE FROM scan_rank WHERE date = ?", (as_of,))
        
        rows = []
        for it in items:
            # 모든 필드를 JSON으로 저장
            indicators_json = json.dumps(it.indicators.__dict__ if hasattr(it.indicators, '__dict__') else {}, ensure_ascii=False)
            trend_json = json.dumps(it.trend.__dict__ if hasattr(it.trend, '__dict__') else {}, ensure_ascii=False)
            flags_json = json.dumps(it.flags.__dict__ if hasattr(it.flags, '__dict__') else {}, ensure_ascii=False)
            details_json = json.dumps(getattr(it, 'details', {}), ensure_ascii=False)
            returns_json = json.dumps(getattr(it, 'returns', None), ensure_ascii=False)
            recurrence_json = json.dumps(getattr(it, 'recurrence', None), ensure_ascii=False)
            
            # 키움 API에서 종목 정보 직접 조회 (등락률 포함)
            try:
                quote = api.get_stock_quote(it.ticker)
                if "error" not in quote:
                    # 키움 API에서 현재가와 등락률 가져오기
                    current_price = quote.get("current_price", 0)
                    volume = quote.get("volume", 0)
                    change_rate = quote.get("change_rate", None)
                    
                    # current_price가 0이면 indicators에서 가져오기
                    if current_price == 0:
                        current_price = float(it.indicators.close if hasattr(it.indicators, 'close') else 0)
                        volume = int(it.indicators.VOL if hasattr(it.indicators, 'VOL') else 0)
                        change_rate = None
                else:
                    # API 실패 시 indicators에서 가져오기
                    current_price = float(it.indicators.close if hasattr(it.indicators, 'close') else 0)
                    volume = int(it.indicators.VOL if hasattr(it.indicators, 'VOL') else 0)
                    change_rate = None  # 데이터 없음
            except Exception as e:
                print(f"⚠️ {it.ticker} 데이터 가져오기 실패: {e}")
                # 실패 시 indicators에서 가져오기
                current_price = float(it.indicators.close if hasattr(it.indicators, 'close') else 0)
                volume = int(it.indicators.VOL if hasattr(it.indicators, 'VOL') else 0)
                change_rate = None  # 데이터 없음
            
            rows.append((
                as_of, 
                it.ticker, 
                it.name, 
                float(it.score), 
                it.score_label or '',
                current_price,
                volume,
                change_rate,
                getattr(it, 'market', ''),
                it.strategy or '',
                indicators_json,
                trend_json,
                flags_json,
                details_json,
                returns_json,
                recurrence_json
            ))
        
        print(f"💾 {len(rows)}개 레코드 삽입 시도")
        cur.executemany("""
            INSERT INTO scan_rank(
                date, code, name, score, score_label, current_price, volume, 
                change_rate, market, strategy, indicators, trend, flags, 
                details, returns, recurrence
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, rows)
        
        conn.commit()
        conn.close()
        print(f"✅ 데이터베이스 저장 완료: {as_of}")
        
    except Exception as e:
        print(f"❌ 데이터베이스 저장 오류: {e}")


def execute_scan(kospi_limit: int = None, kosdaq_limit: int = None, 
                save_snapshot: bool = True, sort_by: str = 'score', 
                date: str = None, api: KiwoomAPI = None) -> ScanResponse:
    """스캔 실행 메인 함수"""
    print(f"🔍 스캔 API 호출: save_snapshot={save_snapshot}, date={date}")
    
    # API 인스턴스 생성
    if api is None:
        api = KiwoomAPI()
    
    # 날짜 처리
    today_as_of = _parse_date(date)
    
    # 유니버스 가져오기
    universe = _get_universe(api, kospi_limit, kosdaq_limit)
    
    # 시장 분석
    market_condition = None
    if hasattr(config, 'market_analysis_enabled') and config.market_analysis_enabled:
        try:
            from market_analyzer import market_analyzer
            market_condition = market_analyzer()
        except Exception as e:
            print(f"⚠️ 시장 분석 실패: {e}")
    
    # 스캔 실행
    scan_result = execute_scan_with_fallback(
        universe=universe,
        date=today_as_of,
        market_condition=market_condition
    )
    
    items, chosen_step = scan_result
    
    # 수익률 데이터 계산 (과거 날짜인 경우)
    returns_data = None
    if date:
        try:
            returns_data = calculate_returns_batch([item["ticker"] for item in items], today_as_of)
        except Exception as e:
            print(f"⚠️ 수익률 계산 실패: {e}")
    
    # ScanItem 객체 생성
    scan_items = _create_scan_items(items, returns_data, date)
    
    # ScanResponse 생성
    resp = _create_scan_response(scan_items, universe, today_as_of, chosen_step, market_condition)
    
    # DB 저장 (필요한 경우)
    if save_snapshot:
        print(f"🔍 save_snapshot 조건 확인: {save_snapshot} (타입: {type(save_snapshot)})")
        print(f"✅ save_snapshot=True, DB 저장 시작")
        print(f"📊 저장할 scan_items 개수: {len(scan_items)}")
        _save_snapshot_db(resp.as_of, scan_items, api)
    
    return resp







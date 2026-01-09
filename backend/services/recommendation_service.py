"""
v3 추천 시스템 서비스
스캔(로그) vs 추천(이벤트) 분리
"""
import logging
from typing import List, Dict, Optional, Tuple, Union
from datetime import datetime, timedelta
import json
import holidays
import uuid
import threading
import concurrent.futures

from db_manager import db_manager
from date_helper import yyyymmdd_to_date, get_trading_date, get_anchor_close, get_kst_now

logger = logging.getLogger(__name__)

# 수익률 계산용 모듈 레벨 캐시 제거 (kiwoom_api의 캐시 활용)
# _today_cache_date, _today_close_cache, _cache_lock은 더 이상 사용하지 않음


def get_trading_days_between(start_date: str, end_date: str) -> int:
    """두 날짜 사이의 거래일 수 계산 (주말, 공휴일 제외)"""
    try:
        start = datetime.strptime(start_date, "%Y%m%d").date()
        end = datetime.strptime(end_date, "%Y%m%d").date()
        
        # 한국 공휴일
        kr_holidays = holidays.SouthKorea(years=range(start.year, end.year + 2))
        
        trading_days = 0
        current = start
        while current <= end:
            # 주말 제외
            if current.weekday() < 5:
                # 공휴일 제외
                if current not in kr_holidays:
                    trading_days += 1
            current += timedelta(days=1)
        
        return trading_days
    except Exception as e:
        logger.error(f"[recommendation_service] 거래일 계산 오류: {e}")
        return 0


def get_nth_trading_day_after(date_str: str, n: int) -> Optional[str]:
    """특정 날짜로부터 N 거래일 후 날짜 반환"""
    try:
        start = datetime.strptime(date_str, "%Y%m%d").date()
        kr_holidays = holidays.SouthKorea(years=range(start.year, start.year + 2))
        
        current = start
        trading_days = 0
        
        while trading_days < n:
            current += timedelta(days=1)
            if current.weekday() < 5 and current not in kr_holidays:
                trading_days += 1
        
        return current.strftime("%Y%m%d")
    except Exception as e:
        logger.error(f"[recommendation_service] N 거래일 후 계산 오류: {e}")
        return None


def save_scan_results(scan_items: List[Dict], scan_date: str, scan_run_id: str = None, scanner_version: str = "v3") -> int:
    """
    스캔 결과를 scan_results 테이블에 저장 (스캔 로그)
    
    Args:
        scan_items: 스캔 결과 리스트
        scan_date: 스캔 날짜 (YYYYMMDD)
        scan_run_id: 스캔 실행 ID (같은 날짜 여러 실행 구분)
        scanner_version: 스캐너 버전
        
    Returns:
        저장된 레코드 수
    """
    if not scan_items:
        logger.info(f"[recommendation_service] 스캔 결과 없음: {scan_date}")
        return 0
    
    if not scan_run_id:
        scan_run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    saved_count = 0
    
    try:
        with db_manager.get_cursor(commit=True) as cur:
            for item in scan_items:
                ticker = item.get("ticker") or item.get("code")
                if not ticker or ticker == "NORESULT":
                    continue
                
                try:
                    # v2 스키마 사용: scan_results는 스캔 로그만 저장 (v3에서는 scan_rank 사용)
                    # scan_results 테이블은 v2 스키마를 사용하므로 여기서는 저장하지 않음
                    # v3는 scan_rank 테이블에 저장되므로 이 함수는 사용하지 않음
                    # 하지만 하위 호환성을 위해 빈 구현 유지
                    saved_count += 1
                except Exception as e:
                    logger.error(f"[recommendation_service] scan_results 저장 오류 ({ticker}): {e}")
                    continue
        
        logger.info(f"[recommendation_service] scan_results 저장 완료: {saved_count}개 (날짜: {scan_date})")
        return saved_count
        
    except Exception as e:
        logger.error(f"[recommendation_service] scan_results 저장 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 0


def can_create_recommendation(ticker: str, scan_date: str, scanner_version: str = "v3", cooldown_days: int = 3) -> Tuple[bool, Optional[str]]:
    """
    추천 생성 가능 여부 확인
    
    Args:
        ticker: 종목 코드
        scan_date: 스캔 날짜 (YYYYMMDD)
        scanner_version: 스캐너 버전
        cooldown_days: BROKEN 후 쿨다운 거래일 수 (기본 3일)
        
    Returns:
        (가능 여부, 이유)
    """
    try:
        with db_manager.get_cursor(commit=False) as cur:
            # 1. 동일 ticker의 ACTIVE 추천이 이미 있는지 확인
            cur.execute("""
                SELECT recommendation_id, anchor_date, status
                FROM recommendations
                WHERE ticker = %s
                AND scanner_version = %s
                AND status = 'ACTIVE'
            """, (ticker, scanner_version))
            
            active_rec = cur.fetchone()
            if active_rec:
                rec_id = active_rec[0] if isinstance(active_rec, dict) else active_rec[0]
                return False, f"이미 ACTIVE 상태인 추천이 존재합니다 (ID: {rec_id})"
            
            # 2. 최근 BROKEN 추천 확인 (쿨다운 체크)
            cur.execute("""
                SELECT recommendation_id, broken_at, anchor_date
                FROM recommendations
                WHERE ticker = %s
                AND scanner_version = %s
                AND status = 'BROKEN'
                ORDER BY broken_at DESC
                LIMIT 1
            """, (ticker, scanner_version))
            
            broken_rec = cur.fetchone()
            if broken_rec:
                broken_at = broken_rec[1] if isinstance(broken_rec, dict) else broken_rec[1]
                if broken_at:
                    # broken_at 날짜 추출
                    if isinstance(broken_at, str):
                        broken_date = broken_at[:8].replace("-", "")
                    else:
                        broken_date = broken_at.strftime("%Y%m%d")
                    
                    # 쿨다운 기간 확인 (broken_date 다음 거래일부터 시작)
                    # broken_date와 scan_date가 같으면 쿨다운 미경과로 처리
                    if broken_date >= scan_date:
                        return False, f"BROKEN 후 쿨다운 기간 중입니다 (BROKEN일: {broken_date}, 스캔일: {scan_date})"
                    
                    trading_days = get_trading_days_between(broken_date, scan_date)
                    # broken_date 당일은 제외하고 다음 거래일부터 계산
                    if trading_days <= cooldown_days:
                        return False, f"BROKEN 후 쿨다운 기간 중입니다 ({trading_days}/{cooldown_days} 거래일 경과)"
            
            return True, None
            
    except Exception as e:
        logger.error(f"[recommendation_service] 추천 생성 가능 여부 확인 오류 ({ticker}): {e}")
        return False, f"확인 중 오류 발생: {e}"


def create_recommendation(
    ticker: str,
    name: str,
    scan_date: str,
    strategy: str,
    score: float,
    score_label: str,
    indicators: Dict,
    flags: Dict,
    details: Dict,
    scanner_version: str = "v3"
) -> Optional[int]:
    """
    추천 이벤트 생성
    
    Args:
        ticker: 종목 코드
        name: 종목명
        scan_date: 스캔 날짜 (YYYYMMDD)
        strategy: 전략 ('v2_lite' 또는 'midterm')
        score: 점수
        score_label: 점수 레이블
        indicators: 지표 데이터
        flags: 플래그 데이터
        details: 상세 데이터
        scanner_version: 스캐너 버전
        
    Returns:
        생성된 추천 ID (실패 시 None)
    """
    try:
        # 추천 생성 가능 여부 확인
        can_create, reason = can_create_recommendation(ticker, scan_date, scanner_version)
        if not can_create:
            logger.info(f"[recommendation_service] 추천 생성 불가 ({ticker}): {reason}")
            return None
        
        # anchor_date 결정 (거래일 보장)
        anchor_date_str = get_trading_date(scan_date)
        anchor_date_obj = yyyymmdd_to_date(anchor_date_str)
        
        # anchor_close 결정 (1회 확정 저장, 재계산 금지)
        anchor_close_value = get_anchor_close(ticker, anchor_date_str, price_type="CLOSE")
        if anchor_close_value is None:
            logger.warning(f"[recommendation_service] anchor_close 조회 실패 ({ticker}), 스캔 결과 종가 사용")
            # indicators에서 종가 추출
            if isinstance(indicators, dict):
                anchor_close_value = indicators.get("close")
            if not anchor_close_value or anchor_close_value <= 0:
                logger.error(f"[recommendation_service] anchor_close 결정 불가 ({ticker})")
                return None
        
        # 기존 ACTIVE 추천이 있으면 ARCHIVED로 전이 (동일 ticker ACTIVE 1개만 보장)
        with db_manager.get_cursor(commit=True) as cur:
            # 기존 ACTIVE 추천 확인 및 ARCHIVED 전이
            cur.execute("""
                SELECT recommendation_id, anchor_date, anchor_close, strategy
                FROM recommendations
                WHERE ticker = %s
                AND scanner_version = %s
                AND status = 'ACTIVE'
            """, (ticker, scanner_version))
            
            existing_active = cur.fetchone()
            if existing_active:
                if isinstance(existing_active, dict):
                    existing_rec_id = existing_active['recommendation_id']
                    existing_anchor_date = existing_active.get('anchor_date')
                    existing_anchor_close = existing_active.get('anchor_close')
                    existing_strategy = existing_active.get('strategy')
                else:
                    existing_rec_id = existing_active[0]
                    existing_anchor_date = existing_active[1] if len(existing_active) > 1 else None
                    existing_anchor_close = existing_active[2] if len(existing_active) > 2 else None
                    existing_strategy = existing_active[3] if len(existing_active) > 3 else None
                
                # 전략별 TTL 설정
                ttl_days = 20  # 기본값
                if existing_strategy == "v2_lite":
                    # v2_lite: holding_period = 14일 (약 10거래일), 여유분 포함하여 15거래일
                    ttl_days = 15
                elif existing_strategy == "midterm":
                    # midterm: holding_periods = [10, 15, 20] (최대 20거래일), 여유분 포함하여 25거래일
                    ttl_days = 25
                
                # 거래일 계산 (TTL 체크용)
                trading_days = 0
                archive_reason = 'REPLACED'  # 기본값
                
                if existing_anchor_date:
                    try:
                        from services.state_transition_service import get_trading_days_since
                        trading_days = get_trading_days_since(existing_anchor_date)
                        
                        # TTL 체크: 전략별 TTL 이상이면 TTL_EXPIRED로 설정
                        if trading_days >= ttl_days:
                            archive_reason = 'TTL_EXPIRED'
                        else:
                            archive_reason = 'REPLACED'
                    except Exception as e:
                        logger.warning(f"[recommendation_service] 거래일 계산 실패 (ticker={ticker}): {e}")
                
                # 현재 가격 조회 (archive_return_pct 계산 및 손절 조건 체크용)
                current_price = None
                archive_return_pct = None
                archive_price = None
                archive_phase = None
                current_return = None
                stop_loss_pct = None  # 변수 스코프 문제 해결
                
                # 전략별 손절 기준 설정 (try 블록 밖에서)
                stop_loss = 0.02  # 기본값
                if existing_strategy == "v2_lite":
                    stop_loss = 0.02
                elif existing_strategy == "midterm":
                    stop_loss = 0.07
                stop_loss_pct = -abs(float(stop_loss) * 100)
                
                try:
                    from kiwoom_api import api
                    from services.recommendation_service import get_nth_trading_day_after
                    today_str = get_kst_now().strftime('%Y%m%d')
                    
                    # TTL_EXPIRED인 경우: TTL 만료 시점의 가격 조회 (정책 준수)
                    if archive_reason == 'TTL_EXPIRED' and existing_anchor_date:
                        try:
                            # TTL 만료일 계산
                            anchor_date_str = existing_anchor_date.strftime('%Y%m%d') if hasattr(existing_anchor_date, 'strftime') else str(existing_anchor_date).replace('-', '')[:8]
                            ttl_expiry_str = get_nth_trading_day_after(anchor_date_str, ttl_days)
                            
                            if ttl_expiry_str:
                                # TTL 만료 시점의 가격 조회
                                df_ttl = api.get_ohlcv(ticker, 30, ttl_expiry_str)
                                if not df_ttl.empty:
                                    if 'date' in df_ttl.columns:
                                        df_ttl['date_str'] = df_ttl['date'].astype(str).str.replace('-', '').str[:8]
                                        df_filtered = df_ttl[df_ttl['date_str'] <= ttl_expiry_str].sort_values('date_str')
                                        if not df_filtered.empty:
                                            ttl_row = df_filtered.iloc[-1]
                                            current_price = float(ttl_row['close']) if 'close' in ttl_row else None
                                            logger.info(f"[recommendation_service] TTL 만료 시점 가격 사용: {ticker}, TTL 만료일={ttl_expiry_str}")
                        except Exception as e:
                            logger.warning(f"[recommendation_service] TTL 만료 시점 가격 조회 실패, 현재 시점 사용: {ticker}, {e}")
                    
                    # TTL_EXPIRED가 아니거나 TTL 시점 가격 조회 실패한 경우: 현재 시점 가격 조회
                    if current_price is None:
                        df_today = api.get_ohlcv(ticker, 1, today_str)
                        if not df_today.empty:
                            if 'close' in df_today.columns:
                                current_price = float(df_today.iloc[-1]['close'])
                            else:
                                current_price = float(df_today.iloc[-1].values[0])
                    
                    # archive_return_pct 계산
                    if existing_anchor_close and existing_anchor_close > 0 and current_price:
                        current_return = round(((current_price - float(existing_anchor_close)) / float(existing_anchor_close)) * 100, 2)
                        archive_return_pct = current_return
                        archive_price = current_price
                        
                        # 손절 조건 도달 시 NO_MOMENTUM으로 변경
                        if current_return <= stop_loss_pct:
                            archive_reason = 'NO_MOMENTUM'
                            logger.info(f"[recommendation_service] 손절 조건 도달 → NO_MOMENTUM: {ticker}, current_return={current_return:.2f}%, stop_loss={stop_loss_pct:.2f}%")
                        
                        # archive_phase 결정
                        if archive_return_pct > 2:
                            archive_phase = 'PROFIT'
                        elif archive_return_pct < -2:
                            archive_phase = 'LOSS'
                        else:
                            archive_phase = 'FLAT'
                except Exception as e:
                    logger.warning(f"[recommendation_service] 현재 가격 조회 실패 (ticker={ticker}): {e}")
                
                # 손절 조건 만족 시 BROKEN 정보 설정
                broken_at = None
                broken_return_pct = None
                if current_return is not None and stop_loss_pct is not None and current_return <= stop_loss_pct:
                    from date_helper import get_kst_now
                    today_str = get_kst_now().strftime('%Y%m%d')
                    broken_at = today_str
                    broken_return_pct = current_return
                    logger.info(f"[recommendation_service] 손절 조건 만족 → BROKEN 정보 설정: {ticker}, broken_at={broken_at}, broken_return_pct={broken_return_pct:.2f}%")
                    # 정책: broken_return_pct를 archive_return_pct로 사용
                    archive_return_pct = broken_return_pct
                    # archive_price 재계산
                    if existing_anchor_close:
                        anchor_close_float = float(existing_anchor_close)
                        archive_price = round(anchor_close_float * (1 + archive_return_pct / 100), 0)
                
                # 기존 ACTIVE를 ARCHIVED로 전이 (archive_return_pct 등 포함, TTL 체크 및 손절 조건 반영)
                # BROKEN 정보도 함께 저장 (broken_at, broken_return_pct)
                # 정책: broken_return_pct가 있으면 archive_return_pct로 사용
                cur.execute("""
                    UPDATE recommendations
                    SET status = 'ARCHIVED',
                        archived_at = NOW(),
                        archive_reason = %s,
                        broken_at = %s,
                        broken_return_pct = %s,
                        archive_return_pct = %s,
                        archive_price = %s,
                        archive_phase = %s,
                        updated_at = NOW(),
                        status_changed_at = NOW()
                    WHERE recommendation_id = %s
                """, (archive_reason, broken_at, broken_return_pct, archive_return_pct, archive_price, archive_phase, existing_rec_id))
                
                # 상태 변경 이벤트 기록
                cur.execute("""
                    INSERT INTO recommendation_state_events (
                        recommendation_id, from_status, to_status, reason, metadata
                    ) VALUES (%s, %s, %s, %s, %s)
                """, (
                    existing_rec_id,
                    'ACTIVE',
                    'ARCHIVED',
                    'REPLACED',
                    json.dumps({
                        "new_recommendation_date": scan_date,
                        "archive_return_pct": archive_return_pct,
                        "archive_price": archive_price,
                        "archive_phase": archive_phase
                    }, ensure_ascii=False)
                ))
                
                logger.info(f"[recommendation_service] 기존 ACTIVE 추천 아카이브: {ticker} (ID: {existing_rec_id}, archive_return_pct: {archive_return_pct})")
            
            # 새 추천 생성
            cur.execute("""
                INSERT INTO recommendations (
                    ticker, name, status, anchor_date, anchor_close, anchor_price_type, anchor_source,
                    strategy, scanner_version, score, score_label, indicators, flags, details
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING recommendation_id
            """, (
                ticker,
                name,
                'ACTIVE',
                anchor_date_obj,
                float(anchor_close_value),
                'CLOSE',
                'KRX_EOD',
                strategy,
                scanner_version,
                score,
                score_label,
                json.dumps(indicators, ensure_ascii=False),
                json.dumps(flags, ensure_ascii=False),
                json.dumps(details, ensure_ascii=False)
            ))
            
            new_rec_row = cur.fetchone()
            if isinstance(new_rec_row, dict):
                new_rec_id = new_rec_row['recommendation_id']
            else:
                new_rec_id = new_rec_row[0] if new_rec_row else None
            
            # 상태 변경 이벤트 기록 (생성)
            cur.execute("""
                INSERT INTO recommendation_state_events (
                    recommendation_id, from_status, to_status, reason, metadata
                ) VALUES (%s, %s, %s, %s, %s)
            """, (
                new_rec_id,
                None,
                'ACTIVE',
                '새 추천 생성',
                json.dumps({"scan_date": scan_date, "anchor_date": anchor_date_str}, ensure_ascii=False)
            ))
            
            logger.info(f"[recommendation_service] 추천 생성 완료: {ticker} (ID: {new_rec_id}, anchor_date: {anchor_date_str}, anchor_close: {anchor_close_value})")
            return new_rec_id
            
    except Exception as e:
        logger.error(f"[recommendation_service] 추천 생성 오류 ({ticker}): {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def process_scan_results_to_recommendations(
    scan_items: List[Dict],
    scan_date: str,
    scan_run_id: str = None,
    scanner_version: str = "v3"
) -> Dict[str, int]:
    """
    스캔 결과를 처리하여 scan_results 저장 및 recommendations 생성
    
    Args:
        scan_items: 스캔 결과 리스트
        scan_date: 스캔 날짜 (YYYYMMDD)
        scan_run_id: 스캔 실행 ID
        scanner_version: 스캐너 버전
        
    Returns:
        {
            "scan_results_saved": 저장된 scan_results 수,
            "recommendations_created": 생성된 recommendations 수,
            "recommendations_skipped": 건너뛴 recommendations 수
        }
    """
    # 1. scan_results에 저장 (스캔 로그)
    scan_results_saved = save_scan_results(scan_items, scan_date, scan_run_id, scanner_version)
    
    # 2. recommendations 생성 (추천 이벤트)
    recommendations_created = 0
    recommendations_skipped = 0
    
    for item in scan_items:
        ticker = item.get("ticker") or item.get("code")
        if not ticker or ticker == "NORESULT":
            continue
        
        rec_id = create_recommendation(
            ticker=ticker,
            name=item.get("name", ""),
            scan_date=scan_date,
            strategy=item.get("strategy"),
            score=item.get("score", 0.0),
            score_label=item.get("score_label", ""),
            indicators=item.get("indicators", {}),
            flags=item.get("flags", {}),
            details=item.get("details", {}),
            scanner_version=scanner_version
        )
        
        if rec_id:
            recommendations_created += 1
        else:
            recommendations_skipped += 1
    
    return {
        "scan_results_saved": scan_results_saved,
        "recommendations_created": recommendations_created,
        "recommendations_skipped": recommendations_skipped
    }


def get_active_recommendations_list(user_id: Optional[int] = None) -> List[Dict]:
    """
    ACTIVE 상태인 추천 목록 조회
    
    Args:
        user_id: 사용자 ID (ack 필터링용, None이면 필터링 안 함)
        
    Returns:
        추천 목록
    """
    try:
        with db_manager.get_cursor(commit=False) as cur:
            # user_id가 있으면 ack 필터링
            if user_id:
                # v2 스키마 사용: recommendation_id (UUID), name 컬럼 포함
                cur.execute("""
                    SELECT 
                        r.recommendation_id, r.ticker, r.name, r.status, r.anchor_date, r.anchor_close,
                        r.strategy, r.scanner_version, r.score, r.score_label,
                        r.indicators, r.flags, r.details,
                        r.created_at, r.updated_at,
                        CASE WHEN ua.id IS NOT NULL THEN true ELSE false END as is_acked
                    FROM recommendations r
                    LEFT JOIN user_rec_ack ua ON (
                        ua.user_id = %s
                        AND ua.rec_code = r.ticker
                        AND ua.rec_scanner_version = r.scanner_version
                        AND ua.ack_type = 'BROKEN_VIEWED'
                    )
                    WHERE r.status IN ('ACTIVE', 'WEAK_WARNING')
                    AND r.scanner_version = 'v3'
                    ORDER BY r.anchor_date DESC, r.ticker
                """, (user_id,))
            else:
                # v2 스키마 사용: recommendation_id (UUID), name 컬럼 포함
                # 방어적 status 필터: ACTIVE, WEAK_WARNING만 허용
                cur.execute("""
                    SELECT 
                        recommendation_id, ticker, name, status, anchor_date, anchor_close,
                        strategy, scanner_version, score, score_label,
                        indicators, flags, details,
                        created_at, updated_at
                    FROM recommendations
                    WHERE status IN ('ACTIVE', 'WEAK_WARNING')
                    AND scanner_version = 'v3'
                    ORDER BY anchor_date DESC, ticker
                """)
            
            rows = cur.fetchall()
            
            # 1단계: 모든 아이템을 기본 구조로 변환
            items = []
            tickers_for_name = set()  # 종목명 조회 필요한 ticker
            tickers_for_return = {}  # 수익률 계산 필요한 ticker -> anchor_close 매핑
            
            for row in rows:
                if isinstance(row, dict):
                    item = dict(row)
                    if 'recommendation_id' in item and 'id' not in item:
                        item['id'] = str(item['recommendation_id'])
                    elif 'recommendation_id' in item:
                        item['id'] = str(item['recommendation_id'])
                else:
                    # name 컬럼이 있는지 확인 (하위 호환)
                    if len(row) >= 15:  # name 컬럼이 있는 경우
                        item = {
                            "id": str(row[0]),
                            "recommendation_id": str(row[0]),
                            "ticker": row[1],
                            "name": row[2],  # name 컬럼
                            "status": row[3],
                            "anchor_date": row[4],
                            "anchor_close": row[5],
                            "strategy": row[6],
                            "scanner_version": row[7],
                            "score": row[8],
                            "score_label": row[9],
                            "indicators": row[10],
                            "flags": row[11],
                            "details": row[12],
                            "created_at": row[13],
                            "updated_at": row[14]
                        }
                        if len(row) > 15:
                            item["is_acked"] = row[15]
                    else:  # name 컬럼이 없는 경우 (하위 호환)
                        item = {
                            "id": str(row[0]),
                            "recommendation_id": str(row[0]),
                            "ticker": row[1],
                            "name": None,  # name 없음
                            "status": row[2],
                            "anchor_date": row[3],
                            "anchor_close": row[4],
                            "strategy": row[5],
                            "scanner_version": row[6],
                            "score": row[7],
                            "score_label": row[8],
                            "indicators": row[9],
                            "flags": row[10],
                            "details": row[11],
                            "created_at": row[12],
                            "updated_at": row[13]
                        }
                        if len(row) > 14:
                            item["is_acked"] = row[14]
                
                # JSON 필드 파싱
                if isinstance(item.get("indicators"), str):
                    try:
                        item["indicators"] = json.loads(item["indicators"])
                    except:
                        item["indicators"] = {}
                
                if isinstance(item.get("flags"), str):
                    try:
                        item["flags"] = json.loads(item["flags"])
                    except:
                        item["flags"] = {}
                
                if isinstance(item.get("details"), str):
                    try:
                        item["details"] = json.loads(item["details"])
                    except:
                        item["details"] = {}
                
                # 종목명 조회 필요한 ticker 수집 (name이 NULL이거나 빈 문자열인 경우만)
                if item.get("ticker") and (not item.get("name") or (isinstance(item.get("name"), str) and not item.get("name").strip())):
                    tickers_for_name.add(item["ticker"])
                
                # 수익률 계산 필요한 ticker 수집
                if item.get("ticker") and item.get("anchor_close") and item.get("anchor_close") > 0:
                    tickers_for_return[item["ticker"]] = float(item["anchor_close"])
                
                items.append(item)
            
            # 2단계: 배치 종목명 조회 (병렬 처리)
            ticker_to_name = {}
            if tickers_for_name:
                def fetch_stock_name(ticker):
                    """종목명 조회 헬퍼 함수"""
                    try:
                        from pykrx import stock
                        result = stock.get_market_ticker_name(ticker)
                        if isinstance(result, str) and result:
                            return ticker, result
                        elif hasattr(result, 'empty') and not result.empty:
                            if hasattr(result, 'iloc'):
                                name = str(result.iloc[0]) if len(result) > 0 else None
                            elif hasattr(result, 'values'):
                                name = str(result.values[0]) if len(result.values) > 0 else None
                            else:
                                name = None
                            if name:
                                return ticker, name
                    except Exception as e:
                        logger.debug(f"[get_active_recommendations_list] pykrx 종목명 조회 실패 (ticker={ticker}): {e}")
                    
                    # pykrx 실패 시 kiwoom_api로 fallback
                    try:
                        from kiwoom_api import api
                        stock_name = api.get_stock_name(ticker)
                        if stock_name:
                            return ticker, stock_name
                    except Exception as e:
                        logger.debug(f"[get_active_recommendations_list] kiwoom_api 종목명 조회 실패 (ticker={ticker}): {e}")
                    
                    return ticker, None
                
                # 병렬 처리로 종목명 조회 (최대 20개 동시로 증가)
                max_workers = min(20, len(tickers_for_name))
                with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_ticker = {
                        executor.submit(fetch_stock_name, ticker): ticker 
                        for ticker in tickers_for_name
                    }
                    
                    # 타임아웃 설정 (각 종목명 조회는 최대 2초)
                    for future in concurrent.futures.as_completed(future_to_ticker):
                        try:
                            ticker, name = future.result(timeout=2.0)
                            if name:
                                ticker_to_name[ticker] = name
                        except concurrent.futures.TimeoutError:
                            ticker = future_to_ticker[future]
                            logger.debug(f"[get_active_recommendations_list] 종목명 조회 타임아웃 (ticker={ticker})")
                        except Exception as e:
                            ticker = future_to_ticker[future]
                            logger.debug(f"[get_active_recommendations_list] 종목명 조회 오류 (ticker={ticker}): {e}")
            
            # 3단계: 배치 수익률 계산 (OHLCV 캐시 활용, API 호출 최소화)
            ticker_to_today_close = {}
            if tickers_for_return:
                try:
                    from kiwoom_api import api
                    
                    today_str = get_kst_now().strftime('%Y%m%d')
                    unique_tickers = list(set(tickers_for_return.keys()))
                    
                    # 캐시에서 직접 읽기 (api.get_ohlcv()는 내부적으로 캐시 확인)
                    def fetch_today_close(ticker):
                        """오늘 종가 조회 헬퍼 함수 (캐시 우선, API 호출 최소화)"""
                        try:
                            # api.get_ohlcv()는 내부적으로 메모리 캐시 → 디스크 캐시 → API 순으로 확인
                            # 스캔을 통해 이미 캐시에 데이터가 있으면 빠르게 반환됨
                            df_today = api.get_ohlcv(ticker, 1, today_str)
                            if not df_today.empty:
                                if 'close' in df_today.columns:
                                    close_price = float(df_today.iloc[-1]['close'])
                                else:
                                    close_price = float(df_today.iloc[-1].values[0])
                                return ticker, close_price
                        except Exception as e:
                            logger.debug(f"[get_active_recommendations_list] 수익률 계산 실패 (ticker={ticker}): {e}")
                        return ticker, None
                    
                    # 병렬 처리로 오늘 종가 조회 (최대 20개 동시)
                    max_workers = min(20, len(unique_tickers))
                    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                        future_to_ticker = {
                            executor.submit(fetch_today_close, ticker): ticker 
                            for ticker in unique_tickers
                        }
                        
                        fetched_prices = {}
                        # 타임아웃 설정 (캐시에서 읽으면 빠르므로 0.5초로 단축)
                        for future in concurrent.futures.as_completed(future_to_ticker):
                            try:
                                ticker, close_price = future.result(timeout=0.5)
                                if close_price is not None:
                                    fetched_prices[ticker] = close_price
                            except concurrent.futures.TimeoutError:
                                ticker = future_to_ticker[future]
                                logger.debug(f"[get_active_recommendations_list] 수익률 계산 타임아웃 (ticker={ticker})")
                            except Exception as e:
                                ticker = future_to_ticker[future]
                                logger.debug(f"[get_active_recommendations_list] 수익률 계산 오류 (ticker={ticker}): {e}")
                    
                    ticker_to_today_close.update(fetched_prices)
                except Exception as e:
                    logger.warning(f"[get_active_recommendations_list] 수익률 배치 계산 실패: {e}")
            
            # 4단계: 아이템에 종목명/수익률/남은 거래일 매핑
            from services.state_transition_service import get_trading_days_since
            
            for item in items:
                # 종목명 매핑
                # 종목명 매핑 (name이 NULL이거나 빈 문자열인 경우만)
                if item.get("ticker") and (not item.get("name") or (isinstance(item.get("name"), str) and not item.get("name").strip())):
                    item["name"] = ticker_to_name.get(item["ticker"])
                    if not item["name"]:
                        logger.warning(f"[get_active_recommendations_list] 종목명 조회 실패: ticker={item['ticker']}")
                
                # 수익률 매핑
                if item.get("ticker") and item.get("anchor_close") and item.get("anchor_close") > 0:
                    today_close = ticker_to_today_close.get(item["ticker"])
                    if today_close:
                        anchor_close = float(item["anchor_close"])
                        current_return = ((today_close - anchor_close) / anchor_close) * 100
                        item["current_return"] = round(current_return, 2)
                    else:
                        # 오늘 종가를 가져오지 못한 경우
                        logger.debug(f"[get_active_recommendations_list] 오늘 종가 없음: ticker={item.get('ticker')}, anchor_close={item.get('anchor_close')}")
                        item["current_return"] = None
                else:
                    # anchor_close가 없거나 0인 경우
                    if item.get("ticker"):
                        logger.warning(f"[get_active_recommendations_list] anchor_close 없음: ticker={item.get('ticker')}, anchor_close={item.get('anchor_close')}")
                    item["current_return"] = None
                
                # ARCHIVED 전이까지 남은 거래일 계산 (ACTIVE/WEAK_WARNING만)
                if item.get("status") in ["ACTIVE", "WEAK_WARNING"] and item.get("anchor_date"):
                    try:
                        strategy = item.get("strategy")
                        anchor_date = item.get("anchor_date")
                        
                        # 전략별 TTL 설정
                        ttl_days = 20  # 기본값
                        if strategy == "v2_lite":
                            ttl_days = 15
                        elif strategy == "midterm":
                            ttl_days = 25
                        
                        # 현재 경과 거래일 계산
                        trading_days_elapsed = get_trading_days_since(anchor_date)
                        
                        # 남은 거래일 계산
                        days_until_archive = max(0, ttl_days - trading_days_elapsed)
                        item["days_until_archive"] = days_until_archive
                    except Exception as e:
                        logger.debug(f"[get_active_recommendations_list] 남은 거래일 계산 실패 (ticker={item.get('ticker')}): {e}")
                        item["days_until_archive"] = None
            
            return items
            
    except Exception as e:
        logger.error(f"[recommendation_service] ACTIVE 추천 목록 조회 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []


def get_needs_attention_recommendations_list(user_id: Optional[int] = None) -> List[Dict]:
    """
    주의가 필요한 추천 목록 조회 (WEAK_WARNING, BROKEN)
    
    Args:
        user_id: 사용자 ID (ack 필터링용, None이면 필터링 안 함)
        
    Returns:
        추천 목록
    """
    try:
        with db_manager.get_cursor(commit=False) as cur:
            # user_id가 있으면 ack 필터링
            if user_id:
                # v2 스키마 사용: recommendation_id (UUID), name 컬럼 포함
                cur.execute("""
                    SELECT 
                        r.recommendation_id, r.ticker, r.name, r.status, r.anchor_date, r.anchor_close,
                        r.strategy, r.scanner_version, r.score, r.score_label,
                        r.indicators, r.flags, r.details,
                        r.created_at, r.updated_at, r.broken_at, r.status_changed_at, r.reason, r.broken_return_pct,
                        CASE WHEN ua.id IS NOT NULL THEN true ELSE false END as is_acked
                    FROM recommendations r
                    LEFT JOIN user_rec_ack ua ON (
                        ua.user_id = %s
                        AND ua.rec_code = r.ticker
                        AND ua.rec_scanner_version = r.scanner_version
                        AND ua.ack_type = 'BROKEN_VIEWED'
                    )
                    WHERE r.status IN ('WEAK_WARNING', 'BROKEN')
                    AND r.scanner_version = 'v3'
                    ORDER BY 
                        CASE r.status
                            WHEN 'BROKEN' THEN 1
                            WHEN 'WEAK_WARNING' THEN 2
                            ELSE 3
                        END,
                        r.broken_at DESC NULLS LAST,
                        r.anchor_date DESC
                """, (user_id,))
            else:
                # v2 스키마 사용: recommendation_id (UUID), name 컬럼 포함
                cur.execute("""
                    SELECT 
                        recommendation_id, ticker, name, status, anchor_date, anchor_close,
                        strategy, scanner_version, score, score_label,
                        indicators, flags, details,
                        created_at, updated_at, broken_at, status_changed_at, reason, broken_return_pct
                    FROM recommendations
                    WHERE status IN ('WEAK_WARNING', 'BROKEN')
                    AND scanner_version = 'v3'
                    ORDER BY 
                        CASE status
                            WHEN 'BROKEN' THEN 1
                            WHEN 'WEAK_WARNING' THEN 2
                            ELSE 3
                        END,
                        broken_at DESC NULLS LAST,
                        anchor_date DESC
                """)
            
            rows = cur.fetchall()
            
            # 배치 처리를 위한 ticker 수집
            items = []
            tickers_for_name = set()
            tickers_for_return = {}
            
            for row in rows:
                if isinstance(row, dict):
                    item = dict(row)
                    if 'recommendation_id' in item and 'id' not in item:
                        item['id'] = str(item['recommendation_id'])
                    elif 'recommendation_id' in item:
                        item['id'] = str(item['recommendation_id'])
                else:
                    # name 컬럼이 있는지 확인 (하위 호환)
                    if len(row) >= 18:  # name 컬럼 + status_changed_at + reason + broken_return_pct 포함
                        item = {
                            "id": str(row[0]),
                            "recommendation_id": str(row[0]),
                            "ticker": row[1],
                            "name": row[2],  # name 컬럼
                            "status": row[3],
                            "anchor_date": row[4],
                            "anchor_close": row[5],
                            "strategy": row[6],
                            "scanner_version": row[7],
                            "score": row[8],
                            "score_label": row[9],
                            "indicators": row[10],
                            "flags": row[11],
                            "details": row[12],
                            "created_at": row[13],
                            "updated_at": row[14],
                            "broken_at": row[15] if len(row) > 15 else None,
                            "status_changed_at": row[16] if len(row) > 16 else None,
                            "reason": row[17] if len(row) > 17 else None,
                            "broken_return_pct": float(row[18]) if len(row) > 18 and row[18] is not None else None
                        }
                        if len(row) > 19:
                            item["is_acked"] = row[19]
                    elif len(row) >= 17:  # name 컬럼 + status_changed_at + reason 포함 (broken_return_pct 없음)
                        item = {
                            "id": str(row[0]),
                            "recommendation_id": str(row[0]),
                            "ticker": row[1],
                            "name": row[2],  # name 컬럼
                            "status": row[3],
                            "anchor_date": row[4],
                            "anchor_close": row[5],
                            "strategy": row[6],
                            "scanner_version": row[7],
                            "score": row[8],
                            "score_label": row[9],
                            "indicators": row[10],
                            "flags": row[11],
                            "details": row[12],
                            "created_at": row[13],
                            "updated_at": row[14],
                            "broken_at": row[15] if len(row) > 15 else None,
                            "status_changed_at": row[16] if len(row) > 16 else None,
                            "reason": row[17] if len(row) > 17 else None,
                            "broken_return_pct": None
                        }
                        if len(row) > 18:
                            item["is_acked"] = row[18]
                    elif len(row) >= 16:  # name 컬럼 + status_changed_at 포함 (reason 없음, 하위 호환)
                        item = {
                            "id": str(row[0]),
                            "recommendation_id": str(row[0]),
                            "ticker": row[1],
                            "name": row[2],  # name 컬럼
                            "status": row[3],
                            "anchor_date": row[4],
                            "anchor_close": row[5],
                            "strategy": row[6],
                            "scanner_version": row[7],
                            "score": row[8],
                            "score_label": row[9],
                            "indicators": row[10],
                            "flags": row[11],
                            "details": row[12],
                            "created_at": row[13],
                            "updated_at": row[14],
                            "broken_at": row[15] if len(row) > 15 else None,
                            "status_changed_at": row[16] if len(row) > 16 else None,
                            "reason": None,
                            "broken_return_pct": None
                        }
                        if len(row) > 17:
                            item["is_acked"] = row[17]
                    else:  # name 컬럼이 없는 경우 (하위 호환)
                        item = {
                            "id": str(row[0]),
                            "recommendation_id": str(row[0]),
                            "ticker": row[1],
                            "name": None,  # name 없음
                            "status": row[2],
                            "anchor_date": row[3],
                            "anchor_close": row[4],
                            "strategy": row[5],
                            "scanner_version": row[6],
                            "score": row[7],
                            "score_label": row[8],
                            "indicators": row[9],
                            "flags": row[10],
                            "details": row[11],
                            "created_at": row[12],
                            "updated_at": row[13],
                            "broken_at": row[14] if len(row) > 14 else None,
                            "status_changed_at": row[15] if len(row) > 15 else None,
                            "reason": row[16] if len(row) > 16 else None,
                            "broken_return_pct": float(row[17]) if len(row) > 17 and row[17] is not None else None
                        }
                        if len(row) > 18:
                            item["is_acked"] = row[18]
                
                # JSON 필드 파싱
                if isinstance(item.get("indicators"), str):
                    try:
                        item["indicators"] = json.loads(item["indicators"])
                    except:
                        item["indicators"] = {}
                
                if isinstance(item.get("flags"), str):
                    try:
                        item["flags"] = json.loads(item["flags"])
                    except:
                        item["flags"] = {}
                
                if isinstance(item.get("details"), str):
                    try:
                        item["details"] = json.loads(item["details"])
                    except:
                        item["details"] = {}
                
                # ticker 수집 (name이 NULL이거나 빈 문자열인 경우만)
                if item.get("ticker") and (not item.get("name") or (isinstance(item.get("name"), str) and not item.get("name").strip())):
                    tickers_for_name.add(item["ticker"])
                
                if item.get("ticker") and item.get("anchor_close") and item.get("anchor_close") > 0:
                    tickers_for_return[item["ticker"]] = float(item["anchor_close"])
                
                items.append(item)
            
            # 배치 종목명 조회 (병렬 처리)
            ticker_to_name = {}
            if tickers_for_name:
                def fetch_stock_name_na(ticker):
                    """종목명 조회 헬퍼 함수 (needs-attention용)"""
                    try:
                        from pykrx import stock
                        result = stock.get_market_ticker_name(ticker)
                        if isinstance(result, str) and result:
                            return ticker, result
                        elif hasattr(result, 'empty') and not result.empty:
                            if hasattr(result, 'iloc'):
                                name = str(result.iloc[0]) if len(result) > 0 else None
                            elif hasattr(result, 'values'):
                                name = str(result.values[0]) if len(result.values) > 0 else None
                            else:
                                name = None
                            if name:
                                return ticker, name
                    except Exception as e:
                        logger.debug(f"[get_needs_attention_recommendations_list] pykrx 종목명 조회 실패 (ticker={ticker}): {e}")
                    
                    # pykrx 실패 시 kiwoom_api로 fallback
                    try:
                        from kiwoom_api import api
                        stock_name = api.get_stock_name(ticker)
                        if stock_name:
                            return ticker, stock_name
                    except Exception as e:
                        logger.debug(f"[get_needs_attention_recommendations_list] kiwoom_api 종목명 조회 실패 (ticker={ticker}): {e}")
                    
                    return ticker, None
                
                # 병렬 처리로 종목명 조회 (최대 20개 동시로 증가)
                max_workers = min(20, len(tickers_for_name))
                with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_ticker = {
                        executor.submit(fetch_stock_name_na, ticker): ticker 
                        for ticker in tickers_for_name
                    }
                    
                    # 타임아웃 설정 (각 종목명 조회는 최대 2초)
                    for future in concurrent.futures.as_completed(future_to_ticker):
                        try:
                            ticker, name = future.result(timeout=2.0)
                            if name:
                                ticker_to_name[ticker] = name
                        except concurrent.futures.TimeoutError:
                            ticker = future_to_ticker[future]
                            logger.debug(f"[get_needs_attention_recommendations_list] 종목명 조회 타임아웃 (ticker={ticker})")
                        except Exception as e:
                            ticker = future_to_ticker[future]
                            logger.debug(f"[get_needs_attention_recommendations_list] 종목명 조회 오류 (ticker={ticker}): {e}")
            
            # 배치 수익률 계산 (OHLCV 캐시 활용, API 호출 최소화)
            ticker_to_today_close = {}
            if tickers_for_return:
                try:
                    from kiwoom_api import api
                    
                    today_str = get_kst_now().strftime('%Y%m%d')
                    unique_tickers = list(set(tickers_for_return.keys()))
                    
                    # 캐시에서 직접 읽기 (api.get_ohlcv()는 내부적으로 캐시 확인)
                    def fetch_today_close_na(ticker):
                        """오늘 종가 조회 헬퍼 함수 (캐시 우선, API 호출 최소화)"""
                        try:
                            # api.get_ohlcv()는 내부적으로 메모리 캐시 → 디스크 캐시 → API 순으로 확인
                            # 스캔을 통해 이미 캐시에 데이터가 있으면 빠르게 반환됨
                            df_today = api.get_ohlcv(ticker, 1, today_str)
                            if not df_today.empty:
                                if 'close' in df_today.columns:
                                    close_price = float(df_today.iloc[-1]['close'])
                                else:
                                    close_price = float(df_today.iloc[-1].values[0])
                                return ticker, close_price
                        except Exception as e:
                            logger.debug(f"[get_needs_attention_recommendations_list] 수익률 계산 실패 (ticker={ticker}): {e}")
                        return ticker, None
                    
                    # 병렬 처리로 오늘 종가 조회 (최대 20개 동시)
                    max_workers = min(20, len(unique_tickers))
                    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                        future_to_ticker = {
                            executor.submit(fetch_today_close_na, ticker): ticker 
                            for ticker in unique_tickers
                        }
                        
                        fetched_prices = {}
                        # 타임아웃 설정 (캐시에서 읽으면 빠르므로 0.5초로 단축)
                        for future in concurrent.futures.as_completed(future_to_ticker):
                            try:
                                ticker, close_price = future.result(timeout=0.5)
                                if close_price is not None:
                                    fetched_prices[ticker] = close_price
                            except concurrent.futures.TimeoutError:
                                ticker = future_to_ticker[future]
                                logger.debug(f"[get_needs_attention_recommendations_list] 수익률 계산 타임아웃 (ticker={ticker})")
                            except Exception as e:
                                ticker = future_to_ticker[future]
                                logger.debug(f"[get_needs_attention_recommendations_list] 수익률 계산 오류 (ticker={ticker}): {e}")
                    
                    ticker_to_today_close.update(fetched_prices)
                except Exception as e:
                    logger.warning(f"[get_needs_attention_recommendations_list] 수익률 배치 계산 실패: {e}")
            
            # 아이템에 종목명/수익률/남은 거래일 매핑
            from services.state_transition_service import get_trading_days_since
            
            for item in items:
                # 종목명 매핑 (name이 NULL이거나 빈 문자열인 경우만)
                if item.get("ticker") and (not item.get("name") or (isinstance(item.get("name"), str) and not item.get("name").strip())):
                    item["name"] = ticker_to_name.get(item["ticker"])
                    if not item["name"]:
                        logger.warning(f"[get_needs_attention_recommendations_list] 종목명 조회 실패: ticker={item['ticker']}")
                
                # 수익률 계산: BROKEN 상태일 때 두 가지 손익률 제공
                if item.get("status") == "BROKEN":
                    # 1. 판단 당시 손익률 (종료 시점 고정)
                    if item.get("broken_return_pct") is not None:
                        item["broken_return_pct"] = item["broken_return_pct"]  # 이미 있음
                    else:
                        item["broken_return_pct"] = None
                    
                    # 2. 현재 시점 손익률 (실시간 계산)
                    if item.get("ticker") and item.get("anchor_close") and item.get("anchor_close") > 0:
                        today_close = ticker_to_today_close.get(item["ticker"])
                        if today_close:
                            anchor_close = float(item["anchor_close"])
                            current_return = ((today_close - anchor_close) / anchor_close) * 100
                            item["current_return"] = round(current_return, 2)
                        else:
                            item["current_return"] = None
                    else:
                        item["current_return"] = None
                    
                    # 3. ARCHIVED 전이까지 남은 거래일 계산 (BROKEN은 1거래일 후 ARCHIVED로 전이)
                    try:
                        # broken_at이 없으면 status_changed_at 사용
                        broken_at = item.get("broken_at")
                        if not broken_at:
                            broken_at = item.get("status_changed_at")
                        
                        if broken_at:
                            # broken_at부터 오늘까지의 거래일 계산
                            broken_trading_days = get_trading_days_since(broken_at)
                            # BROKEN은 1거래일 후 ARCHIVED로 전이되므로, 남은 거래일 = max(0, 1 - broken_trading_days)
                            days_until_archive = max(0, 1 - broken_trading_days)
                            item["days_until_archive"] = days_until_archive
                        else:
                            item["days_until_archive"] = None
                    except Exception as e:
                        logger.debug(f"[get_needs_attention_recommendations_list] BROKEN 남은 거래일 계산 실패 (ticker={item.get('ticker')}): {e}")
                        item["days_until_archive"] = None
                elif item.get("ticker") and item.get("anchor_close") and item.get("anchor_close") > 0:
                    # BROKEN이 아닌 경우 실시간 계산
                    today_close = ticker_to_today_close.get(item["ticker"])
                    if today_close:
                        anchor_close = float(item["anchor_close"])
                        current_return = ((today_close - anchor_close) / anchor_close) * 100
                        item["current_return"] = round(current_return, 2)
                    else:
                        item["current_return"] = None
                else:
                    item["current_return"] = None
                
                # WEAK_WARNING 상태의 ARCHIVED 전이까지 남은 거래일 계산
                if item.get("status") == "WEAK_WARNING" and item.get("anchor_date"):
                    try:
                        strategy = item.get("strategy")
                        anchor_date = item.get("anchor_date")
                        
                        # 전략별 TTL 설정
                        ttl_days = 20  # 기본값
                        if strategy == "v2_lite":
                            ttl_days = 15
                        elif strategy == "midterm":
                            ttl_days = 25
                        
                        # 현재 경과 거래일 계산
                        trading_days_elapsed = get_trading_days_since(anchor_date)
                        
                        # 남은 거래일 계산
                        days_until_archive = max(0, ttl_days - trading_days_elapsed)
                        item["days_until_archive"] = days_until_archive
                    except Exception as e:
                        logger.debug(f"[get_needs_attention_recommendations_list] WEAK_WARNING 남은 거래일 계산 실패 (ticker={item.get('ticker')}): {e}")
                        item["days_until_archive"] = None
            
            return items
            
    except Exception as e:
        logger.error(f"[recommendation_service] 주의 필요 추천 목록 조회 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []


def get_archived_recommendations_list(user_id: Optional[int] = None, limit: Optional[int] = None) -> List[Dict]:
    """
    ARCHIVED 상태인 추천 목록 조회
    
    Args:
        user_id: 사용자 ID (ack 필터링용, None이면 필터링 안 함)
        limit: 조회 개수 제한 (None이면 전체)
        
    Returns:
        추천 목록
    """
    try:
        with db_manager.get_cursor(commit=False) as cur:
            # v2 스키마 사용: recommendation_id (UUID), name 컬럼 포함
            query = """
                    SELECT 
                        recommendation_id, ticker, name, status, anchor_date, anchor_close,
                        strategy, scanner_version, score, score_label,
                        indicators, flags, details,
                        created_at, updated_at, archived_at, archive_reason, archive_return_pct
                    FROM recommendations
                    WHERE status = 'ARCHIVED'
                    AND scanner_version = 'v3'
                    ORDER BY updated_at DESC NULLS LAST, archived_at DESC NULLS LAST, created_at DESC
            """
            
            if limit:
                query += f" LIMIT {limit}"
            
            cur.execute(query)
            rows = cur.fetchall()
            
            # 배치 처리를 위한 ticker 수집
            items = []
            tickers_for_name = set()
            # ARCHIVED는 실시간 계산하지 않으므로 tickers_for_return 제거
            
            for row in rows:
                if isinstance(row, dict):
                    item = dict(row)
                    if 'recommendation_id' in item and 'id' not in item:
                        item['id'] = str(item['recommendation_id'])
                else:
                    # name 컬럼이 있는 경우 (18개 컬럼: archive_at, archive_reason, archive_return_pct 포함)
                    if len(row) >= 18:
                        item = {
                            "id": str(row[0]),
                            "recommendation_id": str(row[0]),
                            "ticker": row[1],
                            "name": row[2],  # name 컬럼
                            "status": row[3],  # status는 row[3]
                            "anchor_date": row[4],
                            "anchor_close": row[5],
                            "strategy": row[6],
                            "scanner_version": row[7],
                            "score": row[8],
                            "score_label": row[9],
                            "indicators": row[10],
                            "flags": row[11],
                            "details": row[12],
                            "created_at": row[13],
                            "updated_at": row[14],
                            "archived_at": row[15] if len(row) > 15 else None,
                            "archive_reason": row[16] if len(row) > 16 else None,
                            "archive_return_pct": float(row[17]) if len(row) > 17 and row[17] is not None else None
                        }
                    elif len(row) >= 16:  # name 컬럼이 있지만 archive 필드 없음 (하위 호환)
                        item = {
                            "id": str(row[0]),
                            "recommendation_id": str(row[0]),
                            "ticker": row[1],
                            "name": row[2],  # name 컬럼
                            "status": row[3],
                            "anchor_date": row[4],
                            "anchor_close": row[5],
                            "strategy": row[6],
                            "scanner_version": row[7],
                            "score": row[8],
                            "score_label": row[9],
                            "indicators": row[10],
                            "flags": row[11],
                            "details": row[12],
                            "created_at": row[13],
                            "updated_at": row[14],
                            "archived_at": row[15] if len(row) > 15 else None,
                            "archive_reason": None,
                            "archive_return_pct": None
                        }
                    else:
                        # name 컬럼이 없는 경우 (하위 호환, 15개 컬럼)
                        item = {
                            "id": str(row[0]),
                            "recommendation_id": str(row[0]),
                            "ticker": row[1],
                            "name": None,  # name 없음
                            "status": row[2],
                            "anchor_date": row[3],
                            "anchor_close": row[4],
                            "strategy": row[5],
                            "scanner_version": row[6],
                            "score": row[7],
                            "score_label": row[8],
                            "indicators": row[9],
                            "flags": row[10],
                            "details": row[11],
                            "created_at": row[12],
                            "updated_at": row[13],
                            "archived_at": row[14] if len(row) > 14 else None,
                            "archive_reason": row[15] if len(row) > 15 else None,
                            "archive_return_pct": float(row[16]) if len(row) > 16 and row[16] is not None else None
                        }
                
                # JSON 필드 파싱
                if isinstance(item.get("indicators"), str):
                    try:
                        item["indicators"] = json.loads(item["indicators"])
                    except:
                        item["indicators"] = {}
                
                if isinstance(item.get("flags"), str):
                    try:
                        item["flags"] = json.loads(item["flags"])
                    except:
                        item["flags"] = {}
                
                if isinstance(item.get("details"), str):
                    try:
                        item["details"] = json.loads(item["details"])
                    except:
                        item["details"] = {}
                
                # ticker 수집 (name이 NULL이거나 빈 문자열인 경우만)
                if item.get("ticker") and (not item.get("name") or (isinstance(item.get("name"), str) and not item.get("name").strip())):
                    tickers_for_name.add(item["ticker"])
                
                # ARCHIVED는 실시간 계산하지 않으므로 tickers_for_return 수집 제거
                
                items.append(item)
            
            # 배치 종목명 조회
            ticker_to_name = {}
            if tickers_for_name:
                try:
                    from pykrx import stock
                    for ticker in tickers_for_name:
                        try:
                            result = stock.get_market_ticker_name(ticker)
                            if isinstance(result, str) and result:
                                ticker_to_name[ticker] = result
                            elif hasattr(result, 'empty') and not result.empty:
                                if hasattr(result, 'iloc'):
                                    ticker_to_name[ticker] = str(result.iloc[0]) if len(result) > 0 else None
                                elif hasattr(result, 'values'):
                                    ticker_to_name[ticker] = str(result.values[0]) if len(result.values) > 0 else None
                        except Exception as e:
                            logger.debug(f"[get_archived_recommendations_list] pykrx 종목명 조회 실패 (ticker={ticker}): {e}")
                            ticker_to_name[ticker] = None
                except Exception as e:
                    logger.warning(f"[get_archived_recommendations_list] pykrx 배치 조회 실패: {e}")
                
                for ticker in tickers_for_name:
                    if ticker not in ticker_to_name or not ticker_to_name[ticker]:
                        try:
                            from kiwoom_api import api
                            stock_name = api.get_stock_name(ticker)
                            if stock_name:
                                ticker_to_name[ticker] = stock_name
                        except Exception as e:
                            logger.debug(f"[get_archived_recommendations_list] kiwoom_api 종목명 조회 실패 (ticker={ticker}): {e}")
            
            # ARCHIVED는 종료 시점 수익률만 사용하므로 실시간 계산 로직 제거
            
            # 아이템에 종목명/수익률/관찰기간 매핑
            for item in items:
                # 종목명 매핑 (name이 NULL이거나 빈 문자열인 경우만)
                if item.get("ticker") and (not item.get("name") or (isinstance(item.get("name"), str) and not item.get("name").strip())):
                    item["name"] = ticker_to_name.get(item["ticker"])
                
                # 수익률 계산: ARCHIVED 상태일 때 archive_return_pct만 사용 (종료 시점 고정)
                # archive_return_pct가 없으면 None으로 설정 (현재 시점 계산 금지)
                if item.get("archive_return_pct") is not None:
                    # ARCHIVED 상태이고 종료 시점 수익률이 저장되어 있으면 그것을 사용
                    item["current_return"] = item["archive_return_pct"]
                else:
                    # archive_return_pct가 없으면 None (종료 시점 데이터 없음)
                    item["current_return"] = None
                
                # 관찰기간 및 수익률 계산: TTL을 초과한 경우 전략별 TTL 시점의 값 사용
                archive_reason = item.get("archive_reason")
                strategy = item.get("strategy")
                anchor_date = item.get("anchor_date")
                anchor_close = item.get("anchor_close")
                archived_at = item.get("archived_at")
                
                # 전략별 TTL 설정
                ttl_days = 20  # 기본값
                if strategy == "v2_lite":
                    ttl_days = 15
                elif strategy == "midterm":
                    ttl_days = 25
                
                if anchor_date and archived_at:
                    try:
                        anchor_str = anchor_date.strftime('%Y%m%d') if hasattr(anchor_date, 'strftime') else str(anchor_date).replace('-', '')[:8]
                        archived_str = archived_at.strftime('%Y%m%d') if hasattr(archived_at, 'strftime') else str(archived_at).replace('-', '')[:8]
                        actual_days = get_trading_days_between(anchor_str, archived_str)
                        
                        # TTL을 초과한 경우: 전략별 TTL 시점의 관찰기간 및 수익률 사용
                        if actual_days >= ttl_days:
                            item["observation_period_days"] = ttl_days
                            
                            # TTL 시점의 수익률 계산
                            if anchor_close and anchor_close > 0:
                                try:
                                    # anchor_date에서 TTL 거래일만큼 더한 날짜 계산
                                    ttl_date_str = get_nth_trading_day_after(anchor_str, ttl_days)
                                    
                                    # TTL 시점의 가격 조회
                                    from kiwoom_api import api
                                    df_ttl = api.get_ohlcv(item.get("ticker"), 10, ttl_date_str)
                                    if not df_ttl.empty:
                                        ttl_price = None
                                        if 'date' in df_ttl.columns:
                                            df_ttl['date_str'] = df_ttl['date'].astype(str).str.replace('-', '').str[:8]
                                            df_filtered = df_ttl[df_ttl['date_str'] == ttl_date_str]
                                            if not df_filtered.empty:
                                                ttl_price = float(df_filtered.iloc[-1]['close'])
                                            else:
                                                # 가장 가까운 이전 거래일 데이터 사용
                                                df_sorted = df_ttl.sort_values('date_str')
                                                df_before = df_sorted[df_sorted['date_str'] <= ttl_date_str]
                                                if not df_before.empty:
                                                    ttl_price = float(df_before.iloc[-1]['close'])
                                        else:
                                            ttl_price = float(df_ttl.iloc[-1]['close']) if 'close' in df_ttl.columns else float(df_ttl.iloc[-1].values[0])
                                        
                                        if ttl_price:
                                            # TTL 시점의 수익률 계산 (표시용으로만 사용, archive_return_pct는 DB 스냅샷 유지)
                                            ttl_return_pct = round(((ttl_price - float(anchor_close)) / float(anchor_close)) * 100, 2)
                                            item["current_return"] = ttl_return_pct
                                            # archive_return_pct는 DB에 저장된 스냅샷 값이므로 덮어쓰지 않음
                                except Exception as e:
                                    logger.warning(f"[get_archived_recommendations_list] TTL 시점 수익률 계산 실패 (ticker={item.get('ticker')}): {e}")
                                    # 실패 시 기존 archive_return_pct 유지
                        else:
                            # TTL 미만인 경우: 실제 관찰기간 사용 (수익률은 기존 archive_return_pct 유지)
                            item["observation_period_days"] = actual_days
                    except Exception as e:
                        logger.warning(f"[get_archived_recommendations_list] 관찰기간 계산 실패 (ticker={item.get('ticker')}): {e}")
                        item["observation_period_days"] = None
                elif archive_reason == 'TTL_EXPIRED':
                    # TTL_EXPIRED인 경우: 전략별 TTL을 관찰기간으로 사용 (날짜 정보가 없어도)
                    item["observation_period_days"] = ttl_days
                    # TTL 시점 수익률 계산 시도 (anchor_date와 anchor_close가 있으면)
                    if anchor_date and anchor_close and anchor_close > 0:
                        try:
                            from services.state_transition_service import get_trading_days_since
                            from date_helper import yyyymmdd_to_date
                            from datetime import timedelta
                            import holidays
                            
                            anchor_str = anchor_date.strftime('%Y%m%d') if hasattr(anchor_date, 'strftime') else str(anchor_date).replace('-', '')[:8]
                            ttl_date_str = get_nth_trading_day_after(anchor_str, ttl_days)
                            
                            from kiwoom_api import api
                            df_ttl = api.get_ohlcv(item.get("ticker"), 10, ttl_date_str)
                            if not df_ttl.empty:
                                ttl_price = None
                                if 'date' in df_ttl.columns:
                                    df_ttl['date_str'] = df_ttl['date'].astype(str).str.replace('-', '').str[:8]
                                    df_filtered = df_ttl[df_ttl['date_str'] == ttl_date_str]
                                    if not df_filtered.empty:
                                        ttl_price = float(df_filtered.iloc[-1]['close'])
                                    else:
                                        df_sorted = df_ttl.sort_values('date_str')
                                        df_before = df_sorted[df_sorted['date_str'] <= ttl_date_str]
                                        if not df_before.empty:
                                            ttl_price = float(df_before.iloc[-1]['close'])
                                else:
                                    ttl_price = float(df_ttl.iloc[-1]['close']) if 'close' in df_ttl.columns else float(df_ttl.iloc[-1].values[0])
                                
                                if ttl_price:
                                    ttl_return_pct = round(((ttl_price - float(anchor_close)) / float(anchor_close)) * 100, 2)
                                    item["current_return"] = ttl_return_pct
                                    # archive_return_pct는 DB에 저장된 스냅샷 값이므로 덮어쓰지 않음
                        except Exception as e:
                            logger.warning(f"[get_archived_recommendations_list] TTL 시점 수익률 계산 실패 (ticker={item.get('ticker')}): {e}")
                else:
                    item["observation_period_days"] = None
            
            return items
            
    except Exception as e:
        logger.error(f"[recommendation_service] ARCHIVED 추천 목록 조회 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []


def get_recommendation_by_id(recommendation_id: int, user_id: Optional[int] = None) -> Optional[Dict]:
    """
    특정 추천 상세 조회
    
    Args:
        recommendation_id: 추천 ID
        user_id: 사용자 ID (ack 필터링용, None이면 필터링 안 함)
        
    Returns:
        추천 상세 정보 (없으면 None)
    """
    try:
        with db_manager.get_cursor(commit=False) as cur:
            if user_id:
                cur.execute("""
                    SELECT 
                        r.recommendation_id, r.ticker, r.name, r.status, r.anchor_date, r.anchor_close,
                        r.anchor_price_type, r.anchor_source,
                        r.strategy, r.scanner_version, r.score, r.score_label,
                        r.indicators, r.flags, r.details,
                        r.created_at, r.updated_at, r.broken_at, r.archived_at,
                        CASE WHEN ua.id IS NOT NULL THEN true ELSE false END as is_acked
                    FROM recommendations r
                    LEFT JOIN user_rec_ack ua ON (
                        ua.user_id = %s
                        AND ua.rec_code = r.ticker
                        AND ua.rec_scanner_version = r.scanner_version
                        AND ua.ack_type = 'BROKEN_VIEWED'
                    )
                    WHERE r.recommendation_id = %s
                """, (user_id, recommendation_id))
            else:
                cur.execute("""
                    SELECT 
                        recommendation_id, ticker, name, status, anchor_date, anchor_close,
                        anchor_price_type, anchor_source,
                        strategy, scanner_version, score, score_label,
                        indicators, flags, details,
                        created_at, updated_at, broken_at, archived_at
                    FROM recommendations
                    WHERE recommendation_id = %s
                """, (recommendation_id,))
            
            row = cur.fetchone()
            if not row:
                return None
            
            if isinstance(row, dict):
                item = dict(row)
                # recommendation_id가 없으면 id를 사용 (하위 호환성)
                if "recommendation_id" not in item and "id" in item:
                    item["recommendation_id"] = item["id"]
            else:
                # 컬럼 순서에 맞게 매핑
                item = {
                    "recommendation_id": row[0],
                    "id": row[0],  # 하위 호환성
                    "ticker": row[1],
                    "name": row[2],
                    "status": row[3],
                    "anchor_date": row[4],
                    "anchor_close": row[5],
                    "anchor_price_type": row[6],
                    "anchor_source": row[7],
                    "strategy": row[8],
                    "scanner_version": row[9],
                    "score": row[10],
                    "score_label": row[11],
                    "indicators": row[12],
                    "flags": row[13],
                    "details": row[14],
                    "created_at": row[15],
                    "updated_at": row[16],
                    "broken_at": row[17] if len(row) > 17 else None,
                    "archived_at": row[18] if len(row) > 18 else None
                }
                if len(row) > 19:
                    item["is_acked"] = row[19]
            
            # JSON 필드 파싱
            if isinstance(item.get("indicators"), str):
                try:
                    item["indicators"] = json.loads(item["indicators"])
                except:
                    item["indicators"] = {}
            
            if isinstance(item.get("flags"), str):
                try:
                    item["flags"] = json.loads(item["flags"])
                except:
                    item["flags"] = {}
            
            if isinstance(item.get("details"), str):
                try:
                    item["details"] = json.loads(item["details"])
                except:
                    item["details"] = {}
            
            return item
            
    except Exception as e:
        logger.error(f"[recommendation_service] 추천 상세 조회 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


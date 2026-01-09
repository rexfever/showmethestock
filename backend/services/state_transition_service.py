"""
v3 추천 상태 전이 서비스
ACTIVE → WEAK_WARNING → BROKEN → ARCHIVED 단방향 전이
"""
import logging
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import json
import holidays

from db_manager import db_manager
from date_helper import get_kst_now, yyyymmdd_to_date

logger = logging.getLogger(__name__)


def get_trading_days_since(anchor_date) -> int:
    """
    anchor_date부터 오늘까지의 거래일 수 계산
    
    중요: 추천 시점은 anchor_date입니다 (created_at이 아님)
    
    Args:
        anchor_date: datetime.date 또는 datetime 객체 (추천일)
        
    Returns:
        거래일 수 (0 이상)
    """
    try:
        if isinstance(anchor_date, str):
            anchor_date = yyyymmdd_to_date(anchor_date.replace('-', '')[:8])
        if isinstance(anchor_date, datetime):
            anchor_date = anchor_date.date()
        
        today = get_kst_now().date()
        
        if anchor_date > today:
            return 0
        
        # 한국 공휴일
        kr_holidays = holidays.SouthKorea(years=range(anchor_date.year, today.year + 2))
        
        trading_days = 0
        current = anchor_date
        while current <= today:
            # 주말 제외 (월요일=0, 일요일=6)
            if current.weekday() < 5:
                # 공휴일 제외
                if current not in kr_holidays:
                    trading_days += 1
            current += timedelta(days=1)
        
        return trading_days
    except Exception as e:
        logger.error(f"[get_trading_days_since] 거래일 계산 오류: {e}")
        return 0


def transition_recommendation_status(
    recommendation_id,  # UUID 또는 int (v1/v2 호환)
    to_status: str,
    reason: str,
    metadata: Optional[Dict] = None
) -> bool:
    """
    추천 상태 전이 (v2 스키마 호환)
    
    Args:
        recommendation_id: 추천 ID (UUID 또는 int)
        to_status: 변경할 상태 (WEAK_WARNING, BROKEN, ARCHIVED)
        reason: 상태 변경 이유
        metadata: 추가 메타데이터
        
    Returns:
        성공 여부
    """
    # v2 스키마의 transaction 함수 사용
    try:
        from services.recommendation_service_v2 import transition_recommendation_status_transaction
        import uuid
        
        # UUID로 변환
        if isinstance(recommendation_id, str):
            rec_uuid = uuid.UUID(recommendation_id)
        elif isinstance(recommendation_id, uuid.UUID):
            rec_uuid = recommendation_id
        else:
            # int인 경우 (v1 스키마) - UUID로 변환 시도 불가, 에러
            logger.error(f"[state_transition_service] UUID가 아닌 ID: {recommendation_id} (v2 스키마는 UUID만 지원)")
            return False
        
        # v2 transaction 함수 사용
        return transition_recommendation_status_transaction(
            recommendation_id=rec_uuid,
            to_status=to_status,
            reason_code=reason,
            reason_text=reason,
            metadata=metadata
        )
    except Exception as e:
        logger.error(f"[state_transition_service] 상태 전이 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def _is_valid_transition(from_status: str, to_status: str) -> bool:
    """
    상태 전이 유효성 검증
    
    허용된 전이:
    - ACTIVE → WEAK_WARNING
    - ACTIVE → BROKEN
    - WEAK_WARNING → BROKEN
    - WEAK_WARNING → ACTIVE (경고 해제)
    - BROKEN → ARCHIVED
    - ACTIVE → ARCHIVED
    - WEAK_WARNING → ARCHIVED
    
    금지된 전이:
    - BROKEN → ACTIVE (회복은 신규 추천 이벤트로만)
    - ARCHIVED → 다른 상태 (아카이브는 최종 상태)
    """
    if from_status == to_status:
        return True  # 동일 상태는 허용 (idempotent)
    
    # ARCHIVED는 최종 상태
    if from_status == 'ARCHIVED':
        return False
    
    # BROKEN → ACTIVE 금지 (회복은 신규 추천으로만)
    if from_status == 'BROKEN' and to_status == 'ACTIVE':
        return False
    
    # 허용된 전이
    valid_transitions = {
        'ACTIVE': ['WEAK_WARNING', 'BROKEN', 'ARCHIVED'],
        'WEAK_WARNING': ['ACTIVE', 'BROKEN', 'ARCHIVED'],
        'BROKEN': ['ARCHIVED'],
        'ARCHIVED': []  # 최종 상태
    }
    
    return to_status in valid_transitions.get(from_status, [])


def evaluate_active_recommendations(today_str: Optional[str] = None) -> Dict:
    """
    ACTIVE 추천을 평가하여 상태 전이
    
    Args:
        today_str: 평가 기준일 (YYYYMMDD), None이면 오늘
        
    Returns:
        평가 결과 통계
    """
    from kiwoom_api import api
    from date_helper import yyyymmdd_to_date
    
    if today_str is None:
        today_str = get_kst_now().strftime('%Y%m%d')
    
    logger.info(f"[state_transition_service] 상태 평가 시작: {today_str}")
    
    stats = {
        'total_active': 0,
        'evaluated': 0,
        'broken': 0,
        'weak_warning': 0,
        'archived_ttl': 0,  # TTL로 인한 ARCHIVED
        'archived_no_performance': 0,  # 무성과로 인한 ARCHIVED
        'errors': 0
    }
    
    try:
        with db_manager.get_cursor(commit=False) as cur:
            # BROKEN 상태인 추천 조회 (1거래일 이상 유지된 경우 ARCHIVED로 전환)
            cur.execute("""
                SELECT 
                    recommendation_id, ticker, status, anchor_date, anchor_close,
                    strategy, flags, indicators, status_changed_at, reason, broken_return_pct
                FROM recommendations
                WHERE status = 'BROKEN'
                AND scanner_version = 'v3'
                ORDER BY status_changed_at ASC, ticker
            """)
            
            broken_rows = cur.fetchall()
            
            # BROKEN → ARCHIVED 전환 처리 (1거래일 이상 유지된 경우)
            for broken_row in broken_rows:
                try:
                    if isinstance(broken_row, dict):
                        broken_rec_id = broken_row.get('recommendation_id')
                        broken_ticker = broken_row.get('ticker')
                        broken_status_changed_at = broken_row.get('status_changed_at')
                        broken_reason = broken_row.get('reason')
                        broken_return_pct = broken_row.get('broken_return_pct')
                    else:
                        broken_rec_id = broken_row[0]
                        broken_ticker = broken_row[1]
                        broken_status_changed_at = broken_row[8] if len(broken_row) > 8 else None
                        broken_reason = broken_row[9] if len(broken_row) > 9 else None
                        broken_return_pct = broken_row[10] if len(broken_row) > 10 else None
                    
                    if not broken_ticker or broken_ticker == 'NORESULT':
                        continue
                    
                    if not broken_status_changed_at:
                        continue
                    
                    # status_changed_at부터 오늘까지의 거래일 계산
                    if isinstance(broken_status_changed_at, str):
                        broken_date = yyyymmdd_to_date(broken_status_changed_at.replace('-', '')[:8])
                    elif isinstance(broken_status_changed_at, datetime):
                        broken_date = broken_status_changed_at.date()
                    elif hasattr(broken_status_changed_at, 'date'):
                        broken_date = broken_status_changed_at.date()
                    elif hasattr(broken_status_changed_at, 'year'):
                        broken_date = broken_status_changed_at
                    else:
                        continue
                    
                    # BROKEN 진입일부터 오늘까지의 거래일 계산
                    broken_trading_days = get_trading_days_since(broken_date)
                    
                    # 1거래일 이상 유지된 경우 ARCHIVED로 전환
                    if broken_trading_days >= 1:
                        logger.info(f"[state_transition_service] BROKEN → ARCHIVED 전이: {broken_ticker}, BROKEN 유지 기간: {broken_trading_days}거래일")
                        
                        # reason을 archive_reason으로 사용
                        archive_reason_code = broken_reason if broken_reason in ['TTL_EXPIRED', 'NO_MOMENTUM', 'MANUAL_ARCHIVE'] else 'NO_MOMENTUM'
                        
                        # BROKEN 시점의 스냅샷 사용 (broken_return_pct가 있으면 사용)
                        archive_return_pct = None
                        archive_price = None
                        archive_phase = None
                        
                        if broken_return_pct is not None:
                            # BROKEN 시점의 스냅샷 사용
                            archive_return_pct = round(float(broken_return_pct), 2)
                            
                            # BROKEN 시점의 가격 계산 (anchor_close와 broken_return_pct로 역산)
                            if isinstance(broken_row, dict):
                                broken_anchor_close = broken_row.get('anchor_close')
                            else:
                                broken_anchor_close = broken_row[4] if len(broken_row) > 4 else None
                            
                            if broken_anchor_close and broken_anchor_close > 0:
                                # broken_return_pct = ((broken_price - anchor_close) / anchor_close) * 100
                                # broken_price = anchor_close * (1 + broken_return_pct / 100)
                                archive_price = round(float(broken_anchor_close) * (1 + archive_return_pct / 100), 0)
                            
                            # archive_phase 결정
                            if archive_return_pct > 2:
                                archive_phase = 'PROFIT'
                            elif archive_return_pct < -2:
                                archive_phase = 'LOSS'
                            else:
                                archive_phase = 'FLAT'
                        else:
                            # broken_return_pct가 없으면 현재 가격으로 계산 (fallback)
                            try:
                                from kiwoom_api import api
                                df_today = api.get_ohlcv(broken_ticker, 10, today_str)
                                if not df_today.empty:
                                    today_close = None
                                    if 'date' in df_today.columns:
                                        df_today['date_str'] = df_today['date'].astype(str).str.replace('-', '').str[:8]
                                        df_filtered = df_today[df_today['date_str'] == today_str]
                                        if not df_filtered.empty:
                                            today_close = float(df_filtered.iloc[-1]['close'])
                                        else:
                                            df_sorted = df_today.sort_values('date_str')
                                            df_before = df_sorted[df_sorted['date_str'] <= today_str]
                                            if not df_before.empty:
                                                today_close = float(df_before.iloc[-1]['close'])
                                            else:
                                                today_close = float(df_today.iloc[-1]['close']) if 'close' in df_today.columns else float(df_today.iloc[-1].values[0])
                                    else:
                                        today_close = float(df_today.iloc[-1]['close']) if 'close' in df_today.columns else float(df_today.iloc[-1].values[0])
                                    
                                    # anchor_close 조회
                                    if isinstance(broken_row, dict):
                                        broken_anchor_close = broken_row.get('anchor_close')
                                    else:
                                        broken_anchor_close = broken_row[4] if len(broken_row) > 4 else None
                                    
                                    if broken_anchor_close and broken_anchor_close > 0 and today_close:
                                        archive_return_pct = round(((today_close - float(broken_anchor_close)) / float(broken_anchor_close)) * 100, 2)
                                        archive_price = today_close
                                        
                                        # archive_phase 결정
                                        if archive_return_pct > 2:
                                            archive_phase = 'PROFIT'
                                        elif archive_return_pct < -2:
                                            archive_phase = 'LOSS'
                                        else:
                                            archive_phase = 'FLAT'
                            except Exception as e:
                                logger.warning(f"[state_transition_service] ARCHIVED 전환 시 가격 조회 실패: {broken_ticker}, {e}")
                                archive_return_pct = None
                                archive_price = None
                                archive_phase = None
                        
                        # 상태 전이 (BROKEN → ARCHIVED)
                        transition_recommendation_status(
                            broken_rec_id,
                            'ARCHIVED',
                            archive_reason_code,
                            {
                                "current_return": archive_return_pct,
                                "current_price": archive_price,
                                "archive_phase": archive_phase,
                                "reason": archive_reason_code
                            }
                        )
                        
                        stats['archived_ttl'] += 1
                
                except Exception as e:
                    logger.error(f"[state_transition_service] BROKEN → ARCHIVED 전이 오류 ({broken_ticker}): {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    stats['errors'] += 1
            
            # ACTIVE/WEAK_WARNING 상태인 추천 조회 (v2 스키마: recommendation_id 사용)
            # anchor_date를 기준으로 조회 (추천 시점 = anchor_date)
            cur.execute("""
                SELECT 
                    recommendation_id, ticker, status, anchor_date, anchor_close,
                    strategy, flags, indicators, status_changed_at
                FROM recommendations
                WHERE status IN ('ACTIVE', 'WEAK_WARNING')
                AND scanner_version = 'v3'
                ORDER BY anchor_date DESC, ticker
            """)
            
            rows = cur.fetchall()
            stats['total_active'] = len(rows)
            
            logger.info(f"[state_transition_service] ACTIVE/WEAK_WARNING 추천: {len(rows)}개")
            
            for row in rows:
                try:
                    if isinstance(row, dict):
                        rec_id = row.get('recommendation_id')
                        ticker = row.get('ticker')
                        name = row.get('name', ticker)  # name이 없으면 ticker 사용
                        status = row.get('status')
                        anchor_date = row.get('anchor_date')
                        anchor_close = row.get('anchor_close')
                        strategy = row.get('strategy')
                        flags = row.get('flags')
                        indicators = row.get('indicators')
                        created_at = row.get('created_at')
                        status_changed_at = row.get('status_changed_at')
                    else:
                        # v2 스키마 컬럼 순서: recommendation_id, ticker, status, anchor_date, anchor_close, strategy, flags, indicators, status_changed_at
                        rec_id = row[0]
                        ticker = row[1]
                        name = ticker  # name은 조회하지 않으므로 ticker 사용
                        status = row[2]
                        anchor_date = row[3]
                        anchor_close = row[4]
                        strategy = row[5]
                        flags = row[6]
                        indicators = row[7] if len(row) > 7 else None
                        status_changed_at = row[8] if len(row) > 8 else None
                    
                    if not ticker or ticker == 'NORESULT':
                        continue
                    
                    # 이미 BROKEN이면 건너뛰기 (idempotent)
                    if status == 'BROKEN':
                        continue
                    
                    # 이미 ARCHIVED이면 건너뛰기 (idempotent)
                    if status == 'ARCHIVED':
                        continue
                    
                    # flags 파싱
                    if isinstance(flags, str):
                        try:
                            flags_dict = json.loads(flags)
                        except:
                            flags_dict = {}
                    else:
                        flags_dict = flags or {}
                    
                    # anchor_close 확인
                    if not anchor_close or anchor_close <= 0:
                        logger.warning(f"[state_transition_service] anchor_close 없음: {ticker}, 건너뜀")
                        continue
                    
                    # 전이 시점의 정확한 종가 조회 (today_str 기준)
                    try:
                        df_today = api.get_ohlcv(ticker, 10, today_str)
                        if df_today.empty:
                            logger.warning(f"[state_transition_service] 오늘 종가 없음: {ticker}, 건너뜀")
                            continue
                        
                        # today_str과 일치하는 행 찾기 (정확한 날짜의 가격 사용)
                        today_close = None
                        actual_price_date = today_str
                        
                        if 'date' in df_today.columns:
                            df_today['date_str'] = df_today['date'].astype(str).str.replace('-', '').str[:8]
                            df_filtered = df_today[df_today['date_str'] == today_str]
                            if not df_filtered.empty:
                                today_close = float(df_filtered.iloc[-1]['close'])
                                actual_price_date = today_str
                            else:
                                # 정확히 일치하는 날짜가 없으면 가장 가까운 이전 거래일 데이터 사용
                                df_sorted = df_today.sort_values('date_str')
                                df_before = df_sorted[df_sorted['date_str'] <= today_str]
                                if not df_before.empty:
                                    today_close = float(df_before.iloc[-1]['close'])
                                    actual_price_date = df_before.iloc[-1]['date_str']
                                else:
                                    # 마지막 행 사용
                                    today_close = float(df_today.iloc[-1]['close']) if 'close' in df_today.columns else float(df_today.iloc[-1].values[0])
                                    if 'date_str' in df_today.columns:
                                        actual_price_date = df_today.iloc[-1]['date_str']
                        else:
                            # date 컬럼이 없으면 마지막 행 사용 (base_dt 이하의 최근 데이터)
                            today_close = float(df_today.iloc[-1]['close']) if 'close' in df_today.columns else float(df_today.iloc[-1].values[0])
                        
                        # 로그: 실제 가격이 조회된 날짜 확인
                        if actual_price_date != today_str:
                            logger.debug(f"[state_transition_service] {ticker}: 요청일({today_str})의 데이터가 없어 {actual_price_date} 날짜의 가격 사용")
                    except Exception as e:
                        logger.warning(f"[state_transition_service] 종가 조회 실패: {ticker}, {e}")
                        continue
                    
                    # current_return 계산
                    current_return = ((today_close - anchor_close) / anchor_close) * 100
                    
                    # stop_loss 확인
                    stop_loss = flags_dict.get("stop_loss")
                    if stop_loss is None:
                        # 기본값 설정 (v2_lite: 2%, midterm: 7%)
                        if strategy == "v2_lite":
                            stop_loss = 0.02
                        elif strategy == "midterm":
                            stop_loss = 0.07
                        else:
                            stop_loss = 0.02
                    
                    stop_loss_pct = -abs(float(stop_loss) * 100)
                    
                    stats['evaluated'] += 1
                    
                    # BROKEN 조건 확인
                    if current_return <= stop_loss_pct:
                        # ACTIVE → BROKEN 전이
                        logger.info(f"[state_transition_service] BROKEN 전이: {ticker} ({name}), current_return={current_return:.2f}%, stop_loss={stop_loss_pct:.2f}%")
                        
                        # 종료 사유 결정: 손절 조건 도달 = NO_MOMENTUM
                        broken_reason = 'NO_MOMENTUM'
                        
                        # flags 업데이트
                        flags_dict["assumption_broken"] = True
                        flags_dict["broken_at"] = today_str
                        flags_dict["broken_reason"] = "HARD_STOP"
                        flags_dict["broken_anchor_return"] = round(current_return, 2)
                        
                        # flags 업데이트 (v2 스키마: recommendation_id 사용)
                        with db_manager.get_cursor(commit=True) as update_cur:
                            update_cur.execute("""
                                UPDATE recommendations
                                SET flags = %s
                                WHERE recommendation_id = %s
                            """, (
                                json.dumps(flags_dict, ensure_ascii=False),
                                rec_id
                            ))
                        
                        # 상태 전이 (v2 transaction 함수 사용, reason_code에 broken_reason 전달)
                        transition_recommendation_status(
                            rec_id,
                            'BROKEN',
                            broken_reason,  # reason_code로 전달
                            {
                                "current_return": round(current_return, 2),
                                "stop_loss": stop_loss_pct,
                                "today_close": today_close,
                                "anchor_close": anchor_close,
                                "reason": broken_reason
                            }
                        )
                        
                        stats['broken'] += 1
                        continue  # BROKEN 전이 후 다음 추천으로
                    
                    # 2) ARCHIVED 조건 확인 (BROKEN이 아닌 경우만)
                    # 추천 시점 = anchor_date (created_at이 아님)
                    archived_reason = None
                    should_archive = False
                    trading_days = 0
                    
                    # 전략별 TTL 설정
                    ttl_days = 20  # 기본값
                    if strategy == "v2_lite":
                        # v2_lite: holding_period = 14일 (약 10거래일), 여유분 포함하여 15거래일
                        ttl_days = 15
                    elif strategy == "midterm":
                        # midterm: holding_periods = [10, 15, 20] (최대 20거래일), 여유분 포함하여 25거래일
                        ttl_days = 25
                    
                    if anchor_date:
                        # anchor_date를 date 객체로 변환
                        anchor_date_obj = None
                        if isinstance(anchor_date, str):
                            anchor_date_obj = yyyymmdd_to_date(anchor_date.replace('-', '')[:8])
                        elif isinstance(anchor_date, datetime):
                            anchor_date_obj = anchor_date.date()
                        elif hasattr(anchor_date, 'date'):
                            anchor_date_obj = anchor_date.date()
                        elif hasattr(anchor_date, 'year'):  # date 객체
                            anchor_date_obj = anchor_date
                        
                        if anchor_date_obj:
                            trading_days = get_trading_days_since(anchor_date_obj)
                        
                        # A) TTL 종료 (전략별 TTL 이상) → BROKEN으로 전환
                        if trading_days >= ttl_days:
                            broken_reason = 'TTL_EXPIRED'
                            logger.info(f"[state_transition_service] TTL 종료 → BROKEN 전이: {ticker} ({name}), trading_days={trading_days}, ttl_days={ttl_days}")
                            
                            # TTL 만료 시점의 수익률 조회 (정책 준수)
                            ttl_return_pct = round(current_return, 2)  # 기본값: 현재 시점
                            ttl_close = today_close  # 기본값: 현재 시점
                            
                            try:
                                # TTL 만료일 계산
                                from services.recommendation_service import get_nth_trading_day_after
                                anchor_date_str = anchor_date_obj.strftime('%Y%m%d') if hasattr(anchor_date_obj, 'strftime') else str(anchor_date_obj).replace('-', '')[:8]
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
                                                ttl_close = float(ttl_row['close']) if 'close' in ttl_row else today_close
                                                if anchor_close and anchor_close > 0:
                                                    ttl_return_pct = round(((ttl_close - float(anchor_close)) / float(anchor_close)) * 100, 2)
                                                    logger.info(f"[state_transition_service] TTL 시점 수익률 사용: {ticker}, TTL 만료일={ttl_expiry_str}, 수익률={ttl_return_pct:.2f}%")
                            except Exception as e:
                                logger.warning(f"[state_transition_service] TTL 시점 가격 조회 실패, 현재 시점 사용: {ticker}, {e}")
                            
                            # flags 업데이트
                            flags_dict["assumption_broken"] = True
                            flags_dict["broken_at"] = today_str
                            flags_dict["broken_reason"] = "TTL_EXPIRED"
                            flags_dict["broken_anchor_return"] = ttl_return_pct
                            
                            # flags 업데이트 (v2 스키마: recommendation_id 사용)
                            with db_manager.get_cursor(commit=True) as update_cur:
                                update_cur.execute("""
                                    UPDATE recommendations
                                    SET flags = %s
                                    WHERE recommendation_id = %s
                                """, (
                                    json.dumps(flags_dict, ensure_ascii=False),
                                    rec_id
                                ))
                            
                            # 상태 전이 (ACTIVE/WEAK_WARNING → BROKEN) - TTL 시점 수익률 사용
                            transition_recommendation_status(
                                rec_id,
                                'BROKEN',
                                broken_reason,
                                {
                                    "current_return": ttl_return_pct,  # TTL 시점 수익률 사용
                                    "current_price": ttl_close,  # TTL 시점 가격 사용
                                    "anchor_close": anchor_close,
                                    "reason": broken_reason
                                }
                            )
                            
                            stats['broken'] += 1
                            continue  # BROKEN 전이 후 다음 추천으로
                        
                        # B) 무성과 종료 (10거래일 연속 abs(return) < 2%) → BROKEN으로 전환
                        # 단순화: 현재 abs(return) < 2%이고 10거래일 이상 경과
                        elif trading_days >= 10 and abs(current_return) < 2.0:
                            broken_reason = 'NO_MOMENTUM'
                            logger.info(f"[state_transition_service] 무성과 → BROKEN 전이: {ticker} ({name}), trading_days={trading_days}, return={current_return:.2f}%")
                            
                            # flags 업데이트
                            flags_dict["assumption_broken"] = True
                            flags_dict["broken_at"] = today_str
                            flags_dict["broken_reason"] = "NO_PERFORMANCE"
                            flags_dict["broken_anchor_return"] = round(current_return, 2)
                            
                            # flags 업데이트 (v2 스키마: recommendation_id 사용)
                            with db_manager.get_cursor(commit=True) as update_cur:
                                update_cur.execute("""
                                    UPDATE recommendations
                                    SET flags = %s
                                    WHERE recommendation_id = %s
                                """, (
                                    json.dumps(flags_dict, ensure_ascii=False),
                                    rec_id
                                ))
                            
                            # 상태 전이 (ACTIVE/WEAK_WARNING → BROKEN)
                            transition_recommendation_status(
                                rec_id,
                                'BROKEN',
                                broken_reason,
                                {
                                    "current_return": round(current_return, 2),
                                    "today_close": today_close,
                                    "anchor_close": anchor_close,
                                    "reason": broken_reason
                                }
                            )
                            
                            stats['broken'] += 1
                            continue  # BROKEN 전이 후 다음 추천으로
                    
                    # 3) ACTIVE 유지
                    logger.debug(f"[state_transition_service] ACTIVE 유지: {ticker} ({name}), current_return={current_return:.2f}% > {stop_loss_pct:.2f}%, trading_days={trading_days if anchor_date_obj else 'N/A'}")
                
                except Exception as e:
                    logger.error(f"[state_transition_service] 평가 오류 ({ticker}): {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    stats['errors'] += 1
        
        logger.info(f"[state_transition_service] 상태 평가 완료: {stats}")
        return stats
        
    except Exception as e:
        logger.error(f"[state_transition_service] 상태 평가 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())
        stats['errors'] += 1
        return stats


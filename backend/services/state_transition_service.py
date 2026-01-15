"""
v3 추천 상태 전이 서비스
ACTIVE → WEAK_WARNING → BROKEN → ARCHIVED 단방향 전이
"""
import logging
from typing import Dict, Optional, List
from datetime import datetime, timedelta, date
import json
import holidays

from db_manager import db_manager
from date_helper import get_kst_now, yyyymmdd_to_date

logger = logging.getLogger(__name__)


def get_trading_days_since(anchor_date, as_of_date: Optional[date] = None) -> int:
    """
    anchor_date부터 as_of_date(또는 오늘)까지의 거래일 수 계산
    
    중요: 추천 시점은 anchor_date입니다 (created_at이 아님)
    
    Args:
        anchor_date: datetime.date 또는 datetime 객체 (추천일)
        as_of_date: 기준일 (재처리 모드용), None이면 오늘
        
    Returns:
        거래일 수 (0 이상)
    """
    try:
        if isinstance(anchor_date, str):
            anchor_date = yyyymmdd_to_date(anchor_date.replace('-', '')[:8])
        if isinstance(anchor_date, datetime):
            anchor_date = anchor_date.date()
        
        # as_of_date가 없으면 오늘 사용 (운영 모드)
        if as_of_date is None:
            target_date = get_kst_now().date()
        else:
            target_date = as_of_date
        
        if anchor_date > target_date:
            return 0
        
        # 한국 공휴일
        kr_holidays = holidays.SouthKorea(years=range(anchor_date.year, target_date.year + 2))
        
        trading_days = 0
        current = anchor_date
        while current <= target_date:
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


def evaluate_active_recommendations(
    today_str: Optional[str] = None,
    *,
    mode: str = "OPERATION",
    filters: Optional[Dict] = None,
    dry_run: bool = False
) -> Dict:
    """
    ACTIVE 추천을 평가하여 상태 전이
    
    Args:
        today_str: 평가 기준일 (YYYYMMDD), None이면 오늘 (운영 모드)
        mode: 평가 모드 ("OPERATION" 또는 "BACKFILL")
            - OPERATION: 운영 모드 (기존 동작, 오늘 날짜 기준)
            - BACKFILL: 재처리 모드 (as_of_date 필수, 과거 날짜 기준)
        filters: 필터 조건 (재처리 모드용)
            - from_date: anchor_date 시작일 (YYYYMMDD)
            - to_date: anchor_date 종료일 (YYYYMMDD)
            - strategy: 전략 필터 (midterm, v2_lite 등)
            - status: 상태 필터 (ACTIVE, WEAK_WARNING, BROKEN)
            - limit: 제한 건수
        dry_run: True면 DB write 없이 결과만 반환
        
    Returns:
        평가 결과 통계
    """
    from kiwoom_api import api
    from date_helper import yyyymmdd_to_date
    
    # 모드 검증
    if mode not in ["OPERATION", "BACKFILL"]:
        raise ValueError(f"잘못된 모드: {mode} (OPERATION 또는 BACKFILL만 허용)")
    
    # 재처리 모드에서는 today_str 필수
    if mode == "BACKFILL":
        if today_str is None:
            raise ValueError("재처리 모드(BACKFILL)에서는 today_str(as_of_date)가 필수입니다")
        as_of_date_obj = yyyymmdd_to_date(today_str.replace('-', '')[:8])
    else:
        # 운영 모드: today_str이 None이면 오늘 사용
        if today_str is None:
            today_str = get_kst_now().strftime('%Y%m%d')
        as_of_date_obj = None
    
    logger.info(f"[state_transition_service] 상태 평가 시작: mode={mode}, as_of_date={today_str}, dry_run={dry_run}")
    
    stats = {
        'total_active': 0,
        'evaluated': 0,
        'broken': 0,
        'broken_no_momentum': 0,
        'broken_ttl_expired': 0,
        'broken_no_performance': 0,
        'weak_warning': 0,
        'archived_ttl': 0,  # TTL로 인한 ARCHIVED
        'archived_no_performance': 0,  # 무성과로 인한 ARCHIVED
        'errors': 0,
        'error_samples': []  # 오류 샘플 (최대 10건)
    }
    
    # 필터 조건 준비
    filters = filters or {}
    from_date = filters.get('from_date')
    to_date = filters.get('to_date')
    strategy_filter = filters.get('strategy')
    status_filter = filters.get('status', ['ACTIVE', 'WEAK_WARNING', 'BROKEN'])
    limit = filters.get('limit')
    
    # status_filter가 문자열이면 리스트로 변환
    if isinstance(status_filter, str):
        status_filter = [status_filter]
    
    try:
        with db_manager.get_cursor(commit=False) as cur:
            # BROKEN 상태인 추천 조회 (1거래일 이상 유지된 경우 ARCHIVED로 전환)
            # 필터 조건 적용
            query_parts = [
                "SELECT recommendation_id, ticker, status, anchor_date, anchor_close, strategy, flags, indicators, status_changed_at, reason, broken_return_pct, broken_at",
                "FROM recommendations",
                "WHERE status = 'BROKEN' AND scanner_version = 'v3'"
            ]
            params = []
            
            if from_date:
                query_parts.append("AND anchor_date >= %s")
                params.append(from_date)
            if to_date:
                query_parts.append("AND anchor_date <= %s")
                params.append(to_date)
            if strategy_filter:
                query_parts.append("AND strategy = %s")
                params.append(strategy_filter)
            
            query_parts.append("ORDER BY status_changed_at ASC, ticker")
            if limit:
                query_parts.append(f"LIMIT {limit}")
            
            cur.execute(" ".join(query_parts), tuple(params))
            
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
                        broken_at = broken_row.get('broken_at')
                    else:
                        broken_rec_id = broken_row[0]
                        broken_ticker = broken_row[1]
                        broken_status_changed_at = broken_row[8] if len(broken_row) > 8 else None
                        broken_reason = broken_row[9] if len(broken_row) > 9 else None
                        broken_return_pct = broken_row[10] if len(broken_row) > 10 else None
                        broken_at = broken_row[11] if len(broken_row) > 11 else None
                    
                    if not broken_ticker or broken_ticker == 'NORESULT':
                        continue
                    
                    # 정책: broken_at부터 거래일 계산 (status_changed_at이 아님)
                    # broken_at이 실제 BROKEN 발생일이므로, broken_at부터 계산해야 함
                    broken_date = None
                    if broken_at:
                        # broken_at 우선 사용 (실제 BROKEN 발생일)
                        if isinstance(broken_at, str):
                            broken_date = yyyymmdd_to_date(broken_at.replace('-', '')[:8])
                        elif isinstance(broken_at, datetime):
                            broken_date = broken_at.date()
                        elif hasattr(broken_at, 'date'):
                            broken_date = broken_at.date()
                        elif hasattr(broken_at, 'year'):
                            broken_date = broken_at
                    
                    # broken_at이 없으면 status_changed_at 사용 (fallback)
                    if broken_date is None and broken_status_changed_at:
                        if isinstance(broken_status_changed_at, str):
                            broken_date = yyyymmdd_to_date(broken_status_changed_at.replace('-', '')[:8])
                        elif isinstance(broken_status_changed_at, datetime):
                            broken_date = broken_status_changed_at.date()
                        elif hasattr(broken_status_changed_at, 'date'):
                            broken_date = broken_status_changed_at.date()
                        elif hasattr(broken_status_changed_at, 'year'):
                            broken_date = broken_status_changed_at
                    
                    if broken_date is None:
                        logger.warning(f"[state_transition_service] broken_at과 status_changed_at 모두 없음: {broken_ticker}, 건너뜀")
                        continue
                    
                    # BROKEN 진입일(broken_at)부터 as_of_date(또는 오늘)까지의 거래일 계산
                    broken_trading_days = get_trading_days_since(broken_date, as_of_date_obj)
                    
                    # 1거래일 이상 유지된 경우 ARCHIVED로 전환
                    if broken_trading_days >= 1:
                        logger.info(f"[state_transition_service] BROKEN → ARCHIVED 전이: {broken_ticker}, BROKEN 유지 기간: {broken_trading_days}거래일")
                        
                        # reason을 archive_reason으로 사용
                        archive_reason_code = broken_reason if broken_reason in ['TTL_EXPIRED', 'NO_MOMENTUM', 'NO_PERFORMANCE', 'MANUAL_ARCHIVE'] else 'NO_MOMENTUM'
                        
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
                            # broken_return_pct가 없으면 재처리 모드에서는 스킵 (fallback 금지)
                            if mode == "BACKFILL":
                                logger.warning(f"[state_transition_service] 재처리 모드: broken_return_pct 없음, ARCHIVED 전환 스킵: {broken_ticker}")
                                if len(stats['error_samples']) < 10:
                                    stats['error_samples'].append({
                                        'ticker': broken_ticker,
                                        'rec_id': str(broken_rec_id),
                                        'error': 'broken_return_pct 없음, ARCHIVED 전환 불가'
                                    })
                                stats['errors'] += 1
                                continue
                            else:
                                # 운영 모드: 현재 가격으로 계산 (fallback)
                                try:
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
                        if not dry_run:
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
                        else:
                            logger.info(f"[state_transition_service] [DRY RUN] ARCHIVED 전이 예정: {broken_ticker}, reason={archive_reason_code}")
                        
                        stats['archived_ttl'] += 1
                
                except Exception as e:
                    logger.error(f"[state_transition_service] BROKEN → ARCHIVED 전이 오류 ({broken_ticker}): {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    stats['errors'] += 1
            
            # ACTIVE/WEAK_WARNING 상태인 추천 조회 (v2 스키마: recommendation_id 사용)
            # anchor_date를 기준으로 조회 (추천 시점 = anchor_date)
            # 필터 조건 적용
            query_parts = [
                "SELECT recommendation_id, ticker, status, anchor_date, anchor_close, strategy, flags, indicators, status_changed_at",
                "FROM recommendations",
                f"WHERE status IN ({','.join(['%s'] * len(status_filter))}) AND scanner_version = 'v3'"
            ]
            params = list(status_filter)
            
            if from_date:
                query_parts.append("AND anchor_date >= %s")
                params.append(from_date)
            if to_date:
                query_parts.append("AND anchor_date <= %s")
                params.append(to_date)
            if strategy_filter:
                query_parts.append("AND strategy = %s")
                params.append(strategy_filter)
            
            query_parts.append("ORDER BY anchor_date DESC, ticker")
            if limit:
                query_parts.append(f"LIMIT {limit}")
            
            cur.execute(" ".join(query_parts), tuple(params))
            
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
                    
                    # anchor_date 기준으로 손절 조건 확인
                    # 백필 실행일(today_str)은 계산에 사용하지 않음
                    # anchor_date부터 시작하여 매일 확인하여 손절 기준에 도달한 첫 날짜를 찾음
                    
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
                    
                    if not anchor_date_obj:
                        logger.warning(f"[state_transition_service] anchor_date 변환 실패: {ticker}, anchor_date={anchor_date}")
                        continue
                    
                    anchor_date_str = anchor_date_obj.strftime('%Y%m%d') if hasattr(anchor_date_obj, 'strftime') else str(anchor_date_obj).replace('-', '')[:8]
                    
                    # anchor_date 이후의 OHLCV 데이터 조회 (TTL 기간 + 여유분)
                    # today_str은 단순히 "이 날짜까지 조회"하는 상한선일 뿐
                    max_days = 60  # TTL(25일) + 여유분
                    try:
                        df_range = api.get_ohlcv(ticker, max_days, today_str if mode == "BACKFILL" else None)
                        if df_range.empty or 'date' not in df_range.columns:
                            error_msg = f"OHLCV 데이터 없음: {ticker}, anchor_date={anchor_date_str}"
                            logger.warning(f"[state_transition_service] {error_msg}")
                            if mode == "BACKFILL":
                                if len(stats['error_samples']) < 10:
                                    stats['error_samples'].append({
                                        'ticker': ticker,
                                        'rec_id': str(rec_id),
                                        'error': error_msg
                                    })
                                stats['errors'] += 1
                                continue
                            else:
                                continue
                        
                        df_range['date_str'] = df_range['date'].astype(str).str.replace('-', '').str[:8]
                        # anchor_date 이후 데이터만 필터링
                        df_after_anchor = df_range[df_range['date_str'] >= anchor_date_str].copy()
                        df_after_anchor = df_after_anchor.sort_values('date_str')
                        
                        if df_after_anchor.empty:
                            error_msg = f"anchor_date 이후 데이터 없음: {ticker}, anchor_date={anchor_date_str}"
                            logger.warning(f"[state_transition_service] {error_msg}")
                            if mode == "BACKFILL":
                                if len(stats['error_samples']) < 10:
                                    stats['error_samples'].append({
                                        'ticker': ticker,
                                        'rec_id': str(rec_id),
                                        'error': error_msg
                                    })
                                stats['errors'] += 1
                                continue
                            else:
                                continue
                    except Exception as e:
                        error_msg = f"OHLCV 조회 실패: {ticker}, anchor_date={anchor_date_str}, error={str(e)}"
                        logger.warning(f"[state_transition_service] {error_msg}")
                        if mode == "BACKFILL":
                            if len(stats['error_samples']) < 10:
                                stats['error_samples'].append({
                                    'ticker': ticker,
                                    'rec_id': str(rec_id),
                                    'error': error_msg
                                })
                            stats['errors'] += 1
                            continue
                        else:
                            continue
                    
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
                    
                    # 손절 기준 확인: anchor_date부터 매일 확인하여 손절 기준에 도달한 첫 날짜 찾기
                    # 백필 실행일(today_str)은 계산에 사용하지 않음
                    actual_broken_at = None
                    broken_at_actual_return = None
                    broken_at_close = None
                    
                    # 매일 확인하여 손절 기준에 도달한 첫 날짜 찾기
                    for idx, row in df_after_anchor.iterrows():
                        day_close = float(row['close']) if 'close' in row else None
                        day_date_str = row['date_str']
                        
                        if day_close and anchor_close and anchor_close > 0:
                            day_return = ((day_close - float(anchor_close)) / float(anchor_close)) * 100
                            
                            # 손절 기준에 도달한 첫 날짜
                            if day_return <= stop_loss_pct:
                                actual_broken_at = day_date_str
                                broken_at_actual_return = round(day_return, 2)
                                broken_at_close = day_close
                                logger.info(f"[state_transition_service] 손절 기준 도달일 발견: {ticker}, 날짜={actual_broken_at}, 수익률={broken_at_actual_return:.2f}%")
                                break
                    
                    # 손절 기준에 도달한 경우 BROKEN 전이
                    if actual_broken_at:
                        # ACTIVE → BROKEN 전이
                        logger.info(f"[state_transition_service] BROKEN 전이: {ticker} ({name}), broken_at={actual_broken_at}, 수익률={broken_at_actual_return:.2f}%, stop_loss={stop_loss_pct:.2f}%")
                        
                        # 종료 사유 결정: 손절 조건 도달 = NO_MOMENTUM
                        broken_reason = 'NO_MOMENTUM'
                        
                        # flags 업데이트
                        flags_dict["assumption_broken"] = True
                        flags_dict["broken_at"] = actual_broken_at  # 손절 기준 도달한 정확한 날짜 (anchor_date 기준)
                        flags_dict["broken_reason"] = "HARD_STOP"
                        flags_dict["broken_anchor_return"] = broken_at_actual_return  # broken_at 시점의 실제 수익률
                        
                        # flags 업데이트 (v2 스키마: recommendation_id 사용)
                        if not dry_run:
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
                        # 정책: broken_return_pct는 broken_at 시점의 실제 종가로 계산한 손해율
                        # 손절 기준(-7%)에 도달했다는 것은 조건이지만, 실제 손해율은 그 시점의 종가로 계산
                        broken_return_for_db = broken_at_actual_return
                        
                        if not dry_run:
                            transition_recommendation_status(
                                rec_id,
                                'BROKEN',
                                broken_reason,  # reason_code로 전달
                                {
                                    "current_return": broken_return_for_db,  # broken_at 시점의 실제 수익률
                                    "stop_loss": stop_loss_pct,
                                    "today_close": broken_at_close,  # broken_at 시점의 종가
                                    "anchor_close": anchor_close,
                                    "reason": broken_reason,
                                    "broken_at": actual_broken_at,  # 손절 기준 도달한 정확한 날짜 (anchor_date 기준)
                                    "actual_return": broken_at_actual_return  # broken_at 시점의 실제 수익률
                                }
                            )
                        else:
                            logger.info(f"[state_transition_service] [DRY RUN] BROKEN 전이 예정: {ticker}, reason={broken_reason}, broken_at={actual_broken_at}")
                        
                        stats['broken'] += 1
                        stats['broken_no_momentum'] += 1
                        continue  # BROKEN 전이 후 다음 추천으로
                    
                    # 손절 기준에 도달하지 않은 경우, TTL 확인으로 진행
                    
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
                    
                    # TTL 만료일 계산 (anchor_date 기준, 백필 실행일과 무관)
                    from services.recommendation_service import get_nth_trading_day_after
                    ttl_expiry_str = get_nth_trading_day_after(anchor_date_str, ttl_days)
                    
                    if not ttl_expiry_str:
                        logger.warning(f"[state_transition_service] TTL 만료일 계산 실패: {ticker}, anchor_date={anchor_date_str}, ttl_days={ttl_days}")
                        continue
                    
                    # TTL 만료일이 anchor_date 이후 데이터 범위 내에 있는지 확인
                    ttl_expiry_in_range = False
                    ttl_expiry_close = None
                    ttl_expiry_return = None
                    
                    for idx, row in df_after_anchor.iterrows():
                        day_date_str = row['date_str']
                        if day_date_str == ttl_expiry_str:
                            ttl_expiry_close = float(row['close']) if 'close' in row else None
                            if ttl_expiry_close and anchor_close and anchor_close > 0:
                                ttl_expiry_return = round(((ttl_expiry_close - float(anchor_close)) / float(anchor_close)) * 100, 2)
                                ttl_expiry_in_range = True
                                break
                        elif day_date_str > ttl_expiry_str:
                            # TTL 만료일이 데이터 범위를 벗어남 (너무 미래)
                            break
                    
                    # TTL 만료일이 지났는지 확인
                    # anchor_date부터 TTL 만료일까지의 거래일 수 계산
                    ttl_expiry_date_obj = yyyymmdd_to_date(ttl_expiry_str)
                    trading_days_to_ttl = get_trading_days_since(anchor_date_obj, ttl_expiry_date_obj)
                    
                    # A) TTL 종료 (전략별 TTL 이상) → BROKEN으로 전환
                    # 정책: TTL 만료일 시점에 손절 조건을 확인
                    # - 손절 조건 충족: NO_MOMENTUM (TTL 만료일 시점 손절)
                    # - 손절 조건 미충족: TTL_EXPIRED (TTL 만료로 종료)
                    # 주의: trading_days_to_ttl >= ttl_days가 아니라, TTL 만료일이 지났는지만 확인
                    # (백필 실행일과 무관하게 anchor_date 기준으로만 계산)
                    # TTL 만료일이 지났는지 확인 (anchor_date 기준, 백필 실행일과 무관)
                    # trading_days_to_ttl은 anchor_date부터 ttl_expiry_str까지의 거래일 수
                    # ttl_days는 25거래일이므로, trading_days_to_ttl >= ttl_days는 항상 True (ttl_expiry_str이 정확히 25거래일 후이므로)
                    # 따라서 TTL 만료일이 데이터 범위 내에 있는지만 확인하면 됨
                    if ttl_expiry_in_range:
                        logger.info(f"[state_transition_service] TTL 종료 확인: {ticker} ({name}), TTL 만료일={ttl_expiry_str}, trading_days_to_ttl={trading_days_to_ttl}, ttl_days={ttl_days}")
                        
                        # TTL 만료일 시점의 수익률 사용 (이미 계산됨)
                        ttl_return_pct = ttl_expiry_return
                        ttl_close = ttl_expiry_close
                        logger.info(f"[state_transition_service] TTL 시점 수익률 사용: {ticker}, TTL 만료일={ttl_expiry_str}, 수익률={ttl_return_pct:.2f}%")
                        
                        # TTL 만료일 시점의 손절/손익 판정
                        if ttl_return_pct <= stop_loss_pct:
                            # TTL 만료일 시점 손절 → NO_MOMENTUM
                            broken_reason = 'NO_MOMENTUM'
                            logger.info(f"[state_transition_service] TTL 만료일 시점 손절 → BROKEN 전이: {ticker} ({name}), TTL 만료일={ttl_expiry_str}, 수익률={ttl_return_pct:.2f}%, stop_loss={stop_loss_pct:.2f}%")
                        elif ttl_return_pct < 0:
                            # 손절은 아니지만 손해 → NO_MOMENTUM
                            broken_reason = 'NO_MOMENTUM'
                            logger.info(f"[state_transition_service] TTL 만료일 손해 → BROKEN 전이: {ticker} ({name}), TTL 만료일={ttl_expiry_str}, 수익률={ttl_return_pct:.2f}%")
                        else:
                            # 수익이면 TTL_EXPIRED
                            broken_reason = 'TTL_EXPIRED'
                            logger.info(f"[state_transition_service] TTL 만료 → BROKEN 전이: {ticker} ({name}), TTL 만료일={ttl_expiry_str}, 수익률={ttl_return_pct:.2f}%")
                        
                        # TTL 만료일을 broken_at으로 사용
                        broken_at_date = ttl_expiry_str
                        
                        # flags 업데이트
                        flags_dict["assumption_broken"] = True
                        flags_dict["broken_at"] = broken_at_date
                        flags_dict["broken_reason"] = "HARD_STOP" if broken_reason == 'NO_MOMENTUM' and ttl_return_pct <= stop_loss_pct else broken_reason
                        flags_dict["broken_anchor_return"] = round(ttl_return_pct, 2)
                        
                        if not dry_run:
                            with db_manager.get_cursor(commit=True) as update_cur:
                                update_cur.execute("""
                                    UPDATE recommendations
                                    SET flags = %s
                                    WHERE recommendation_id = %s
                                """, (
                                    json.dumps(flags_dict, ensure_ascii=False),
                                    rec_id
                                ))
                        
                        if not dry_run:
                            transition_recommendation_status(
                                rec_id,
                                'BROKEN',
                                broken_reason,
                                {
                                    "current_return": round(ttl_return_pct, 2),
                                    "current_price": ttl_close,
                                    "anchor_close": anchor_close,
                                    "reason": broken_reason,
                                    "broken_at": broken_at_date,
                                    "stop_loss": stop_loss_pct,
                                    "actual_return": round(ttl_return_pct, 2)
                                }
                            )
                        else:
                            logger.info(f"[state_transition_service] [DRY RUN] BROKEN 전이 예정: {ticker}, reason={broken_reason}, broken_at={broken_at_date}")
                        
                        stats['broken'] += 1
                        if broken_reason == 'TTL_EXPIRED':
                            stats['broken_ttl_expired'] += 1
                        else:
                            stats['broken_no_momentum'] += 1
                        continue  # BROKEN 전이 후 다음 추천으로
                    
                    # B) 무성과 종료는 운영 모드에서만 처리 (백필 모드에서는 제외)
                    # NO_PERFORMANCE 로직은 anchor_date 기준으로 계산해야 하므로 복잡함
                    # 현재는 운영 모드에서만 동작하도록 유지
                    # TODO: 백필 모드에서도 NO_PERFORMANCE 처리 필요 시 별도 구현
                    
                    # 3) ACTIVE 유지
                    logger.debug(f"[state_transition_service] ACTIVE 유지: {ticker} ({name}), 손절 기준 미도달, TTL 미만료")
                
                except Exception as e:
                    error_msg = f"평가 오류: {ticker}, error={str(e)}"
                    logger.error(f"[state_transition_service] {error_msg}")
                    import traceback
                    logger.error(traceback.format_exc())
                    if len(stats['error_samples']) < 10:
                        stats['error_samples'].append({
                            'ticker': ticker,
                            'rec_id': str(rec_id) if 'rec_id' in locals() else 'unknown',
                            'error': error_msg
                        })
                    stats['errors'] += 1
        
        logger.info(f"[state_transition_service] 상태 평가 완료: {stats}")
        return stats
        
    except Exception as e:
        logger.error(f"[state_transition_service] 상태 평가 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())
        stats['errors'] += 1
        return stats

"""
v3 추천 시스템 서비스 v2
UUID 기반, 트랜잭션 안전한 추천 생성 및 상태 전이
"""
import logging
from typing import List, Dict, Optional, Tuple, Union
from datetime import datetime, timedelta, date
import json
import uuid

from db_manager import db_manager
from date_helper import yyyymmdd_to_date, get_trading_date, get_anchor_close

logger = logging.getLogger(__name__)


def create_recommendation_transaction(
    ticker: str,
    anchor_date: date,
    anchor_close: int,
    anchor_source: str = "KRX_EOD",
    reason_code: str = "RECOMMEND_CREATED",
    name: Optional[str] = None,
    strategy: Optional[str] = None,
    scanner_version: str = "v3",
    score: Optional[float] = None,
    score_label: Optional[str] = None,
    indicators: Optional[Dict] = None,
    flags: Optional[Dict] = None,
    details: Optional[Dict] = None
) -> Optional[uuid.UUID]:
    """
    추천 생성 트랜잭션 (중복 ACTIVE 방지 + 기존 추천 대체)
    
    정책:
    - 동일 ticker ACTIVE는 1개만 (partial unique index가 최후 방어)
    - 기존 ACTIVE가 있으면 REPLACED로 전환 후 신규 ACTIVE 생성
    - anchor_date/anchor_close는 생성 시점에 1회 고정 저장
    
    Args:
        ticker: 종목 코드
        anchor_date: 추천 기준 거래일
        anchor_close: 추천 기준 종가 (INTEGER, 원 단위)
        anchor_source: 데이터 소스
        reason_code: 생성 이유 코드
        name: 종목명 (선택)
        strategy: 전략 (선택)
        scanner_version: 스캐너 버전
        score: 점수 (선택)
        score_label: 점수 레이블 (선택)
        indicators: 지표 데이터 (선택)
        flags: 플래그 데이터 (선택)
        details: 상세 데이터 (선택)
        
    Returns:
        생성된 추천 ID (UUID, 실패 시 None)
    """
    new_id = uuid.uuid4()
    
    try:
        with db_manager.get_cursor(commit=True) as cur:
            # (A) 기존 ACTIVE를 잠그고(동시성 제어), 있으면 대체 처리
            # REPLACED 상태 전이 시에도 status_changed_at 갱신 및 archive 정보 저장
            # 먼저 기존 ACTIVE 정보 조회 (strategy 포함)
            cur.execute("""
                SELECT recommendation_id, anchor_date, anchor_close, strategy
                FROM recommendations
                WHERE ticker = %s AND status = 'ACTIVE'
                FOR UPDATE
            """, (ticker,))
            
            existing_active_rows = cur.fetchall()
            
            if existing_active_rows:
                # 거래일 계산 및 archive 정보 준비
                from services.state_transition_service import get_trading_days_since
                from kiwoom_api import api
                from date_helper import get_kst_now
                
                today_str = get_kst_now().strftime('%Y%m%d')
                
                for existing_row in existing_active_rows:
                    existing_rec_id = existing_row[0] if isinstance(existing_row, (list, tuple)) else existing_row.get('recommendation_id')
                    existing_anchor_date = existing_row[1] if isinstance(existing_row, (list, tuple)) else existing_row.get('anchor_date')
                    existing_anchor_close = existing_row[2] if isinstance(existing_row, (list, tuple)) else existing_row.get('anchor_close')
                    existing_strategy = existing_row[3] if isinstance(existing_row, (list, tuple)) and len(existing_row) > 3 else existing_row.get('strategy')
                    
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
                            trading_days = get_trading_days_since(existing_anchor_date)
                            # TTL 체크: 전략별 TTL 이상이면 TTL_EXPIRED로 설정
                            if trading_days >= ttl_days:
                                archive_reason = 'TTL_EXPIRED'
                            else:
                                archive_reason = 'REPLACED'
                        except Exception as e:
                            logger.warning(f"[create_recommendation_transaction] 거래일 계산 실패 (ticker={ticker}): {e}")
                    
                    # 현재 가격 조회 (archive_return_pct 계산용)
                    archive_return_pct = None
                    archive_price = None
                    archive_phase = None
                    
                    try:
                        # 전이 시점의 정확한 가격 조회 (today_str 기준)
                        df_today = api.get_ohlcv(ticker, 10, today_str)
                        if not df_today.empty:
                            # today_str과 일치하는 행 찾기 (정확한 날짜의 가격 사용)
                            current_price = None
                            actual_price_date = today_str
                            
                            if 'date' in df_today.columns:
                                df_today['date_str'] = df_today['date'].astype(str).str.replace('-', '').str[:8]
                                df_filtered = df_today[df_today['date_str'] == today_str]
                                if not df_filtered.empty:
                                    current_price = float(df_filtered.iloc[-1]['close'])
                                    actual_price_date = today_str
                                else:
                                    # 정확히 일치하는 날짜가 없으면 가장 가까운 이전 거래일 데이터 사용
                                    df_sorted = df_today.sort_values('date_str')
                                    df_before = df_sorted[df_sorted['date_str'] <= today_str]
                                    if not df_before.empty:
                                        current_price = float(df_before.iloc[-1]['close'])
                                        actual_price_date = df_before.iloc[-1]['date_str']
                                    else:
                                        # 마지막 행 사용
                                        current_price = float(df_today.iloc[-1]['close']) if 'close' in df_today.columns else float(df_today.iloc[-1].values[0])
                                        if 'date_str' in df_today.columns:
                                            actual_price_date = df_today.iloc[-1]['date_str']
                            else:
                                # date 컬럼이 없으면 마지막 행 사용 (base_dt 이하의 최근 데이터)
                                current_price = float(df_today.iloc[-1]['close']) if 'close' in df_today.columns else float(df_today.iloc[-1].values[0])
                            
                            # archive_return_pct 계산 (전이 시점의 정확한 가격 사용)
                            if existing_anchor_close and existing_anchor_close > 0 and current_price:
                                archive_return_pct = round(((current_price - float(existing_anchor_close)) / float(existing_anchor_close)) * 100, 2)
                                archive_price = current_price
                                
                                # 로그: 실제 가격이 조회된 날짜 확인
                                if actual_price_date != today_str:
                                    logger.debug(f"[create_recommendation_transaction] {ticker}: 요청일({today_str})의 데이터가 없어 {actual_price_date} 날짜의 가격 사용")
                                
                                # archive_phase 결정
                                if archive_return_pct > 2:
                                    archive_phase = 'PROFIT'
                                elif archive_return_pct < -2:
                                    archive_phase = 'LOSS'
                                else:
                                    archive_phase = 'FLAT'
                    except Exception as e:
                        logger.warning(f"[create_recommendation_transaction] 현재 가격 조회 실패 (ticker={ticker}): {e}")
                    
                    # REPLACED 상태로 전이 (archive 정보 포함)
                    cur.execute("""
                        UPDATE recommendations
                        SET status = 'REPLACED',
                            replaced_by_recommendation_id = %s,
                            archived_at = NOW(),
                            archive_reason = %s,
                            archive_return_pct = %s,
                            archive_price = %s,
                            archive_phase = %s,
                            updated_at = NOW(),
                            status_changed_at = NOW()
                        WHERE recommendation_id = %s
                    """, (new_id, archive_reason, archive_return_pct, archive_price, archive_phase, existing_rec_id))
            
            replaced_count = len(existing_active_rows) if existing_active_rows else 0
            
            replaced_count = cur.rowcount
            if replaced_count > 0:
                logger.info(f"[create_recommendation_transaction] 기존 ACTIVE {replaced_count}개를 REPLACED로 전환: {ticker}")
            
            # (B) 신규 추천 이벤트 생성 (ACTIVE)
            # 기존 REPLACED 추천의 ID를 찾아서 replaces_recommendation_id에 설정
            # status_changed_at은 초기 생성 시점(ACTIVE)으로 설정
            cur.execute("""
                INSERT INTO recommendations (
                    recommendation_id,
                    ticker,
                    name,
                    anchor_date,
                    anchor_close,
                    anchor_price_type,
                    anchor_source,
                    status,
                    status_changed_at,
                    replaces_recommendation_id,
                    strategy,
                    scanner_version,
                    score,
                    score_label,
                    indicators,
                    flags,
                    details
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, NOW(),
                    (
                        SELECT recommendation_id
                        FROM recommendations
                        WHERE ticker = %s AND status = 'REPLACED'
                            AND replaced_by_recommendation_id = %s
                        ORDER BY created_at DESC
                        LIMIT 1
                    ),
                    %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                new_id,
                ticker,
                name,  # 종목명 추가
                anchor_date,
                anchor_close,
                'CLOSE',
                anchor_source,
                'ACTIVE',
                ticker,  # replaces_recommendation_id 서브쿼리용
                new_id,  # replaces_recommendation_id 서브쿼리용
                strategy,
                scanner_version,
                score,
                score_label,
                json.dumps(indicators or {}, ensure_ascii=False),
                json.dumps(flags or {}, ensure_ascii=False),
                json.dumps(details or {}, ensure_ascii=False)
            ))
            
            # (C) 상태 이벤트 로그 기록 (생성)
            cur.execute("""
                INSERT INTO recommendation_state_events (
                    event_id, recommendation_id, from_status, to_status, reason_code
                )
                VALUES (
                    gen_random_uuid(), %s, NULL, 'ACTIVE', %s
                )
            """, (new_id, reason_code))
            
            logger.info(f"[create_recommendation_transaction] 추천 생성 완료: {ticker} (ID: {new_id}, anchor_date: {anchor_date}, anchor_close: {anchor_close})")
            return new_id
            
    except Exception as e:
        logger.error(f"[create_recommendation_transaction] 추천 생성 오류 ({ticker}): {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def transition_recommendation_status_transaction(
    recommendation_id: uuid.UUID,
    to_status: str,
    reason_code: str,
    reason_text: Optional[str] = None,
    metadata: Optional[Dict] = None
) -> bool:
    """
    상태 전이 트랜잭션 (단방향 + 로그 기록)
    
    정책:
    - ACTIVE -> WEAK_WARNING -> BROKEN -> ARCHIVED 단방향
    - BROKEN -> ACTIVE 복귀 금지
    - 상태 변경은 반드시 recommendation_state_events에 기록
    
    Args:
        recommendation_id: 추천 ID (UUID)
        to_status: 변경할 상태 ('WEAK_WARNING'|'BROKEN'|'ARCHIVED')
        reason_code: 상태 변경 이유 코드
        reason_text: 상태 변경 이유 텍스트 (선택)
        metadata: 추가 메타데이터 (선택)
        
    Returns:
        성공 여부
    """
    valid_statuses = ['ACTIVE', 'WEAK_WARNING', 'BROKEN', 'ARCHIVED', 'REPLACED']
    if to_status not in valid_statuses:
        logger.error(f"[transition_recommendation_status_transaction] 잘못된 상태: {to_status}")
        return False
    
    try:
        with db_manager.get_cursor(commit=True) as cur:
            # 현재 상태를 잠그고 가져온다
            cur.execute("""
                WITH cur AS (
                    SELECT recommendation_id, status AS from_status
                    FROM recommendations
                    WHERE recommendation_id = %s
                    FOR UPDATE
                ),
                validate AS (
                    SELECT
                        recommendation_id,
                        from_status,
                        %s::TEXT AS to_status,
                        CASE
                            WHEN from_status = %s THEN false
                            WHEN from_status = 'ARCHIVED' THEN false
                            WHEN from_status = 'REPLACED' THEN false
                            WHEN from_status = 'BROKEN' AND %s = 'ACTIVE' THEN false
                            WHEN from_status = 'ACTIVE' AND %s IN ('WEAK_WARNING','BROKEN','ARCHIVED') THEN true
                            WHEN from_status = 'WEAK_WARNING' AND %s IN ('BROKEN','ARCHIVED','ACTIVE') THEN true
                            WHEN from_status = 'BROKEN' AND %s IN ('ARCHIVED') THEN true
                            ELSE false
                        END AS ok
                    FROM cur
                )
                SELECT recommendation_id, from_status, to_status, ok
                FROM validate
            """, (recommendation_id, to_status, to_status, to_status, to_status, to_status, to_status))
            
            validation = cur.fetchone()
            if not validation:
                logger.error(f"[transition_recommendation_status_transaction] 추천을 찾을 수 없음: {recommendation_id}")
                return False
            
            if isinstance(validation, dict):
                rec_id = validation.get('recommendation_id')
                from_status = validation.get('from_status')
                to_status_val = validation.get('to_status')
                ok = validation.get('ok')
            else:
                rec_id = validation[0]
                from_status = validation[1]
                to_status_val = validation[2]
                ok = validation[3]
            
            if not ok:
                logger.warning(f"[transition_recommendation_status_transaction] 잘못된 상태 전이: {from_status} → {to_status} (ID: {recommendation_id})")
                return False
            
            # BROKEN 전환 시 reason 및 broken_return_pct 저장
            if to_status == 'BROKEN':
                # reason_code를 정확한 값으로 검증
                if reason_code and isinstance(reason_code, str):
                    broken_reason = reason_code.upper().strip()
                    if broken_reason not in ['TTL_EXPIRED', 'NO_MOMENTUM', 'MANUAL_ARCHIVE']:
                        # 기본값: NO_MOMENTUM (손절 조건 도달)
                        broken_reason = 'NO_MOMENTUM'
                else:
                    # reason_code가 없거나 유효하지 않으면 기본값
                    broken_reason = 'NO_MOMENTUM'
                
                # broken_return_pct 계산 (종료 시점 고정)
                broken_return_pct = None
                if metadata and metadata.get('current_return') is not None:
                    broken_return_pct = round(float(metadata.get('current_return')), 2)
                elif metadata and metadata.get('current_price') is not None and metadata.get('anchor_close') is not None:
                    current_price = float(metadata.get('current_price'))
                    anchor_close = float(metadata.get('anchor_close'))
                    if anchor_close > 0:
                        broken_return_pct = round(((current_price - anchor_close) / anchor_close) * 100, 2)
                
                cur.execute("""
                    UPDATE recommendations
                    SET status = %s,
                        updated_at = NOW(),
                        status_changed_at = NOW(),
                        reason = %s,
                        broken_return_pct = %s
                    WHERE recommendation_id = %s
                """, (to_status, broken_reason, broken_return_pct, recommendation_id))
            
            # ARCHIVED 전환 시 스냅샷 저장
            archive_snapshot = None
            if to_status == 'ARCHIVED' and metadata:
                # metadata에서 스냅샷 정보 추출
                current_return = metadata.get('current_return')
                current_price = metadata.get('current_price')
                anchor_close = metadata.get('anchor_close')
                
                # archive_reason 결정
                # 1) BROKEN에서 전환된 경우: reason을 archive_reason으로 복사
                # 2) ACTIVE에서 직접 전환된 경우: reason_code 기반으로 결정
                if from_status == 'BROKEN':
                    # BROKEN의 reason을 archive_reason으로 복사
                    cur.execute("""
                        SELECT reason FROM recommendations WHERE recommendation_id = %s
                    """, (recommendation_id,))
                    reason_row = cur.fetchone()
                    if reason_row and reason_row[0]:
                        archive_reason = reason_row[0]
                    else:
                        # reason이 없으면 기본값
                        archive_reason = 'NO_MOMENTUM'
                else:
                    # ACTIVE에서 직접 전환: reason_code 기반으로 정확한 값 비교
                    if reason_code and isinstance(reason_code, str):
                        reason_code_upper = reason_code.upper().strip()
                        # 정확한 값 비교 (문자열 매칭 대신)
                        if reason_code_upper == 'TTL_EXPIRED':
                            archive_reason = 'TTL_EXPIRED'
                        elif reason_code_upper == 'NO_MOMENTUM' or reason_code_upper == 'NO_PERFORMANCE':
                            archive_reason = 'NO_MOMENTUM'
                        elif reason_code_upper == 'MANUAL_ARCHIVE':
                            archive_reason = 'MANUAL_ARCHIVE'
                        else:
                            # 알 수 없는 값이면 기본값
                            archive_reason = 'NO_MOMENTUM'
                    else:
                        # reason_code가 없거나 유효하지 않으면 기본값
                        archive_reason = 'NO_MOMENTUM'
                
                # archive_return_pct 계산
                archive_return_pct = None
                if current_return is not None:
                    archive_return_pct = round(float(current_return), 2)
                elif current_price is not None and anchor_close is not None and anchor_close > 0:
                    archive_return_pct = round(((float(current_price) - float(anchor_close)) / float(anchor_close)) * 100, 2)
                
                # archive_price 설정
                archive_price = None
                if current_price is not None:
                    archive_price = float(current_price)
                
                # archive_phase 결정
                archive_phase = None
                if archive_return_pct is not None:
                    if archive_return_pct > 2:
                        archive_phase = 'PROFIT'
                    elif archive_return_pct < -2:
                        archive_phase = 'LOSS'
                    else:
                        archive_phase = 'FLAT'
                
                archive_snapshot = {
                    'archive_at': 'NOW()',
                    'archive_reason': archive_reason,
                    'archive_return_pct': archive_return_pct,
                    'archive_price': archive_price,
                    'archive_phase': archive_phase
                }
            
            # 유효할 때만 상태 업데이트 (status_changed_at도 함께 갱신)
            if archive_snapshot:
                # ARCHIVED 전환 시 스냅샷 포함
                cur.execute("""
                    UPDATE recommendations
                    SET status = %s,
                        updated_at = NOW(),
                        status_changed_at = NOW(),
                        archived_at = NOW(),
                        archive_reason = %s,
                        archive_return_pct = %s,
                        archive_price = %s,
                        archive_phase = %s
                    WHERE recommendation_id = %s
                """, (
                    to_status,
                    archive_snapshot['archive_reason'],
                    archive_snapshot['archive_return_pct'],
                    archive_snapshot['archive_price'],
                    archive_snapshot['archive_phase'],
                    recommendation_id
                ))
            elif to_status != 'BROKEN':
                # BROKEN이 아닌 일반 상태 전이 (BROKEN은 위에서 이미 처리됨)
                cur.execute("""
                    UPDATE recommendations
                    SET status = %s,
                        updated_at = NOW(),
                        status_changed_at = NOW()
                    WHERE recommendation_id = %s
                """, (to_status, recommendation_id))
            
            # 실제로 업데이트가 일어났을 때만 로그를 남긴다
            cur.execute("""
                INSERT INTO recommendation_state_events (
                    event_id, recommendation_id, from_status, to_status, reason_code, reason_text, metadata
                )
                VALUES (
                    gen_random_uuid(), %s, %s, %s, %s, %s, %s
                )
            """, (
                recommendation_id,
                from_status,
                to_status,
                reason_code,
                reason_text,
                json.dumps(metadata or {}, ensure_ascii=False) if metadata else None
            ))
            
            logger.info(f"[transition_recommendation_status_transaction] 상태 전이 완료: {recommendation_id} ({from_status} → {to_status})")
            return True
            
    except Exception as e:
        logger.error(f"[transition_recommendation_status_transaction] 상태 전이 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def get_active_recommendations() -> List[Dict]:
    """
    ACTIVE 추천 조회 (ticker 당 1개 보장)
    
    Returns:
        ACTIVE 추천 목록
    """
    try:
        with db_manager.get_cursor(commit=False) as cur:
            cur.execute("""
                SELECT 
                    recommendation_id, ticker, name, status,
                    anchor_date, anchor_close, anchor_price_type, anchor_source,
                    strategy, scanner_version, score, score_label,
                    indicators, flags, details,
                    created_at, updated_at,
                    replaces_recommendation_id, replaced_by_recommendation_id,
                    cooldown_until
                FROM recommendations
                WHERE status = 'ACTIVE'
                ORDER BY created_at DESC
            """)
            
            rows = cur.fetchall()
            
            items = []
            for row in rows:
                if isinstance(row, dict):
                    item = dict(row)
                else:
                    # 컬럼 순서에 맞게 매핑
                    item = {
                        "recommendation_id": row[0],
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
                        "replaces_recommendation_id": row[17] if len(row) > 17 else None,
                        "replaced_by_recommendation_id": row[18] if len(row) > 18 else None,
                        "cooldown_until": row[19] if len(row) > 19 else None
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
                
                items.append(item)
            
            return items
            
    except Exception as e:
        logger.error(f"[get_active_recommendations] ACTIVE 추천 조회 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []


def check_duplicate_active_recommendations() -> List[Dict]:
    """
    중복 ACTIVE 점검 (모니터링용)
    결과가 나오면 시스템 이상
    
    Returns:
        중복 ACTIVE가 있는 ticker 목록
    """
    try:
        with db_manager.get_cursor(commit=False) as cur:
            cur.execute("""
                SELECT ticker, COUNT(*) as count
                FROM recommendations
                WHERE status = 'ACTIVE'
                GROUP BY ticker
                HAVING COUNT(*) > 1
            """)
            
            rows = cur.fetchall()
            
            duplicates = []
            for row in rows:
                if isinstance(row, dict):
                    duplicates.append({
                        "ticker": row.get("ticker"),
                        "count": row.get("count")
                    })
                else:
                    duplicates.append({
                        "ticker": row[0],
                        "count": row[1]
                    })
            
            if duplicates:
                logger.warning(f"[check_duplicate_active_recommendations] 중복 ACTIVE 발견: {len(duplicates)}개 ticker")
                for dup in duplicates:
                    logger.warning(f"  - {dup['ticker']}: {dup['count']}개 ACTIVE")
            
            return duplicates
            
    except Exception as e:
        logger.error(f"[check_duplicate_active_recommendations] 중복 ACTIVE 점검 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []


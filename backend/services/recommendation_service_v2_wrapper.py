"""
v3 추천 시스템 서비스 v2 래퍼
기존 API와의 호환성을 위한 래퍼 함수
"""
import logging
from typing import List, Dict, Optional
from datetime import date
import uuid

from services.recommendation_service_v2 import (
    create_recommendation_transaction,
    transition_recommendation_status_transaction,
    get_active_recommendations,
    check_duplicate_active_recommendations
)
from date_helper import yyyymmdd_to_date, get_trading_date, get_anchor_close

logger = logging.getLogger(__name__)


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
) -> Optional[str]:
    """
    추천 생성 (기존 API 호환)
    
    Args:
        ticker: 종목 코드
        name: 종목명
        scan_date: 스캔 날짜 (YYYYMMDD)
        strategy: 전략
        score: 점수
        score_label: 점수 레이블
        indicators: 지표 데이터
        flags: 플래그 데이터
        details: 상세 데이터
        scanner_version: 스캐너 버전
        
    Returns:
        생성된 추천 ID (UUID 문자열, 실패 시 None)
    """
    try:
        # anchor_date 결정 (거래일 보장)
        anchor_date_str = get_trading_date(scan_date)
        anchor_date_obj = yyyymmdd_to_date(anchor_date_str)
        
        # anchor_close 결정 (1회 확정 저장, 재계산 금지)
        anchor_close_value = get_anchor_close(ticker, anchor_date_str, price_type="CLOSE")
        if anchor_close_value is None:
            logger.warning(f"[create_recommendation] anchor_close 조회 실패 ({ticker}), 스캔 결과 종가 사용")
            # indicators에서 종가 추출
            if isinstance(indicators, dict):
                anchor_close_value = indicators.get("close")
            if not anchor_close_value or anchor_close_value <= 0:
                logger.error(f"[create_recommendation] anchor_close 결정 불가 ({ticker})")
                return None
        
        # INTEGER로 변환 (원 단위)
        anchor_close_int = int(round(anchor_close_value))
        
        # 추천 생성 트랜잭션 호출
        rec_id = create_recommendation_transaction(
            ticker=ticker,
            anchor_date=anchor_date_obj,
            anchor_close=anchor_close_int,
            anchor_source="KRX_EOD",
            reason_code="RECOMMEND_CREATED",
            name=name,
            strategy=strategy,
            scanner_version=scanner_version,
            score=score,
            score_label=score_label,
            indicators=indicators,
            flags=flags,
            details=details
        )
        
        if rec_id:
            return str(rec_id)
        return None
        
    except Exception as e:
        logger.error(f"[create_recommendation] 추천 생성 오류 ({ticker}): {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def transition_recommendation_status(
    recommendation_id: Union[str, uuid.UUID],
    to_status: str,
    reason: str,
    metadata: Optional[Dict] = None
) -> bool:
    """
    상태 전이 (기존 API 호환)
    
    Args:
        recommendation_id: 추천 ID (UUID 문자열 또는 UUID 객체)
        to_status: 변경할 상태
        reason: 상태 변경 이유
        metadata: 추가 메타데이터
        
    Returns:
        성공 여부
    """
    try:
        # UUID 변환
        if isinstance(recommendation_id, str):
            rec_uuid = uuid.UUID(recommendation_id)
        else:
            rec_uuid = recommendation_id
        
        # reason을 reason_code와 reason_text로 분리
        reason_code = reason
        reason_text = reason
        
        return transition_recommendation_status_transaction(
            recommendation_id=rec_uuid,
            to_status=to_status,
            reason_code=reason_code,
            reason_text=reason_text,
            metadata=metadata
        )
        
    except Exception as e:
        logger.error(f"[transition_recommendation_status] 상태 전이 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False



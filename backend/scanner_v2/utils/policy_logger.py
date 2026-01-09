"""
Regime v4 정책 로깅 유틸리티

레짐 분석 및 정책 적용 결과를 로그와 JSONL 파일로 기록합니다.
"""
import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# 로그 파일 경로
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# JSONL 파일 경로
JSONL_DIR = Path(__file__).parent.parent.parent / "backtest" / "output"
JSONL_DIR.mkdir(parents=True, exist_ok=True)
JSONL_FILE = JSONL_DIR / "regime_policy_shadow_log.jsonl"


def log_policy_application(
    scan_date: str,
    mode: str,
    final_regime: Optional[str],
    risk_label: Optional[str],
    grade: Optional[str],
    top_n: Optional[int],
    candidates_before: int,
    candidates_after: Optional[int],
    apply_success: bool,
    error: Optional[str] = None,
    reason: Optional[str] = None,
    snapshot: Optional[Dict[str, Any]] = None,
    candidates_list: Optional[List[Dict[str, Any]]] = None
) -> None:
    """
    정책 적용 결과를 로그와 JSONL 파일로 기록
    
    Args:
        scan_date: 스캔 날짜 (YYYYMMDD)
        mode: 정책 모드 ("off", "on", "shadow")
        final_regime: 최종 레짐 (bull/neutral/bear/crash)
        risk_label: 리스크 레이블 (normal/elevated/stressed)
        grade: 정책 등급 (STRONG/NORMAL/CAUTION/OFF)
        top_n: 적용된 top_n 값
        candidates_before: 정책 적용 전 candidates 수
        candidates_after: 정책 적용 후 candidates 수 (가정값 포함)
        apply_success: 정책 적용 성공 여부
        error: 에러 메시지 (있는 경우)
        reason: 정책 결정 이유
        snapshot: 레짐 스냅샷 정보
    """
    # off 모드는 기록하지 않음
    if mode == "off":
        return
    
    # 로그 레코드 생성
    log_record = {
        "scan_date": scan_date,
        "mode": mode,
        "final_regime": final_regime,
        "risk_label": risk_label,
        "grade": grade,
        "top_n": top_n,
        "candidates_before": candidates_before,
        "candidates_after": candidates_after,
        "apply_success": apply_success,
        "error": error,
        "reason": reason,
        "snapshot": snapshot,
        "candidates": candidates_list,  # shadow 모드에서 후보 리스트 저장
        "timestamp": datetime.now().isoformat()
    }
    
    # JSONL 파일에 기록
    try:
        with open(JSONL_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_record, ensure_ascii=False) + '\n')
    except Exception as e:
        logger.warning(f"JSONL 로그 기록 실패: {e}")
    
    # 로그 출력
    if apply_success:
        logger.info(
            f"📊 Regime v4 정책 [{mode}]: {grade} (top_n={top_n}) "
            f"- {final_regime}/{risk_label} - {candidates_before}→{candidates_after} - {reason}"
        )
    else:
        logger.warning(
            f"⚠️ Regime v4 정책 [{mode}] 실패: {error} "
            f"(레짐: {final_regime}/{risk_label}, candidates: {candidates_before})"
        )

























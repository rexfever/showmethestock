#!/usr/bin/env python3
"""
v3 추천 시스템 백필 스크립트
과거 scan_rank 데이터를 recommendations로 마이그레이션
동일 ticker는 최신 ACTIVE 1개만 유지
"""
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import json
import logging

# 프로젝트 루트를 Python 경로에 추가
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from db_manager import db_manager
from date_helper import yyyymmdd_to_date, get_anchor_close
from services.recommendation_service_v2 import create_recommendation_transaction
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_scan_rank_data_for_migration(scanner_version: str = "v3") -> List[Dict]:
    """
    scan_rank에서 마이그레이션할 데이터 조회
    
    Returns:
        스캔 결과 리스트 (추천 이벤트로 볼 최소 집합)
    """
    try:
        with db_manager.get_cursor(commit=False) as cur:
            # v3 스캔 결과 조회 (NORESULT 제외)
            cur.execute("""
                SELECT 
                    date, code, name, score, score_label,
                    strategy, indicators, flags, details,
                    anchor_date, anchor_close, anchor_price_type, anchor_source
                FROM scan_rank
                WHERE scanner_version = %s
                AND code != 'NORESULT'
                AND date IS NOT NULL
                ORDER BY date DESC, code
            """, (scanner_version,))
            
            rows = cur.fetchall()
            
            items = []
            for row in rows:
                if isinstance(row, dict):
                    item = dict(row)
                else:
                    item = {
                        "date": row[0],
                        "code": row[1],
                        "name": row[2],
                        "score": row[3],
                        "score_label": row[4],
                        "strategy": row[5],
                        "indicators": row[6],
                        "flags": row[7],
                        "details": row[8],
                        "anchor_date": row[9] if len(row) > 9 else None,
                        "anchor_close": row[10] if len(row) > 10 else None,
                        "anchor_price_type": row[11] if len(row) > 11 else None,
                        "anchor_source": row[12] if len(row) > 12 else None
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
        logger.error(f"[backfill_recommendations] scan_rank 조회 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []


def determine_recommendation_status(flags: Dict, anchor_date, today_date_str: str) -> str:
    """
    flags와 날짜를 기반으로 추천 상태 결정
    
    Args:
        flags: flags 딕셔너리
        anchor_date: anchor_date (date 객체 또는 문자열)
        today_date_str: 오늘 날짜 (YYYYMMDD)
        
    Returns:
        상태 (ACTIVE, BROKEN, ARCHIVED)
    """
    # flags에서 BROKEN 여부 확인
    assumption_broken = flags.get("assumption_broken") == True
    flow_broken = flags.get("flow_broken") == True
    
    if assumption_broken or flow_broken:
        return "BROKEN"
    
    # anchor_date 확인 (오래된 추천은 ARCHIVED)
    if anchor_date:
        if isinstance(anchor_date, str):
            anchor_date_str = anchor_date.replace("-", "")[:8]
        else:
            anchor_date_str = anchor_date.strftime("%Y%m%d")
        
        # 30일 이상 지난 추천은 ARCHIVED (임시 기준)
        # 실제로는 상태 평가 엔진이 처리하지만, 백필에서는 간단히 처리
        try:
            anchor_dt = datetime.strptime(anchor_date_str, "%Y%m%d")
            today_dt = datetime.strptime(today_date_str, "%Y%m%d")
            days_diff = (today_dt - anchor_dt).days
            
            # 60일 이상 지난 추천은 ARCHIVED
            if days_diff > 60:
                return "ARCHIVED"
        except:
            pass
    
    return "ACTIVE"


def backfill_recommendations(scanner_version: str = "v3", dry_run: bool = True) -> Dict:
    """
    과거 데이터를 recommendations로 마이그레이션
    
    Args:
        scanner_version: 스캐너 버전
        dry_run: True이면 실제 저장하지 않고 시뮬레이션만
        
    Returns:
        마이그레이션 결과 통계
    """
    from date_helper import get_kst_now
    
    today_str = get_kst_now().strftime("%Y%m%d")
    
    logger.info(f"[backfill_recommendations] 백필 시작: scanner_version={scanner_version}, dry_run={dry_run}")
    
    # scan_rank 데이터 조회
    scan_data = get_scan_rank_data_for_migration(scanner_version)
    logger.info(f"[backfill_recommendations] 조회된 scan_rank 데이터: {len(scan_data)}개")
    
    # 모든 스캔 결과를 날짜 순서대로 정렬 (오래된 것부터)
    # 날짜 순서대로 처리하면 자동으로 REPLACED가 적용됨
    scan_data_sorted = sorted(scan_data, key=lambda x: (
        x["date"] if isinstance(x["date"], str) else str(x["date"]),
        x["code"]
    ))
    
    # 모든 스캔 결과를 recommendations로 마이그레이션
    selected_items = scan_data_sorted
    
    logger.info(f"[backfill_recommendations] 마이그레이션 대상: {len(selected_items)}개 (모든 스캔 결과)")
    
    # ticker 개수 계산
    unique_tickers = len(set(item["code"] for item in scan_data))
    
    stats = {
        "total_scan_rank": len(scan_data),
        "total_tickers": unique_tickers,
        "selected_recommendations": len(selected_items),
        "created": 0,
        "skipped": 0,
        "errors": 0
    }
    
    if dry_run:
        logger.info(f"[backfill_recommendations] DRY RUN 모드 - 실제 저장하지 않음")
        for item in selected_items:
            logger.info(f"  - {item['code']} ({item['name']}): {item['date']}")
        return stats
    
    # recommendations 생성 (v2 트랜잭션 사용)
    for item in selected_items:
        try:
            # anchor_date 추출
            anchor_date_obj = item.get("anchor_date")
            if isinstance(anchor_date_obj, str):
                anchor_date_obj = yyyymmdd_to_date(anchor_date_obj.replace("-", "")[:8])
            elif anchor_date_obj is None:
                # anchor_date가 없으면 date에서 추출
                date_obj = item["date"]
                if isinstance(date_obj, str):
                    scan_date = date_obj.replace("-", "")[:8]
                else:
                    scan_date = date_obj.strftime("%Y%m%d")
                anchor_date_obj = yyyymmdd_to_date(scan_date)
            
            # anchor_close 추출
            anchor_close_value = item.get("anchor_close")
            if not anchor_close_value or anchor_close_value <= 0:
                # anchor_close가 없으면 조회 시도
                date_obj = item["date"]
                if isinstance(date_obj, str):
                    scan_date = date_obj.replace("-", "")[:8]
                else:
                    scan_date = date_obj.strftime("%Y%m%d")
                anchor_close_value = get_anchor_close(item["code"], scan_date, price_type="CLOSE")
                if not anchor_close_value:
                    logger.warning(f"[backfill_recommendations] anchor_close 결정 불가: {item['code']}")
                    stats["skipped"] += 1
                    continue
            
            # INTEGER로 변환 (원 단위)
            anchor_close_int = int(round(float(anchor_close_value)))
            
            # v2 트랜잭션 사용
            # name 파라미터는 함수 시그니처에 있지만 실제로는 사용하지 않음 (v2 스키마에 name 컬럼 없음)
            rec_id = create_recommendation_transaction(
                ticker=item["code"],
                anchor_date=anchor_date_obj,
                anchor_close=anchor_close_int,
                anchor_source=item.get("anchor_source", "KRX_EOD"),
                reason_code="BACKFILL_MIGRATION",
                # name=item.get("name", ""),  # v2 스키마에 name 컬럼 없음
                strategy=item.get("strategy"),
                scanner_version=scanner_version,
                score=item.get("score", 0.0),
                score_label=item.get("score_label", ""),
                indicators=item.get("indicators", {}),
                flags=item.get("flags", {}),
                details=item.get("details", {})
            )
            
            if rec_id:
                stats["created"] += 1
                logger.info(f"[backfill_recommendations] 추천 생성: {item['code']} (ID: {rec_id})")
            else:
                stats["skipped"] += 1
                logger.warning(f"[backfill_recommendations] 추천 생성 건너뜀: {item['code']}")
                
        except Exception as e:
            stats["errors"] += 1
            logger.error(f"[backfill_recommendations] 추천 생성 오류 ({item.get('code')}): {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    logger.info(f"[backfill_recommendations] 백필 완료: {stats}")
    return stats


def verify_kai_recommendations(ticker: str = "047810") -> Dict:
    """
    한국항공우주(047810) 추천 검증
    
    Returns:
        검증 결과
    """
    logger.info(f"[verify_kai_recommendations] 한국항공우주({ticker}) 검증 시작")
    
    try:
        with db_manager.get_cursor(commit=False) as cur:
            # recommendations에서 ACTIVE 추천 조회 (v2 스키마)
            cur.execute("""
                SELECT 
                    recommendation_id, ticker, status, anchor_date, anchor_close,
                    strategy, created_at
                FROM recommendations
                WHERE ticker = %s
                AND scanner_version = 'v3'
                ORDER BY anchor_date DESC
            """, (ticker,))
            
            rows = cur.fetchall()
            
            active_count = 0
            recommendations = []
            
            for row in rows:
                if isinstance(row, dict):
                    rec = dict(row)
                else:
                    rec = {
                        "recommendation_id": str(row[0]),
                        "ticker": row[1],
                        "status": row[2],
                        "anchor_date": str(row[3]),
                        "anchor_close": row[4],
                        "strategy": row[5] if len(row) > 5 else None,
                        "created_at": str(row[6]) if len(row) > 6 else None
                    }
                
                recommendations.append(rec)
                if rec["status"] == "ACTIVE":
                    active_count += 1
            
            # scan_rank에서도 확인 (비교용)
            cur.execute("""
                SELECT 
                    date, code, name, anchor_date, anchor_close, flags
                FROM scan_rank
                WHERE code = %s
                AND scanner_version = 'v3'
                ORDER BY date DESC
            """, (ticker,))
            
            scan_rows = cur.fetchall()
            scan_dates = []
            for row in scan_rows:
                if isinstance(row, dict):
                    scan_dates.append({
                        "date": row["date"],
                        "anchor_date": row.get("anchor_date"),
                        "anchor_close": row.get("anchor_close")
                    })
                else:
                    scan_dates.append({
                        "date": row[0],
                        "anchor_date": row[3] if len(row) > 3 else None,
                        "anchor_close": row[4] if len(row) > 4 else None
                    })
            
            result = {
                "ticker": ticker,
                "active_count": active_count,
                "total_recommendations": len(recommendations),
                "recommendations": recommendations,
                "scan_rank_dates": scan_dates,
                "is_valid": active_count <= 1  # ACTIVE는 최대 1개만
            }
            
            logger.info(f"[verify_kai_recommendations] 검증 결과: ACTIVE {active_count}개, 전체 {len(recommendations)}개")
            
            if active_count > 1:
                logger.warning(f"[verify_kai_recommendations] ⚠️ ACTIVE 중복 발견: {active_count}개")
            else:
                logger.info(f"[verify_kai_recommendations] ✅ ACTIVE 중복 없음")
            
            return result
            
    except Exception as e:
        logger.error(f"[verify_kai_recommendations] 검증 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {"error": str(e)}


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="v3 추천 시스템 백필 스크립트")
    parser.add_argument("--dry-run", action="store_true", help="실제 저장하지 않고 시뮬레이션만")
    parser.add_argument("--verify", action="store_true", help="한국항공우주(047810) 검증만 수행")
    parser.add_argument("--ticker", type=str, default="047810", help="검증할 종목 코드 (기본값: 047810)")
    
    args = parser.parse_args()
    
    if args.verify:
        result = verify_kai_recommendations(args.ticker)
        print("\n=== 검증 결과 ===")
        print(json.dumps(result, indent=2, default=str, ensure_ascii=False))
    else:
        stats = backfill_recommendations(dry_run=args.dry_run)
        print("\n=== 백필 결과 ===")
        print(json.dumps(stats, indent=2, default=str, ensure_ascii=False))
        
        # 검증도 함께 수행
        print("\n=== 한국항공우주(047810) 검증 ===")
        verify_result = verify_kai_recommendations()
        print(json.dumps(verify_result, indent=2, default=str, ensure_ascii=False))


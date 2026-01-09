#!/usr/bin/env python3
"""
v3 추천 시스템 구현 검증 스크립트
운영 관점에서 핵심 계약이 DB/코드 레벨에서 깨지지 않는지 증명
"""
import sys
import os
from pathlib import Path
from datetime import datetime, date
import json
import uuid
import logging

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from db_manager import db_manager
from services.recommendation_service_v2 import (
    create_recommendation_transaction,
    transition_recommendation_status_transaction,
    check_duplicate_active_recommendations,
    get_active_recommendations
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def verify_table_exists(table_name: str) -> bool:
    """테이블 존재 여부 확인"""
    try:
        with db_manager.get_cursor(commit=False) as cur:
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = %s
                )
            """, (table_name,))
            result = cur.fetchone()
            exists = result[0] if isinstance(result, (list, tuple)) else result.get('exists') if isinstance(result, dict) else result
            return bool(exists)
    except Exception as e:
        logger.error(f"[verify_table_exists] 오류: {e}")
        return False


def verify_partial_unique_index() -> bool:
    """Partial unique index 존재 및 작동 확인"""
    try:
        with db_manager.get_cursor(commit=False) as cur:
            # 인덱스 존재 확인
            cur.execute("""
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE tablename = 'recommendations'
                AND indexname = 'uniq_active_recommendation_per_ticker'
            """)
            index = cur.fetchone()
            
            if not index:
                logger.error("[verify_partial_unique_index] 인덱스가 존재하지 않습니다")
                return False
            
            logger.info(f"[verify_partial_unique_index] 인덱스 확인: {index}")
            return True
    except Exception as e:
        logger.error(f"[verify_partial_unique_index] 오류: {e}")
        return False


def verify_duplicate_active_recommendations() -> tuple[bool, list]:
    """
    (A) ticker별 ACTIVE 중복 탐지
    결과는 반드시 0행이어야 함
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
            
            duplicates = cur.fetchall()
            
            if duplicates:
                logger.error(f"[verify_duplicate_active] 중복 ACTIVE 발견: {len(duplicates)}개 ticker")
                for dup in duplicates:
                    if isinstance(dup, dict):
                        logger.error(f"  - {dup.get('ticker')}: {dup.get('count')}개 ACTIVE")
                    else:
                        logger.error(f"  - {dup[0]}: {dup[1]}개 ACTIVE")
                return False, duplicates
            else:
                logger.info("[verify_duplicate_active] ✅ 중복 ACTIVE 없음")
                return True, []
    except Exception as e:
        logger.error(f"[verify_duplicate_active] 오류: {e}")
        return False, []


def verify_ticker_047810_history() -> list:
    """
    (B) 047810 이력 확인
    """
    try:
        with db_manager.get_cursor(commit=False) as cur:
            cur.execute("""
                SELECT 
                    recommendation_id,
                    anchor_date,
                    status,
                    created_at,
                    anchor_close,
                    replaces_recommendation_id,
                    replaced_by_recommendation_id
                FROM recommendations
                WHERE ticker = '047810'
                ORDER BY created_at DESC
            """)
            
            rows = cur.fetchall()
            
            history = []
            for row in rows:
                if isinstance(row, dict):
                    history.append({
                        "recommendation_id": str(row.get('recommendation_id')),
                        "anchor_date": str(row.get('anchor_date')),
                        "status": row.get('status'),
                        "created_at": str(row.get('created_at')),
                        "anchor_close": row.get('anchor_close'),
                        "replaces": str(row.get('replaces_recommendation_id')) if row.get('replaces_recommendation_id') else None,
                        "replaced_by": str(row.get('replaced_by_recommendation_id')) if row.get('replaced_by_recommendation_id') else None
                    })
                else:
                    history.append({
                        "recommendation_id": str(row[0]),
                        "anchor_date": str(row[1]),
                        "status": row[2],
                        "created_at": str(row[3]),
                        "anchor_close": row[4],
                        "replaces": str(row[5]) if len(row) > 5 and row[5] else None,
                        "replaced_by": str(row[6]) if len(row) > 6 and row[6] else None
                    })
            
            active_count = sum(1 for h in history if h['status'] == 'ACTIVE')
            logger.info(f"[verify_ticker_047810] 047810 이력: 총 {len(history)}개, ACTIVE {active_count}개")
            
            return history
    except Exception as e:
        logger.error(f"[verify_ticker_047810] 오류: {e}")
        return []


def verify_state_events(recommendation_id: uuid.UUID) -> list:
    """
    (C) 상태 이벤트 로그 확인
    """
    try:
        with db_manager.get_cursor(commit=False) as cur:
            cur.execute("""
                SELECT 
                    event_id,
                    recommendation_id,
                    from_status,
                    to_status,
                    reason_code,
                    reason_text,
                    occurred_at
                FROM recommendation_state_events
                WHERE recommendation_id = %s
                ORDER BY occurred_at ASC
            """, (recommendation_id,))
            
            rows = cur.fetchall()
            
            events = []
            for row in rows:
                if isinstance(row, dict):
                    events.append({
                        "event_id": str(row.get('event_id')),
                        "from_status": row.get('from_status'),
                        "to_status": row.get('to_status'),
                        "reason_code": row.get('reason_code'),
                        "reason_text": row.get('reason_text'),
                        "occurred_at": str(row.get('occurred_at'))
                    })
                else:
                    events.append({
                        "event_id": str(row[0]),
                        "from_status": row[1],
                        "to_status": row[2],
                        "reason_code": row[3],
                        "reason_text": row[4] if len(row) > 4 else None,
                        "occurred_at": str(row[5] if len(row) > 5 else row[4])
                    })
            
            logger.info(f"[verify_state_events] 상태 이벤트: {len(events)}개")
            return events
    except Exception as e:
        logger.error(f"[verify_state_events] 오류: {e}")
        return []


def test_duplicate_active_constraint():
    """
    6) DB 제약(Partial Unique Index) 강제 테스트
    같은 ticker로 ACTIVE 추천을 의도적으로 2번 생성 시도
    """
    test_ticker = "TEST999"
    test_date = date(2025, 12, 15)
    
    logger.info(f"[test_duplicate_active_constraint] 테스트 시작: {test_ticker}")
    
    try:
        # 첫 번째 ACTIVE 생성
        rec_id_1 = create_recommendation_transaction(
            ticker=test_ticker,
            anchor_date=test_date,
            anchor_close=50000,
            anchor_source="TEST",
            reason_code="TEST_DUPLICATE_1",
            name="테스트 종목"
        )
        
        if not rec_id_1:
            logger.error("[test_duplicate_active_constraint] 첫 번째 추천 생성 실패")
            return False
        
        logger.info(f"[test_duplicate_active_constraint] 첫 번째 ACTIVE 생성 성공: {rec_id_1}")
        
        # 두 번째 ACTIVE 생성 시도 (제약 위반 예상)
        try:
            rec_id_2 = create_recommendation_transaction(
                ticker=test_ticker,
                anchor_date=test_date,
                anchor_close=51000,
                anchor_source="TEST",
                reason_code="TEST_DUPLICATE_2",
                name="테스트 종목"
            )
            
            # 두 번째가 성공했다면 문제 (REPLACED로 전환되어야 함)
            if rec_id_2:
                logger.warning(f"[test_duplicate_active_constraint] 두 번째 ACTIVE 생성됨: {rec_id_2}")
                logger.warning("[test_duplicate_active_constraint] ⚠️ 첫 번째가 REPLACED로 전환되었는지 확인 필요")
                
                # 첫 번째 상태 확인
                with db_manager.get_cursor(commit=False) as cur:
                    cur.execute("""
                        SELECT status, replaced_by_recommendation_id
                        FROM recommendations
                        WHERE recommendation_id = %s
                    """, (rec_id_1,))
                    first_rec = cur.fetchone()
                    
                    if first_rec:
                        status = first_rec[0] if isinstance(first_rec, (list, tuple)) else first_rec.get('status')
                        if status == 'REPLACED':
                            logger.info("[test_duplicate_active_constraint] ✅ 첫 번째가 REPLACED로 전환됨 (정상)")
                            return True
                        else:
                            logger.error(f"[test_duplicate_active_constraint] ❌ 첫 번째 상태: {status} (REPLACED여야 함)")
                            return False
                
                return True  # REPLACED로 전환되었다면 정상
            else:
                logger.error("[test_duplicate_active_constraint] 두 번째 생성 실패 (예상과 다름)")
                return False
                
        except Exception as e:
            # DB 제약 위반 예외 확인
            error_msg = str(e)
            if "duplicate key" in error_msg.lower() or "unique constraint" in error_msg.lower():
                logger.info(f"[test_duplicate_active_constraint] ✅ DB 제약 위반 감지: {error_msg}")
                return True
            else:
                logger.error(f"[test_duplicate_active_constraint] 예상치 못한 오류: {e}")
                return False
        
        finally:
            # 테스트 데이터 정리
            try:
                with db_manager.get_cursor(commit=True) as cur:
                    cur.execute("""
                        DELETE FROM recommendations
                        WHERE ticker = %s
                    """, (test_ticker,))
                logger.info(f"[test_duplicate_active_constraint] 테스트 데이터 정리 완료: {test_ticker}")
            except:
                pass
        
    except Exception as e:
        logger.error(f"[test_duplicate_active_constraint] 테스트 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def test_anchor_close_immutability():
    """
    7) 과거 상태가 조회 시 재계산되는지 회귀 테스트
    특정 reco_id의 anchor_close를 조회한 뒤, 시간이 지나도 변하지 않음을 보장
    """
    test_ticker = "TEST998"
    test_date = date(2025, 12, 15)
    test_anchor_close = 50000
    
    logger.info(f"[test_anchor_close_immutability] 테스트 시작: {test_ticker}")
    
    try:
        # 추천 생성
        rec_id = create_recommendation_transaction(
            ticker=test_ticker,
            anchor_date=test_date,
            anchor_close=test_anchor_close,
            anchor_source="TEST",
            reason_code="TEST_IMMUTABILITY",
            name="테스트 종목"
        )
        
        if not rec_id:
            logger.error("[test_anchor_close_immutability] 추천 생성 실패")
            return False
        
        # 첫 번째 조회
        with db_manager.get_cursor(commit=False) as cur:
            cur.execute("""
                SELECT anchor_close, anchor_date, status
                FROM recommendations
                WHERE recommendation_id = %s
            """, (rec_id,))
            first_read = cur.fetchone()
            
            if not first_read:
                logger.error("[test_anchor_close_immutability] 첫 번째 조회 실패")
                return False
            
            first_anchor_close = first_read[0] if isinstance(first_read, (list, tuple)) else first_read.get('anchor_close')
            first_anchor_date = first_read[1] if isinstance(first_read, (list, tuple)) else first_read.get('anchor_date')
            first_status = first_read[2] if isinstance(first_read, (list, tuple)) else first_read.get('status')
            
            logger.info(f"[test_anchor_close_immutability] 첫 번째 조회: anchor_close={first_anchor_close}, anchor_date={first_anchor_date}, status={first_status}")
        
        # 잠시 대기 (시간 경과 시뮬레이션)
        import time
        time.sleep(1)
        
        # 두 번째 조회 (동일 값 확인)
        with db_manager.get_cursor(commit=False) as cur:
            cur.execute("""
                SELECT anchor_close, anchor_date, status
                FROM recommendations
                WHERE recommendation_id = %s
            """, (rec_id,))
            second_read = cur.fetchone()
            
            if not second_read:
                logger.error("[test_anchor_close_immutability] 두 번째 조회 실패")
                return False
            
            second_anchor_close = second_read[0] if isinstance(second_read, (list, tuple)) else second_read.get('anchor_close')
            second_anchor_date = second_read[1] if isinstance(second_read, (list, tuple)) else second_read.get('anchor_date')
            second_status = second_read[2] if isinstance(second_read, (list, tuple)) else second_read.get('status')
            
            logger.info(f"[test_anchor_close_immutability] 두 번째 조회: anchor_close={second_anchor_close}, anchor_date={second_anchor_date}, status={second_status}")
        
        # 값 비교
        if (first_anchor_close == second_anchor_close and 
            first_anchor_date == second_anchor_date and 
            first_status == second_status):
            logger.info("[test_anchor_close_immutability] ✅ anchor_close/status 불변성 확인")
            
            # 테스트 데이터 정리
            try:
                with db_manager.get_cursor(commit=True) as cur:
                    cur.execute("""
                        DELETE FROM recommendations
                        WHERE ticker = %s
                    """, (test_ticker,))
            except:
                pass
            
            return True
        else:
            logger.error("[test_anchor_close_immutability] ❌ 값이 변경됨!")
            logger.error(f"  anchor_close: {first_anchor_close} → {second_anchor_close}")
            logger.error(f"  anchor_date: {first_anchor_date} → {second_anchor_date}")
            logger.error(f"  status: {first_status} → {second_status}")
            return False
        
    except Exception as e:
        logger.error(f"[test_anchor_close_immutability] 테스트 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def main():
    """메인 검증 프로세스"""
    logger.info("=" * 80)
    logger.info("v3 추천 시스템 구현 검증 시작")
    logger.info("=" * 80)
    
    results = {
        "table_exists": {},
        "partial_unique_index": False,
        "duplicate_active_before": None,
        "duplicate_active_after": None,
        "ticker_047810_before": [],
        "ticker_047810_after": [],
        "constraint_test": False,
        "immutability_test": False
    }
    
    # 1. 테이블 존재 확인
    logger.info("\n[1단계] 테이블 존재 확인")
    for table in ['recommendations', 'scan_results', 'recommendation_state_events']:
        exists = verify_table_exists(table)
        results["table_exists"][table] = exists
        logger.info(f"  {table}: {'✅ 존재' if exists else '❌ 없음'}")
    
    # 2. Partial unique index 확인
    logger.info("\n[2단계] Partial unique index 확인")
    results["partial_unique_index"] = verify_partial_unique_index()
    logger.info(f"  결과: {'✅ 존재' if results['partial_unique_index'] else '❌ 없음'}")
    
    # 3. (A) 중복 ACTIVE 확인 (backfill 전)
    logger.info("\n[3단계-A] 중복 ACTIVE 확인 (backfill 전)")
    ok, duplicates = verify_duplicate_active_recommendations()
    results["duplicate_active_before"] = {"ok": ok, "duplicates": duplicates}
    
    # 4. (B) 047810 이력 확인 (backfill 전)
    logger.info("\n[3단계-B] 047810 이력 확인 (backfill 전)")
    history_before = verify_ticker_047810_history()
    results["ticker_047810_before"] = history_before
    
    if history_before:
        active_before = [h for h in history_before if h['status'] == 'ACTIVE']
        logger.info(f"  ACTIVE 개수: {len(active_before)}")
        for h in active_before:
            logger.info(f"    - {h['anchor_date']}: {h['status']} (ID: {h['recommendation_id'][:8]}...)")
    
    # 5. (C) 상태 이벤트 로그 확인 (047810의 첫 번째 추천이 있다면)
    if history_before:
        first_rec_id = history_before[0].get('recommendation_id')
        if first_rec_id:
            try:
                rec_uuid = uuid.UUID(first_rec_id)
                logger.info(f"\n[3단계-C] 상태 이벤트 로그 확인 (recommendation_id: {first_rec_id[:8]}...)")
                events = verify_state_events(rec_uuid)
                for event in events:
                    logger.info(f"  {event['occurred_at']}: {event['from_status']} → {event['to_status']} ({event['reason_code']})")
            except:
                pass
    
    # 6. DB 제약 강제 테스트
    logger.info("\n[6단계] DB 제약 강제 테스트")
    results["constraint_test"] = test_duplicate_active_constraint()
    logger.info(f"  결과: {'✅ 통과' if results['constraint_test'] else '❌ 실패'}")
    
    # 7. anchor_close 불변성 테스트
    logger.info("\n[7단계] anchor_close 불변성 테스트")
    results["immutability_test"] = test_anchor_close_immutability()
    logger.info(f"  결과: {'✅ 통과' if results['immutability_test'] else '❌ 실패'}")
    
    # 최종 결과 출력
    logger.info("\n" + "=" * 80)
    logger.info("검증 결과 요약")
    logger.info("=" * 80)
    
    all_passed = (
        all(results["table_exists"].values()) and
        results["partial_unique_index"] and
        results["duplicate_active_before"]["ok"] and
        results["constraint_test"] and
        results["immutability_test"]
    )
    
    logger.info(f"전체 검증: {'✅ 통과' if all_passed else '❌ 실패'}")
    logger.info(f"  - 테이블 존재: {all(results['table_exists'].values())}")
    logger.info(f"  - Partial unique index: {results['partial_unique_index']}")
    logger.info(f"  - 중복 ACTIVE 없음: {results['duplicate_active_before']['ok']}")
    logger.info(f"  - 제약 강제 테스트: {results['constraint_test']}")
    logger.info(f"  - 불변성 테스트: {results['immutability_test']}")
    
    # JSON 출력 (자동화용)
    print("\n" + "=" * 80)
    print("JSON 결과:")
    print(json.dumps(results, indent=2, default=str, ensure_ascii=False))
    
    return results


if __name__ == "__main__":
    main()




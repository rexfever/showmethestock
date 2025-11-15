"""
스캔 관련 서비스
"""
import json
import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime
from scanner import scan_with_preset
from config import config
from kiwoom_api import api
from db_manager import db_manager


def _ensure_scan_rank_table(cursor) -> None:
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scan_rank(
            date TEXT NOT NULL,
            code TEXT NOT NULL,
            name TEXT,
            score DOUBLE PRECISION,
            flags TEXT,
            score_label TEXT,
            close_price DOUBLE PRECISION,
            volume DOUBLE PRECISION,
            change_rate DOUBLE PRECISION,
            PRIMARY KEY (date, code)
        )
    """)


def get_recurrence_data(tickers: List[str], today_as_of: str) -> Dict[str, Dict]:
    """재등장 이력 조회 (배치 처리)"""
    recurrence_data = {}
    
    if not tickers:
        return recurrence_data
    
    try:
        with db_manager.get_cursor(commit=False) as cur_hist:
            _ensure_scan_rank_table(cur_hist)
            cur_hist.execute("""
                SELECT code, date
                FROM scan_rank
                WHERE code = ANY(%s)
                ORDER BY code, date DESC
            """, (tickers,))
            rows = cur_hist.fetchall()
        
        # 결과를 종목별로 그룹화
        for ticker in tickers:
            prev_dates = [str(row["date"]) for row in rows if row["code"] == ticker and str(row["date"]) < today_as_of]
            if prev_dates:
                last_as_of = prev_dates[0]
                first_as_of = prev_dates[-1]
                try:
                    days_since_last = int((pd.to_datetime(today_as_of) - pd.to_datetime(last_as_of)).days)
                except Exception:
                    days_since_last = None
                recurrence_data[ticker] = {
                    'appeared_before': True,
                    'appear_count': len(prev_dates),
                    'last_as_of': last_as_of,
                    'first_as_of': first_as_of,
                    'days_since_last': days_since_last,
                }
            else:
                recurrence_data[ticker] = {
                    'appeared_before': False,
                    'appear_count': 0,
                    'last_as_of': None,
                    'first_as_of': today_as_of,
                    'days_since_last': None,
                }
    except Exception as e:
        print(f"재등장 이력 조회 오류: {e}")
        # 오류 시 기본값 설정
        for ticker in tickers:
            recurrence_data[ticker] = {
                'appeared_before': False,
                'appear_count': 0,
                'last_as_of': None,
                'first_as_of': today_as_of,
                'days_since_last': None,
            }
    
    return recurrence_data


# save_scan_snapshot 함수 제거됨 - main.py::_save_snapshot_db() 사용


def execute_scan_with_fallback(universe: List[str], date: Optional[str] = None, market_condition=None) -> tuple:
    """Fallback 로직을 적용한 스캔 실행 (시장별 프리셋 + 하이브리드 접근)"""
    chosen_step = None
    
    # 급락장 감지 시 추천하지 않음
    if market_condition and market_condition.market_sentiment == 'crash':
        print(f"🔴 급락장 감지 (KOSPI: {market_condition.kospi_return:.2f}%) - 추천 종목 없음 반환")
        return [], None
    
    use_fallback = config.fallback_enable
    sentiment = getattr(market_condition, "market_sentiment", "neutral") if market_condition else "neutral"
    fallback_profile = config.get_fallback_profile(sentiment)
    target_min = max(1, fallback_profile.get("target_min", config.fallback_target_min))
    target_max = max(target_min, fallback_profile.get("target_max", config.fallback_target_max))
    selected_presets = fallback_profile.get("presets") or [{}]
    if not selected_presets:
        selected_presets = [{}]
    
    if market_condition:
        print(f"🧭 장세: {sentiment} (KOSPI: {market_condition.kospi_return:.2f}%), 목표: {target_min}~{target_max}개, 프리셋 수: {len(selected_presets)}")
    else:
        print(f"🧭 장세 정보 없음 - 기본(중립) 프리셋 사용, 목표: {target_min}~{target_max}개")
    
    print(f"🔄 하이브리드 Fallback 로직 시작: universe={len(universe)}개, fallback_enable={use_fallback}")
    
    if not use_fallback:
        # Fallback 비활성화 시 기존 로직 (10점 이상만)
        print(f"📊 Fallback 비활성화 - 시장 상황 기반 조건으로 스캔 (10점 이상만)")
        try:
            items = scan_with_preset(universe, {}, date, market_condition)
        except Exception as e:
            print(f"❌ 스캔 오류: {e}")
            return [], None
        # 10점 이상만 필터링
        items_10_plus = [item for item in items if item.get("score", 0) >= 10]
        items = items_10_plus[:config.top_k]
        chosen_step = 0  # 기본 조건 사용
        print(f"📊 스캔 결과: {len(items)}개 종목 (10점 이상만, 조건 강화)")
    else:
        # 통합 Fallback: 점수와 지표를 동시에 Fallback (장세별 프리셋)
        print(f"📊 통합 Fallback 활성화 - 목표: 최소 {target_min}개, 최대 {target_max}개")
        
        final_items = []
        chosen_step = None  # 명확한 초기값
        
        # Step 0: 기본/장세별 첫 프리셋
        step0_overrides = selected_presets[0] if selected_presets else {}
        print(f"🔄 Step 0: 기본 조건 적용 ({'타이트' if not step0_overrides else step0_overrides})")
        try:
            step0_items = scan_with_preset(universe, step0_overrides, date, market_condition)
        except Exception as e:
            print(f"❌ Step 0 스캔 오류: {e}")
            return [], None
        step0_items_10_plus = [item for item in step0_items if item.get("score", 0) >= 10]
        print(f"📊 Step 0 결과: {len(step0_items_10_plus)}개 종목 (10점 이상)")
        
        if len(step0_items_10_plus) >= target_min:
            chosen_step = 0
            final_items = step0_items_10_plus[:min(config.top_k, target_max)]
            print(f"✅ Step 0에서 목표 달성: {len(final_items)}개 종목 선택 (10점 이상)")
        else:
            current_items_for_score_fallback = step0_items
            
            # Step 1: 장세별 두 번째 프리셋 + 10점 이상
            step1_items = None
            if len(selected_presets) > 1:
                print(f"🔄 Step 1: 장세별 지표 완화 + 10점 이상")
                try:
                    step1_overrides = selected_presets[1]
                    step1_items = scan_with_preset(universe, step1_overrides, date, market_condition)
                except Exception as e:
                    print(f"❌ Step 1 스캔 오류: {e}")
                    return [], None
                step1_items_10_plus = [item for item in step1_items if item.get("score", 0) >= 10]
                print(f"📊 Step 1 결과: {len(step1_items_10_plus)}개 종목 (지표 완화 + 10점 이상)")
                
                if len(step1_items_10_plus) >= target_min:
                    chosen_step = 1
                    final_items = step1_items_10_plus[:min(config.top_k, target_max)]
                    print(f"✅ Step 1에서 목표 달성: {len(final_items)}개 종목 선택 (지표 완화 + 10점 이상)")
                else:
                    current_items_for_score_fallback = step1_items
            else:
                print(f"ℹ️ Step 1 프리셋 없음 - Step 0 결과로 점수 Fallback 진행")
            
            # Step 2: 현재 데이터 기반 8점 이상 Fallback
            if not final_items:
                print(f"🔄 Step 2: 점수 Fallback (8점 이상) 적용")
                step2_source = step1_items if step1_items is not None else current_items_for_score_fallback
                step2_candidates = [item for item in (step2_source or []) if item.get("score", 0) >= 8]
                print(f"📊 Step 2 결과: {len(step2_candidates)}개 종목 (8점 이상)")
                
                if len(step2_candidates) >= target_min:
                    chosen_step = 2
                    final_items = step2_candidates[:min(config.top_k, target_max)]
                    print(f"✅ Step 2에서 목표 달성: {len(final_items)}개 종목 선택 (8점 이상)")
            
            # Step 3: 장세별 추가 프리셋 (8점 이상, 최대 한 단계)
            if not final_items and len(selected_presets) > 2:
                print(f"⚠️ Step 2 목표 미달 - 장세별 Step 3 프리셋 적용")
                step3_overrides = selected_presets[2]
                print(f"🔄 Step 3: 추가 프리셋 적용 -> {step3_overrides}")
                try:
                    step3_items = scan_with_preset(universe, step3_overrides, date, market_condition)
                except Exception as e:
                    print(f"❌ Step 3 스캔 오류: {e}")
                    step3_items = []
                
                step3_items_8_plus = [item for item in step3_items if item.get("score", 0) >= 8]
                print(f"📊 Step 3 결과: {len(step3_items_8_plus)}개 종목 (8점 이상)")
                
                if len(step3_items_8_plus) >= target_min:
                    chosen_step = 3
                    final_items = step3_items_8_plus[:min(config.top_k, target_max)]
                    print(f"✅ Step 3에서 목표 달성: {len(final_items)}개 종목 선택")
                else:
                    print(f"❌ Step 3 목표 미달: {len(step3_items_8_plus)} < {target_min}")
            
            if not final_items:
                print(f"⚠️ 모든 프리셋 적용 후에도 목표 미달 - 추천 종목 없음")
                print(f"🔍 디버깅: universe={len(universe)}개, market_condition={market_condition}")
                final_items = []
                chosen_step = None
        
        items = final_items
    
    print(f"🎯 최종 선택: Step {chosen_step}, {len(items)}개 종목")
    return items, chosen_step

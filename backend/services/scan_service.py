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


def save_scan_snapshot(scan_items: List[Dict], today_as_of: str) -> None:
    """스캔 스냅샷 저장"""
    try:
        with db_manager.get_cursor(commit=True) as cur_hist:
            _ensure_scan_rank_table(cur_hist)
        
            enhanced_rank = []
            for it in scan_items:
                try:
                    df = api.get_ohlcv(it["ticker"], 2)
                    if not df.empty:
                        latest = df.iloc[-1]
                        prev = df.iloc[-2] if len(df) > 1 else None
                        change_rate = (latest.close - prev.close) / prev.close if prev is not None and prev.close else 0.0
                        enhanced_rank.append({
                            "date": today_as_of,
                            "code": it["ticker"],
                            "name": it["name"],
                            "score": it["score"],
                            "flags": json.dumps(it["flags"], ensure_ascii=False),
                            "score_label": it["score_label"],
                            "close_price": float(latest.close),
                            "volume": float(latest.volume),
                            "change_rate": float(change_rate),
                        })
                except Exception:
                    continue
        
            cur_hist.execute("DELETE FROM scan_rank WHERE date = %s", (today_as_of,))
            
            if not scan_items:
                print(f"📭 스캔 결과 0개 - NORESULT 레코드 저장: {today_as_of}")
                cur_hist.execute(
                    """
                    INSERT INTO scan_rank (date, code, name, score, flags, score_label, close_price, volume, change_rate)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (today_as_of, "NORESULT", "추천종목 없음", 0.0, json.dumps({"no_result": True}, ensure_ascii=False),
                     "추천종목 없음", 0.0, 0.0, 0.0)
                )
            elif enhanced_rank:
                cur_hist.executemany("""
                    INSERT INTO scan_rank (date, code, name, score, flags, score_label, close_price, volume, change_rate)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, [
                    (
                        r["date"], r["code"], r["name"], r["score"], r["flags"],
                        r["score_label"], r["close_price"], r["volume"], r["change_rate"]
                    )
                    for r in enhanced_rank
                ])
            else:
                print(f"📭 enhanced_rank 비어있음 - NORESULT 레코드 저장: {today_as_of}")
                cur_hist.execute(
                    """
                    INSERT INTO scan_rank (date, code, name, score, flags, score_label, close_price, volume, change_rate)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (today_as_of, "NORESULT", "추천종목 없음", 0.0, json.dumps({"no_result": True}, ensure_ascii=False),
                     "추천종목 없음", 0.0, 0.0, 0.0)
                )
    except Exception as e:
        print(f"스냅샷 저장 오류: {e}")


def execute_scan_with_fallback(universe: List[str], date: Optional[str] = None, market_condition=None) -> tuple:
    """Fallback 로직을 적용한 스캔 실행 (하이브리드 접근: 10점 이상 우선, 없으면 8점 이상 Fallback)"""
    chosen_step = None
    
    # 급락장 감지 시 추천하지 않음
    if market_condition and market_condition.market_sentiment == 'crash':
        print(f"🔴 급락장 감지 (KOSPI: {market_condition.kospi_return:.2f}%) - 추천 종목 없음 반환")
        return [], None
    
    # 약세장에서도 fallback 활성화하되, 장세별 목표 개수 적용
    use_fallback = config.fallback_enable
    
    # 장세별 MIN/MAX 설정 및 검증
    if market_condition and market_condition.market_sentiment == 'bear':
        target_min = max(1, config.fallback_target_min_bear)  # 최소 1개
        target_max = max(target_min, config.fallback_target_max_bear)  # 최소 target_min 이상
        print(f"⚠️ 약세장 감지 (KOSPI: {market_condition.kospi_return:.2f}%) - Fallback 활성화, 목표: {target_min}~{target_max}개")
    else:
        target_min = max(1, config.fallback_target_min_bull)  # 최소 1개
        target_max = max(target_min, config.fallback_target_max_bull)  # 최소 target_min 이상
        if market_condition:
            print(f"📈 {market_condition.market_sentiment} 장세 (KOSPI: {market_condition.kospi_return:.2f}%) - Fallback 활성화, 목표: {target_min}~{target_max}개")
    
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
        # 통합 Fallback: 점수와 지표를 동시에 Fallback
        print(f"📊 통합 Fallback 활성화 - 목표: 최소 {target_min}개, 최대 {target_max}개")
        
        final_items = []
        chosen_step = None  # 명확한 초기값
        
        # Step 0: 기본 조건 (10점 이상만, 지표 완화 없음)
        print(f"🔄 Step 0: 기본 조건 (10점 이상만)")
        try:
            step0_items = scan_with_preset(universe, {}, date, market_condition)
        except Exception as e:
            print(f"❌ Step 0 스캔 오류: {e}")
            return [], None
        # 신호 충족 = 후보군 (점수 무관), 점수는 순위 매기기용
        # 신호 미충족 = 점수 기준 적용 (10점 이상)
        step0_items_filtered = []
        for item in step0_items:
            flags = item.get("flags", {})
            signals_count = flags.get("signals_count", 0)
            min_signals = flags.get("min_signals_required", 3)
            score = item.get("score", 0)
            matched = item.get("match", False)
            
            # 신호 충족 = 후보군 (점수 무관하게 포함)
            # 신호 미충족 = 점수 기준 적용 (10점 이상)
            if matched:  # 신호 충족으로 매칭된 경우
                step0_items_filtered.append(item)
            elif score >= 10:  # 신호 미충족이지만 점수 높은 경우
                step0_items_filtered.append(item)
        
        # 점수 순으로 정렬 (높은 점수 우선)
        step0_items_filtered.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        step0_items_10_plus = step0_items_filtered
        print(f"📊 Step 0 결과: {len(step0_items_10_plus)}개 종목 (신호충족:점수 무관, 미충족:10점 이상)")
        
        if len(step0_items_10_plus) >= target_min:
            chosen_step = 0
            final_items = step0_items_10_plus[:min(config.top_k, target_max)]
            print(f"✅ Step 0에서 목표 달성: {len(final_items)}개 종목 선택 (10점 이상만)")
        else:
            # Step 1: 지표 완화 Level 1 + 10점 이상
            print(f"🔄 Step 1: 지표 완화 Level 1 + 10점 이상")
            try:
                if len(config.fallback_presets) < 2:
                    print(f"❌ fallback_presets 인덱스 오류: Step 1 프리셋 없음")
                    return [], None
                step1_items = scan_with_preset(universe, config.fallback_presets[1], date, market_condition)
            except Exception as e:
                print(f"❌ Step 1 스캔 오류: {e}")
                return [], None
            # 신호 충족 = 후보군 (점수 무관), 점수는 순위 매기기용
            step1_items_filtered = []
            for item in step1_items:
                flags = item.get("flags", {})
                score = item.get("score", 0)
                matched = item.get("match", False)
                
                if matched:  # 신호 충족으로 매칭된 경우
                    step1_items_filtered.append(item)
                elif score >= 10:  # 신호 미충족이지만 점수 높은 경우
                    step1_items_filtered.append(item)
            
            # 점수 순으로 정렬
            step1_items_filtered.sort(key=lambda x: x.get("score", 0), reverse=True)
            
            step1_items_10_plus = step1_items_filtered
            print(f"📊 Step 1 결과: {len(step1_items_10_plus)}개 종목 (지표 완화 + 신호충족:점수 무관, 미충족:10점 이상)")
            
            if len(step1_items_10_plus) >= target_min:
                chosen_step = 1
                final_items = step1_items_10_plus[:min(config.top_k, target_max)]
                print(f"✅ Step 1에서 목표 달성: {len(final_items)}개 종목 선택 (지표 완화 + 10점 이상)")
            else:
                # Step 2: 지표 완화 Level 1 + 점수 Fallback (신호 충족 = 점수 무관, 미충족 = 8점 이상)
                print(f"🔄 Step 2: 지표 완화 Level 1 + 점수 Fallback")
                step1_items_8_plus = []
                for item in step1_items:
                    flags = item.get("flags", {})
                    score = item.get("score", 0)
                    matched = item.get("match", False)
                    fallback = flags.get("fallback", False)
                    
                    # 신호 충족 = 후보군 (점수 무관하게 포함)
                    # 신호 미충족 = 점수 기준 완화 (8점 이상)
                    if matched:  # 신호 충족으로 매칭된 경우
                        step1_items_8_plus.append(item)
                    elif fallback or score >= 8:  # 신호 미충족이지만 점수 높은 경우
                        step1_items_8_plus.append(item)
                
                # 점수 순으로 정렬
                step1_items_8_plus.sort(key=lambda x: x.get("score", 0), reverse=True)
                
                print(f"📊 Step 2 결과: {len(step1_items_8_plus)}개 종목 (지표 완화 + 신호충족:점수 무관, 미충족:8점 이상)")
                
                if len(step1_items_8_plus) >= target_min:
                    chosen_step = 2
                    final_items = step1_items_8_plus[:min(config.top_k, target_max)]
                    print(f"✅ Step 2에서 목표 달성: {len(final_items)}개 종목 선택 (지표 완화 + 8점 이상)")
                else:
                    # Step 3: 지표 추가 완화 + 8점 이상 (Step 3까지만 시도)
                    print(f"⚠️ Step 2에서 목표 미달 - 지표 추가 완화 시도 (Step 3까지만)")
                    
                    # Step 3: 지표 추가 완화 + 8점 이상
                    print(f"🔄 Step 3: 지표 완화 Level 2 + 8점 이상")
                    try:
                        if len(config.fallback_presets) < 3:
                            print(f"❌ fallback_presets 인덱스 오류: Step 3 프리셋 없음")
                            final_items = []
                            chosen_step = None
                        else:
                            step3_overrides = config.fallback_presets[2]
                            print(f"   설정: {step3_overrides}")
                            step3_items = scan_with_preset(universe, step3_overrides, date, market_condition)
                            # Step 3: 신호 충족 = 점수 무관, 미충족 = 8점 이상
                            step3_items_8_plus = []
                            for item in step3_items:
                                flags = item.get("flags", {})
                                score = item.get("score", 0)
                                matched = item.get("match", False)
                                fallback = flags.get("fallback", False)
                                
                                # 신호 충족 = 후보군 (점수 무관하게 포함)
                                # 신호 미충족 = 점수 기준 완화 (8점 이상)
                                if matched:  # 신호 충족으로 매칭된 경우
                                    step3_items_8_plus.append(item)
                                elif fallback or score >= 8:  # 신호 미충족이지만 점수 높은 경우
                                    step3_items_8_plus.append(item)
                            
                            # 점수 순으로 정렬
                            step3_items_8_plus.sort(key=lambda x: x.get("score", 0), reverse=True)
                            
                            print(f"📊 Step 3 결과: {len(step3_items_8_plus)}개 종목 (지표 완화 Level 2 + 신호충족:점수 무관, 미충족:8점 이상)")
                            
                            if len(step3_items_8_plus) >= target_min:
                                chosen_step = 3
                                final_items = step3_items_8_plus[:min(config.top_k, target_max)]
                                print(f"✅ Step 3에서 목표 달성: {len(final_items)}개 종목 선택")
                            else:
                                print(f"❌ Step 3 목표 미달: {len(step3_items_8_plus)} < {target_min}")
                    except Exception as e:
                        print(f"❌ Step 3 스캔 오류: {e}")
                        final_items = []
                        chosen_step = None
                    
                    # Step 3에서도 목표 미달이면 빈 리스트 반환 (Step 7 제거)
                    if not final_items:
                        print(f"⚠️ Step 0~3 모두 목표 미달 - 추천 종목 없음 (품질 저하 방지)")
                        print(f"🔍 디버깅: universe={len(universe)}개, market_condition={market_condition}")
                        final_items = []
                        chosen_step = None
        
        items = final_items
    
    print(f"🎯 최종 선택: Step {chosen_step}, {len(items)}개 종목")
    return items, chosen_step

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
    """Fallback 로직을 적용한 스캔 실행"""
    chosen_step = None
    
    # 급락장 감지 시 추천하지 않음
    if market_condition and market_condition.market_sentiment == 'crash':
        print(f"🔴 급락장 감지 (KOSPI: {market_condition.kospi_return:.2f}%) - 추천 종목 없음 반환")
        return [], None
    
    # 약세장에서도 fallback 활성화하되, 장세별 목표 개수 적용
    use_fallback = config.fallback_enable
    
    # 장세별 MIN/MAX 설정
    if market_condition and market_condition.market_sentiment == 'bear':
        target_min = config.fallback_target_min_bear
        target_max = config.fallback_target_max_bear
        print(f"⚠️ 약세장 감지 (KOSPI: {market_condition.kospi_return:.2f}%) - Fallback 활성화, 목표: {target_min}~{target_max}개")
    else:
        target_min = config.fallback_target_min_bull
        target_max = config.fallback_target_max_bull
        if market_condition:
            print(f"📈 {market_condition.market_sentiment} 장세 (KOSPI: {market_condition.kospi_return:.2f}%) - Fallback 활성화, 목표: {target_min}~{target_max}개")
    
    print(f"🔄 Fallback 로직 시작: universe={len(universe)}개, fallback_enable={use_fallback}")
    
    if not use_fallback:
        # Fallback 비활성화 시 기존 로직
        print(f"📊 Fallback 비활성화 - 시장 상황 기반 조건으로 스캔")
        items = scan_with_preset(universe, {}, date, market_condition)
        items = items[:config.top_k]
        print(f"📊 스캔 결과: {len(items)}개 종목 (조건 강화)")
    else:
        # Fallback 활성화 시 단계별 완화
        final_items = []
        chosen_step = 0
        
        print(f"📊 Fallback 활성화 - {len(config.fallback_presets)}단계 완화 시도")
        print(f"📊 목표: 최소 {target_min}개, 최대 {target_max}개")
        
        for step, overrides in enumerate(config.fallback_presets):
            print(f"🔄 Step {step}: {overrides if overrides else '기본 조건'}")
            items = scan_with_preset(universe, overrides, date, market_condition)
            print(f"📊 Step {step} 결과: {len(items)}개 종목")
            
            # 하드 컷은 scan_one_symbol 내부에서 이미 처리되어야 함(과열/유동성/가격 등)
            if len(items) >= target_min:
                chosen_step = step
                final_items = items[:min(config.top_k, target_max)]
                print(f"✅ Step {step}에서 목표 달성: {len(final_items)}개 종목 선택")
                break
            else:
                print(f"❌ Step {step} 목표 미달: {len(items)} < {target_min}")
        
        # 만약 모든 단계에서도 목표 미달이라면, 마지막 단계 결과에서 score 상위만 가져오기
        if not final_items:
            print(f"⚠️ 모든 단계에서 목표 미달 - 마지막 단계 결과 사용")
            if items:  # 마지막 단계에서 결과가 있다면
                final_items = items[:min(config.top_k, target_max)]
                chosen_step = len(config.fallback_presets) - 1
                print(f"📊 최종 결과: {len(final_items)}개 종목 (마지막 단계)")
            else:
                print(f"❌ 모든 단계에서 0개 결과 - 빈 리스트 반환")
                print(f"🔍 디버깅: universe={len(universe)}개, market_condition={market_condition}")
                final_items = []
        
        items = final_items
    
    print(f"🎯 최종 선택: Step {chosen_step}, {len(items)}개 종목")
    return items, chosen_step

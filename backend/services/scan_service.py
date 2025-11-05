"""
스캔 관련 서비스
"""
import sqlite3
import json
import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime
from scanner import scan_with_preset
from config import config
from kiwoom_api import api


def _db_path() -> str:
    """데이터베이스 경로 반환"""
    return "snapshots.db"


def get_recurrence_data(tickers: List[str], today_as_of: str) -> Dict[str, Dict]:
    """재등장 이력 조회 (배치 처리)"""
    recurrence_data = {}
    
    if not tickers:
        return recurrence_data
    
    try:
        conn_hist = sqlite3.connect(_db_path(), timeout=30.0)
        conn_hist.execute("PRAGMA journal_mode=WAL")
        conn_hist.execute("PRAGMA synchronous=NORMAL")
        cur_hist = conn_hist.cursor()
        cur_hist.execute("CREATE TABLE IF NOT EXISTS scan_rank(date TEXT, code TEXT, score REAL, flags TEXT, score_label TEXT, close_price REAL, PRIMARY KEY(date, code))")
        
        # 모든 종목의 재등장 이력을 한 번에 조회
        placeholders = ','.join(['?' for _ in tickers])
        query = f"SELECT code, date FROM scan_rank WHERE code IN ({placeholders}) ORDER BY code, date DESC"
        
        rows = cur_hist.execute(query, tickers).fetchall()
        conn_hist.close()
        
        # 결과를 종목별로 그룹화
        for ticker in tickers:
            prev_dates = [str(row[1]) for row in rows if row[0] == ticker and str(row[1]) < today_as_of]
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
        conn_hist = sqlite3.connect(_db_path(), timeout=30.0)
        conn_hist.execute("PRAGMA journal_mode=WAL")
        conn_hist.execute("PRAGMA synchronous=NORMAL")
        conn_hist.execute("PRAGMA cache_size=10000")
        conn_hist.execute("PRAGMA temp_store=memory")
        cur_hist = conn_hist.cursor()
        cur_hist.execute("CREATE TABLE IF NOT EXISTS scan_rank(date TEXT, code TEXT, name TEXT, score REAL, flags TEXT, score_label TEXT, close_price REAL, volume REAL, change_rate REAL, PRIMARY KEY(date, code))")
        # 기존 테이블에 컬럼이 없으면 추가
        try:
            cur_hist.execute("ALTER TABLE scan_rank ADD COLUMN name TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            cur_hist.execute("ALTER TABLE scan_rank ADD COLUMN close_price REAL")
        except sqlite3.OperationalError:
            pass
        try:
            cur_hist.execute("ALTER TABLE scan_rank ADD COLUMN volume REAL")
        except sqlite3.OperationalError:
            pass
        try:
            cur_hist.execute("ALTER TABLE scan_rank ADD COLUMN change_rate REAL")
        except sqlite3.OperationalError:
            pass
        
        # 스냅샷에는 핵심 메타/랭킹만 저장(용량 절약)
        enhanced_rank = []
        for it in scan_items:
            try:
                # 최신 OHLCV 데이터 가져오기 (스냅샷 생성 시점)
                df = api.get_ohlcv(it["ticker"], 2)  # 최근 2일 데이터 (전일 대비 변동률 계산용)
                if not df.empty:
                    latest = df.iloc[-1]
                    prev = df.iloc[-2] if len(df) > 1 else None
                    change_rate = (latest.close - prev.close) / prev.close if prev is not None and prev.close else 0.0
                    enhanced_rank.append({
                        "date": today_as_of,
                        "code": it["ticker"],
                        "name": it["name"],
                        "score": it["score"],
                        "flags": json.dumps(it["flags"]),
                        "score_label": it["score_label"],
                        "close_price": latest.close,
                        "volume": latest.volume,
                        "change_rate": change_rate,
                    })
            except Exception:
                continue
        
        # 기존 스냅샷 삭제
        cur_hist.execute("DELETE FROM scan_rank WHERE date=?", (today_as_of,))
        
        # 스캔 결과가 0개인 경우 NORESULT 레코드 추가
        if not scan_items:
            print(f"📭 스캔 결과 0개 - NORESULT 레코드 저장: {today_as_of}")
            cur_hist.execute(
                "INSERT INTO scan_rank (date, code, name, score, flags, score_label, close_price, volume, change_rate) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (today_as_of, "NORESULT", "추천종목 없음", 0.0, json.dumps({"no_result": True}), "추천종목 없음", 0.0, 0.0, 0.0)
            )
        elif enhanced_rank:
            cur_hist.executemany("INSERT INTO scan_rank (date, code, name, score, flags, score_label, close_price, volume, change_rate) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                [(r["date"], r["code"], r["name"], r["score"], r["flags"], r["score_label"], r["close_price"], r["volume"], r["change_rate"]) for r in enhanced_rank])
        else:
            # enhanced_rank도 비어있으면 NORESULT 저장
            print(f"📭 enhanced_rank 비어있음 - NORESULT 레코드 저장: {today_as_of}")
            cur_hist.execute(
                "INSERT INTO scan_rank (date, code, name, score, flags, score_label, close_price, volume, change_rate) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (today_as_of, "NORESULT", "추천종목 없음", 0.0, json.dumps({"no_result": True}), "추천종목 없음", 0.0, 0.0, 0.0)
            )
        conn_hist.commit()
        conn_hist.close()
    except Exception as e:
        print(f"스냅샷 저장 오류: {e}")


def execute_scan_with_fallback(universe: List[str], date: Optional[str] = None, market_condition=None) -> tuple:
    """Fallback 로직을 적용한 스캔 실행"""
    chosen_step = None
    
    print(f"🔄 Fallback 로직 시작: universe={len(universe)}개, fallback_enable={config.fallback_enable}")
    
    if not config.fallback_enable:
        # Fallback 비활성화 시 기존 로직
        print(f"📊 Fallback 비활성화 - 기본 조건으로 스캔")
        items = scan_with_preset(universe, {}, date, market_condition)
        items = items[:config.top_k]
        print(f"📊 기본 스캔 결과: {len(items)}개 종목")
    else:
        # Fallback 활성화 시 단계별 완화
        final_items = []
        chosen_step = 0
        
        print(f"📊 Fallback 활성화 - {len(config.fallback_presets)}단계 완화 시도")
        print(f"📊 목표: 최소 {config.fallback_target_min}개, 최대 {config.fallback_target_max}개")
        
        for step, overrides in enumerate(config.fallback_presets):
            print(f"🔄 Step {step}: {overrides if overrides else '기본 조건'}")
            items = scan_with_preset(universe, overrides, date, market_condition)
            print(f"📊 Step {step} 결과: {len(items)}개 종목")
            
            # 하드 컷은 scan_one_symbol 내부에서 이미 처리되어야 함(과열/유동성/가격 등)
            if len(items) >= config.fallback_target_min:
                chosen_step = step
                final_items = items[:min(config.top_k, config.fallback_target_max)]
                print(f"✅ Step {step}에서 목표 달성: {len(final_items)}개 종목 선택")
                break
            else:
                print(f"❌ Step {step} 목표 미달: {len(items)} < {config.fallback_target_min}")
        
        # 만약 모든 단계에서도 목표 미달이라면, 마지막 단계 결과에서 score 상위만 가져오기
        if not final_items:
            print(f"⚠️ 모든 단계에서 목표 미달 - 마지막 단계 결과 사용")
            if items:  # 마지막 단계에서 결과가 있다면
                final_items = items[:min(config.top_k, config.fallback_target_max)]
                chosen_step = len(config.fallback_presets) - 1
                print(f"📊 최종 결과: {len(final_items)}개 종목 (마지막 단계)")
            else:
                print(f"❌ 모든 단계에서 0개 결과 - 빈 리스트 반환")
                print(f"🔍 디버깅: universe={len(universe)}개, market_condition={market_condition}")
                final_items = []
        
        items = final_items
    
    print(f"🎯 최종 선택: Step {chosen_step}, {len(items)}개 종목")
    return items, chosen_step

#!/usr/bin/env python3
"""
간단한 백필 스크립트 - 복잡한 모듈 구조 없이 직접 실행
"""
import os
import pickle
import psycopg
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# DB 연결
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://rexsmac@localhost/stockfinder")

def load_cache_data():
    """캐시 데이터 로드"""
    cache_dir = Path("data_cache")
    
    data = {}
    try:
        with open(cache_dir / "kospi200_ohlcv.pkl", 'rb') as f:
            data['kospi'] = pickle.load(f)
        with open(cache_dir / "spy_ohlcv.pkl", 'rb') as f:
            data['spy'] = pickle.load(f)
        with open(cache_dir / "qqq_ohlcv.pkl", 'rb') as f:
            data['qqq'] = pickle.load(f)
        with open(cache_dir / "vix_ohlcv.pkl", 'rb') as f:
            data['vix'] = pickle.load(f)
        with open(cache_dir / "universe_ohlcv.pkl", 'rb') as f:
            data['universe'] = pickle.load(f)
        logger.info("캐시 데이터 로드 완료")
        return data
    except Exception as e:
        logger.error(f"캐시 데이터 로드 실패: {e}")
        return None

def analyze_regime(date_str, cache_data):
    """간단한 레짐 분석"""
    try:
        date_dt = pd.to_datetime(date_str, format='%Y%m%d')
        
        # 한국 점수
        kospi_data = cache_data['kospi']
        mask = kospi_data.index <= date_dt
        if mask.any():
            recent = kospi_data[mask].tail(5)
            if len(recent) >= 2:
                kr_return = (recent.iloc[-1]['close'] / recent.iloc[-2]['close'] - 1)
                kr_score = 1.0 if kr_return > 0.01 else (-1.0 if kr_return < -0.01 else 0.0)
            else:
                kr_score = 0.0
        else:
            kr_score = 0.0
        
        # 미국 점수
        spy_data = cache_data['spy']
        us_mask = spy_data.index <= date_dt
        if us_mask.any():
            us_recent = spy_data[us_mask].tail(5)
            if len(us_recent) >= 2:
                us_return = (us_recent.iloc[-1]['close'] / us_recent.iloc[-2]['close'] - 1)
                us_score = 1.0 if us_return > 0.01 else (-1.0 if us_return < -0.01 else 0.0)
            else:
                us_score = 0.0
        else:
            us_score = 0.0
        
        # 최종 점수
        final_score = 0.6 * kr_score + 0.4 * us_score
        
        if final_score >= 1.0:
            final_regime = "bull"
        elif final_score <= -1.0:
            final_regime = "bear"
        else:
            final_regime = "neutral"
        
        return {
            'final_regime': final_regime,
            'final_score': final_score,
            'kr_score': kr_score,
            'us_prev_score': us_score,
            'us_preopen_score': 0.0,
            'version': 'simple-v1'
        }
    except Exception as e:
        logger.error(f"레짐 분석 실패 ({date_str}): {e}")
        return {
            'final_regime': 'neutral',
            'final_score': 0.0,
            'kr_score': 0.0,
            'us_prev_score': 0.0,
            'us_preopen_score': 0.0,
            'version': 'simple-v1'
        }

def scan_stocks(date_str, regime, cache_data):
    """간단한 스톡 스캔"""
    try:
        universe = cache_data['universe']
        date_dt = pd.to_datetime(date_str, format='%Y%m%d')
        
        candidates = {'swing': [], 'position': [], 'longterm': []}
        
        # crash면 빈 결과
        if regime == 'crash':
            return candidates
        
        # 샘플 종목들 스캔
        for code, df in list(universe.items())[:50]:  # 50개만 테스트
            try:
                mask = df.index <= date_dt
                if not mask.any():
                    continue
                
                recent = df[mask].tail(10)
                if len(recent) < 5:
                    continue
                
                current = recent.iloc[-1]
                
                # 간단한 점수 계산
                price = current['close']
                volume = current['volume']
                
                if price < 1000 or volume < 10000:
                    continue
                
                # 수익률 기반 점수
                returns = recent['close'].pct_change().dropna()
                if len(returns) < 3:
                    continue
                
                avg_return = returns.mean()
                score = 5.0 + avg_return * 100  # 기본 5점 + 수익률 보정
                
                if score < 3.0:
                    continue
                
                candidate = {
                    'code': code,
                    'score': score,
                    'price': price,
                    'volume': int(volume)
                }
                
                # 레짐별 분류
                if regime == 'bull' and score >= 5.0:
                    candidates['swing'].append(candidate)
                    candidates['position'].append(candidate)
                    candidates['longterm'].append(candidate)
                elif regime == 'neutral' and score >= 4.5:
                    candidates['position'].append(candidate)
                    candidates['longterm'].append(candidate)
                elif regime == 'bear' and score >= 6.0:
                    candidates['longterm'].append(candidate)
                    
            except Exception as e:
                continue
        
        # 최대 개수 제한
        for horizon in candidates:
            candidates[horizon] = sorted(candidates[horizon], key=lambda x: x['score'], reverse=True)[:15]
        
        return candidates
        
    except Exception as e:
        logger.error(f"스캔 실패 ({date_str}): {e}")
        return {'swing': [], 'position': [], 'longterm': []}

def save_to_db(date_str, regime_data, scan_data):
    """DB 저장"""
    try:
        formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                # 레짐 데이터 저장
                cur.execute("""
                    INSERT INTO market_regime_daily (
                        date, final_regime, us_metrics, kr_metrics, us_preopen_metrics, version
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (date) DO UPDATE SET
                        final_regime = EXCLUDED.final_regime,
                        us_metrics = EXCLUDED.us_metrics,
                        kr_metrics = EXCLUDED.kr_metrics,
                        us_preopen_metrics = EXCLUDED.us_preopen_metrics,
                        run_timestamp = CURRENT_TIMESTAMP
                """, (
                    formatted_date,
                    regime_data['final_regime'],
                    f'{{"final_score": {regime_data["final_score"]}}}',
                    f'{{"kr_score": {regime_data["kr_score"]}}}',
                    f'{{"us_preopen_score": {regime_data["us_preopen_score"]}}}',
                    regime_data['version']
                ))
                
                # 스캔 데이터 저장
                cur.execute("DELETE FROM scan_daily WHERE date = %s AND version = 'simple-v1'", (formatted_date,))
                
                for horizon, candidates in scan_data.items():
                    for candidate in candidates:
                        cur.execute("""
                            INSERT INTO scan_daily (date, horizon, code, score, price, volume, version)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """, (
                            formatted_date, horizon, candidate['code'],
                            candidate['score'], candidate['price'], candidate['volume'], 'simple-v1'
                        ))
                
                conn.commit()
        
    except Exception as e:
        logger.error(f"DB 저장 실패 ({date_str}): {e}")

def run_backfill(start_date, end_date):
    """백필 실행"""
    logger.info(f"백필 시작: {start_date} ~ {end_date}")
    
    # 캐시 데이터 로드
    cache_data = load_cache_data()
    if not cache_data:
        logger.error("캐시 데이터 로드 실패")
        return
    
    # 날짜 범위 생성
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    
    current_dt = start_dt
    success_count = 0
    total_count = 0
    
    while current_dt <= end_dt:
        if current_dt.weekday() < 5:  # 주말 제외
            date_str = current_dt.strftime('%Y%m%d')
            total_count += 1
            
            try:
                logger.info(f"처리 중: {date_str}")
                
                # 레짐 분석
                regime_data = analyze_regime(date_str, cache_data)
                
                # 스톡 스캔
                scan_data = scan_stocks(date_str, regime_data['final_regime'], cache_data)
                
                # DB 저장
                save_to_db(date_str, regime_data, scan_data)
                
                success_count += 1
                
                total_candidates = sum(len(candidates) for candidates in scan_data.values())
                logger.info(f"완료: {date_str} - {regime_data['final_regime']} - {total_candidates}개 후보")
                
            except Exception as e:
                logger.error(f"처리 실패 ({date_str}): {e}")
        
        current_dt += timedelta(days=1)
    
    logger.info(f"백필 완료: {success_count}/{total_count} 성공")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("사용법: python simple_backfill.py 2020-01-01 2025-11-22")
        sys.exit(1)
    
    start_date = sys.argv[1]
    end_date = sys.argv[2]
    
    run_backfill(start_date, end_date)
#!/usr/bin/env python3
"""
과거 스캔 데이터 분석을 통한 최적 조건 도출

목표:
1. scan_rank 테이블에서 과거 스캔 데이터 로드
2. 각 종목의 가격 추적 (익절/손절/보존 시뮬레이션)
3. 다양한 조건 조합 테스트:
   - min_signals: 1, 2, 3
   - vol_ma5_mult: 1.3, 1.5, 1.8, 2.0, 2.5
   - score_threshold: 6, 8, 10
4. 각 조합별 승률, 평균 수익률, 추천 종목 수 분석
5. 최적 조건 추천
"""

import os
import sys
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
from collections import defaultdict

import FinanceDataReader as fdr
import pandas as pd
import numpy as np

# Environment prep
os.environ.setdefault("SKIP_DB_PATCH", "1")

from config import config  # noqa: E402
from db_manager import db_manager  # noqa: E402

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "optimal_conditions_analysis_jul_sep")


def ensure_output_dir():
    """출력 디렉토리 생성"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)


class PriceCache:
    """가격 데이터 캐시 (FinanceDataReader 사용)"""
    def __init__(self, start_date: str, end_date: str):
        self.cache = {}
        self.start_date = start_date
        self.end_date = end_date
    
    def get_prices(self, ticker: str) -> pd.DataFrame:
        """종목 가격 데이터 조회 (캐시 활용)"""
        if ticker not in self.cache:
            try:
                df = fdr.DataReader(ticker, self.start_date, self.end_date)
                if df.empty:
                    print(f"⚠️ {ticker}: 데이터 없음")
                    self.cache[ticker] = pd.DataFrame()
                else:
                    self.cache[ticker] = df
            except Exception as e:
                print(f"❌ {ticker} 데이터 로드 실패: {e}")
                self.cache[ticker] = pd.DataFrame()
        
        return self.cache[ticker]


def load_scan_history(start_date: str = "20250701", end_date: str = "20250930") -> List[Dict]:
    """scan_rank 테이블에서 과거 스캔 데이터 로드"""
    try:
        with db_manager.get_cursor() as cur:
            cur.execute("""
                SELECT date, code, name, score, score_label, 
                       current_price, close_price, volume, change_rate,
                       indicators, flags, details
                FROM scan_rank
                WHERE date >= %s AND date <= %s
                ORDER BY date ASC, score DESC
            """, (start_date, end_date))
            
            rows = cur.fetchall()
            
            results = []
            for row in rows:
                # PostgreSQL은 JSON을 dict로 반환, SQLite는 문자열로 반환
                indicators = row[9] if isinstance(row[9], dict) else (json.loads(row[9]) if row[9] else {})
                flags = row[10] if isinstance(row[10], dict) else (json.loads(row[10]) if row[10] else {})
                details = row[11] if isinstance(row[11], dict) else (json.loads(row[11]) if row[11] else {})
                
                # details가 None이면 indicators['details']에서 가져오기 (구 스키마 호환)
                if not details and indicators and 'details' in indicators:
                    details = indicators['details']
                
                # date가 datetime.date 객체일 수 있으므로 문자열로 변환
                date_str = row[0].strftime("%Y%m%d") if hasattr(row[0], 'strftime') else row[0]
                
                # score가 비정상적으로 큰 값이면 스킵 (데이터 오류)
                score = row[3]
                if score and score > 100:
                    continue
                
                results.append({
                    "date": date_str,
                    "code": row[1],
                    "name": row[2],
                    "score": score,
                    "score_label": row[4],
                    "current_price": row[5] or row[6],  # current_price 우선, 없으면 close_price
                    "volume": row[7],
                    "change_rate": row[8],
                    "indicators": indicators,
                    "flags": flags,
                    "details": details,
                })
            
            print(f"✅ {len(results)}개 스캔 데이터 로드 완료 ({start_date} ~ {end_date})")
            return results
    
    except Exception as e:
        print(f"❌ 스캔 데이터 로드 실패: {e}")
        return []


def evaluate_returns(
    scan_data: List[Dict],
    price_cache: PriceCache,
    stop_loss: float = -0.07,
    take_profit: float = 0.03,
    preserve: float = 0.015,
    max_hold_days: int = 45
) -> List[Dict]:
    """각 스캔 종목의 수익률 계산"""
    results = []
    
    for item in scan_data:
        ticker = item["code"]
        scan_date = item["date"]
        scan_price = item["current_price"]
        
        if not scan_price or scan_price <= 0:
            continue
        
        # 가격 데이터 조회
        df = price_cache.get_prices(ticker)
        if df.empty:
            continue
        
        # 스캔 날짜 이후 데이터만 필터링
        scan_dt = datetime.strptime(scan_date, "%Y%m%d")
        df_after = df[df.index > scan_dt]
        
        if df_after.empty:
            continue
        
        # 매수가 = 스캔 다음날 시가 (없으면 스캔가)
        if len(df_after) > 0:
            buy_price = float(df_after.iloc[0]['Open']) if df_after.iloc[0]['Open'] > 0 else scan_price
        else:
            buy_price = scan_price
        
        # 매도 시뮬레이션
        sell_price = None
        sell_date = None
        sell_reason = None
        peak_return = 0.0
        
        for i, (date, row) in enumerate(df_after.iterrows()):
            if i >= max_hold_days:
                sell_price = float(row['Close'])
                sell_date = date.strftime("%Y%m%d")
                sell_reason = "max_hold"
                break
            
            high = float(row['High']) if row['High'] > 0 else float(row['Close'])
            low = float(row['Low']) if row['Low'] > 0 else float(row['Close'])
            close = float(row['Close'])
            
            # 당일 최고가 기준 수익률
            high_return = (high - buy_price) / buy_price
            low_return = (low - buy_price) / buy_price
            close_return = (close - buy_price) / buy_price
            
            # Peak 업데이트
            peak_return = max(peak_return, high_return)
            
            # 손절 체크 (저가 기준)
            if low_return <= stop_loss:
                sell_price = buy_price * (1 + stop_loss)
                sell_date = date.strftime("%Y%m%d")
                sell_reason = "stop_loss"
                break
            
            # 익절 체크 (고가 기준)
            if high_return >= take_profit:
                sell_price = buy_price * (1 + take_profit)
                sell_date = date.strftime("%Y%m%d")
                sell_reason = "take_profit"
                break
            
            # 보존 체크 (고가가 preserve 이상 도달 후 종가가 하락)
            if peak_return >= preserve and close_return < preserve * 0.5:
                sell_price = close
                sell_date = date.strftime("%Y%m%d")
                sell_reason = "preserve"
                break
        
        # 만기까지 매도 안됨
        if sell_price is None:
            if len(df_after) > 0:
                sell_price = float(df_after.iloc[-1]['Close'])
                sell_date = df_after.index[-1].strftime("%Y%m%d")
                sell_reason = "hold_end"
            else:
                continue
        
        final_return = (sell_price - buy_price) / buy_price
        hold_days = (datetime.strptime(sell_date, "%Y%m%d") - scan_dt).days if sell_date else 0
        
        results.append({
            **item,
            "buy_price": buy_price,
            "sell_price": sell_price,
            "sell_date": sell_date,
            "sell_reason": sell_reason,
            "hold_days": hold_days,
            "return": final_return,
            "peak_return": peak_return,
        })
    
    return results


def filter_by_conditions(
    scan_data: List[Dict],
    min_signals: int = None,
    vol_ma5_mult: float = None,
    score_threshold: int = None
) -> List[Dict]:
    """조건에 따라 스캔 데이터 필터링"""
    filtered = []
    
    for item in scan_data:
        indicators = item.get("indicators", {})
        details = item.get("details", {})
        score = item.get("score", 0)
        
        # 점수 필터
        if score_threshold is not None and score < score_threshold:
            continue
        
        # min_signals 필터
        if min_signals is not None:
            signal_count = 0
            
            # details가 있으면 사용, 없으면 indicators에서 직접 계산
            if details:
                if details.get("CROSS_GOLDEN"):
                    signal_count += 1
                if details.get("VOL_SURGE"):
                    signal_count += 1
                if details.get("MACD_GOLDEN"):
                    signal_count += 1
                if details.get("RSI_OVERSOLD_RECOVERY"):
                    signal_count += 1
                if details.get("TEMA_SLOPE_POSITIVE"):
                    signal_count += 1
                if details.get("DEMA_SLOPE_POSITIVE"):
                    signal_count += 1
                if details.get("OBV_SLOPE_POSITIVE"):
                    signal_count += 1
            else:
                # indicators에서 직접 신호 계산
                # 골든크로스: RSI_DEMA < RSI_TEMA
                if indicators.get("RSI_DEMA", 0) < indicators.get("RSI_TEMA", 0):
                    signal_count += 1
                
                # 거래량 급증: VOL > VOL_MA5 * 1.5
                vol = indicators.get("VOL", 0)
                vol_ma5 = indicators.get("VOL_MA5", 1)
                if vol_ma5 > 0 and vol / vol_ma5 > 1.5:
                    signal_count += 1
                
                # MACD 골든크로스: MACD_OSC > 0
                if indicators.get("MACD_OSC", 0) > 0:
                    signal_count += 1
            
            if signal_count < min_signals:
                continue
        
        # vol_ma5_mult 필터
        if vol_ma5_mult is not None:
            vol = indicators.get("VOL", 0)
            vol_ma5 = indicators.get("VOL_MA5", 1)
            if vol_ma5 > 0:
                vol_ratio = vol / vol_ma5
                if vol_ratio < vol_ma5_mult:
                    continue
            else:
                continue
        
        filtered.append(item)
    
    return filtered


def analyze_condition_combination(
    scan_data_with_returns: List[Dict],
    min_signals: int,
    vol_ma5_mult: float,
    score_threshold: int
) -> Dict[str, Any]:
    """특정 조건 조합에 대한 성과 분석"""
    # 필터링
    filtered = filter_by_conditions(
        scan_data_with_returns,
        min_signals=min_signals,
        vol_ma5_mult=vol_ma5_mult,
        score_threshold=score_threshold
    )
    
    if not filtered:
        return {
            "min_signals": min_signals,
            "vol_ma5_mult": vol_ma5_mult,
            "score_threshold": score_threshold,
            "total_picks": 0,
            "win_count": 0,
            "win_rate": 0.0,
            "avg_return": 0.0,
            "avg_hold_days": 0.0,
            "total_return": 0.0,
        }
    
    # 성과 계산
    returns = [item["return"] for item in filtered]
    win_count = sum(1 for r in returns if r > 0)
    win_rate = win_count / len(returns) if returns else 0.0
    avg_return = np.mean(returns) if returns else 0.0
    total_return = sum(returns)
    avg_hold_days = np.mean([item["hold_days"] for item in filtered])
    
    # 날짜별 추천 종목 수
    dates = defaultdict(int)
    for item in filtered:
        dates[item["date"]] += 1
    
    avg_picks_per_day = np.mean(list(dates.values())) if dates else 0.0
    
    return {
        "min_signals": min_signals,
        "vol_ma5_mult": vol_ma5_mult,
        "score_threshold": score_threshold,
        "total_picks": len(filtered),
        "win_count": win_count,
        "win_rate": win_rate,
        "avg_return": avg_return,
        "avg_hold_days": avg_hold_days,
        "total_return": total_return,
        "avg_picks_per_day": avg_picks_per_day,
        "trading_days": len(dates),
    }


def main():
    ensure_output_dir()
    
    print("=" * 80)
    print("📊 과거 스캔 데이터 분석을 통한 최적 조건 도출 (7~9월)")
    print("=" * 80)
    
    # 1. 과거 스캔 데이터 로드
    print("\n[1단계] 과거 스캔 데이터 로드 (7~9월)")
    scan_data = load_scan_history(start_date="20250701", end_date="20250930")
    
    if not scan_data:
        print("❌ 스캔 데이터가 없습니다.")
        return
    
    print(f"   총 {len(scan_data)}개 스캔 데이터")
    
    # 날짜별 통계
    dates = set(item["date"] for item in scan_data)
    print(f"   기간: {min(dates)} ~ {max(dates)} ({len(dates)}일)")
    
    # 2. 가격 추적 및 수익률 계산
    print("\n[2단계] 가격 추적 및 수익률 계산")
    price_cache = PriceCache("2025-06-01", "2025-11-30")
    
    scan_data_with_returns = evaluate_returns(
        scan_data,
        price_cache,
        stop_loss=-0.07,
        take_profit=0.03,
        preserve=0.015,
        max_hold_days=45
    )
    
    print(f"   수익률 계산 완료: {len(scan_data_with_returns)}개 종목")
    
    # 전체 성과
    if scan_data_with_returns:
        returns = [item["return"] for item in scan_data_with_returns]
        win_count = sum(1 for r in returns if r > 0)
        win_rate = win_count / len(returns)
        avg_return = np.mean(returns)
        print(f"   전체 승률: {win_rate*100:.1f}% ({win_count}/{len(returns)})")
        print(f"   전체 평균 수익률: {avg_return*100:.2f}%")
    
    # 3. 다양한 조건 조합 테스트
    print("\n[3단계] 다양한 조건 조합 테스트")
    
    test_conditions = []
    for min_signals in [1, 2, 3]:
        for vol_ma5_mult in [1.3, 1.5, 1.8, 2.0, 2.5]:
            for score_threshold in [6, 8, 10]:
                test_conditions.append({
                    "min_signals": min_signals,
                    "vol_ma5_mult": vol_ma5_mult,
                    "score_threshold": score_threshold,
                })
    
    print(f"   총 {len(test_conditions)}개 조합 테스트")
    
    results = []
    for i, cond in enumerate(test_conditions, 1):
        result = analyze_condition_combination(
            scan_data_with_returns,
            min_signals=cond["min_signals"],
            vol_ma5_mult=cond["vol_ma5_mult"],
            score_threshold=cond["score_threshold"]
        )
        results.append(result)
        
        if i % 15 == 0:
            print(f"   진행: {i}/{len(test_conditions)}")
    
    # 4. 결과 정렬 및 저장
    print("\n[4단계] 결과 분석")
    
    # 승률 기준 정렬
    results_by_winrate = sorted(results, key=lambda x: x["win_rate"], reverse=True)
    
    # 평균 수익률 기준 정렬
    results_by_return = sorted(results, key=lambda x: x["avg_return"], reverse=True)
    
    # 추천 종목 수가 적정한 조합 (일평균 1~5개)
    results_balanced = [r for r in results if 1 <= r.get("avg_picks_per_day", 0) <= 5]
    results_balanced_sorted = sorted(results_balanced, key=lambda x: (x["win_rate"], x["avg_return"]), reverse=True)
    
    # 결과 출력
    print("\n" + "=" * 80)
    print("📊 최적 조건 분석 결과")
    print("=" * 80)
    
    print("\n[승률 TOP 10]")
    for i, r in enumerate(results_by_winrate[:10], 1):
        print(f"{i:2d}. min_signals={r['min_signals']}, vol={r['vol_ma5_mult']:.1f}, score≥{r['score_threshold']} "
              f"→ 승률 {r['win_rate']*100:.1f}%, 평균 {r['avg_return']*100:+.2f}%, "
              f"종목 {r['total_picks']}개 (일평균 {r.get('avg_picks_per_day', 0):.1f}개)")
    
    print("\n[평균 수익률 TOP 10]")
    for i, r in enumerate(results_by_return[:10], 1):
        print(f"{i:2d}. min_signals={r['min_signals']}, vol={r['vol_ma5_mult']:.1f}, score≥{r['score_threshold']} "
              f"→ 평균 {r['avg_return']*100:+.2f}%, 승률 {r['win_rate']*100:.1f}%, "
              f"종목 {r['total_picks']}개 (일평균 {r.get('avg_picks_per_day', 0):.1f}개)")
    
    print("\n[균형잡힌 조건 TOP 10] (일평균 1~5개 추천)")
    for i, r in enumerate(results_balanced_sorted[:10], 1):
        print(f"{i:2d}. min_signals={r['min_signals']}, vol={r['vol_ma5_mult']:.1f}, score≥{r['score_threshold']} "
              f"→ 승률 {r['win_rate']*100:.1f}%, 평균 {r['avg_return']*100:+.2f}%, "
              f"일평균 {r.get('avg_picks_per_day', 0):.1f}개")
    
    # 5. 최종 추천
    print("\n" + "=" * 80)
    print("💡 최종 추천 조건")
    print("=" * 80)
    
    if results_balanced_sorted:
        best = results_balanced_sorted[0]
        print(f"\n✅ 추천 조건:")
        print(f"   - min_signals: {best['min_signals']}")
        print(f"   - vol_ma5_mult: {best['vol_ma5_mult']}")
        print(f"   - score_threshold: {best['score_threshold']}")
        print(f"\n📊 예상 성과:")
        print(f"   - 승률: {best['win_rate']*100:.1f}%")
        print(f"   - 평균 수익률: {best['avg_return']*100:+.2f}%")
        print(f"   - 일평균 추천 종목: {best.get('avg_picks_per_day', 0):.1f}개")
        print(f"   - 평균 보유 기간: {best['avg_hold_days']:.1f}일")
    
    # JSON 저장
    output_file = os.path.join(OUTPUT_DIR, "optimal_conditions_analysis.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "summary": {
                "total_scan_data": len(scan_data),
                "evaluated_picks": len(scan_data_with_returns),
                "test_conditions": len(test_conditions),
            },
            "top_by_winrate": results_by_winrate[:10],
            "top_by_return": results_by_return[:10],
            "balanced_top": results_balanced_sorted[:10],
            "recommended": results_balanced_sorted[0] if results_balanced_sorted else None,
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 결과 저장: {output_file}")


if __name__ == "__main__":
    main()


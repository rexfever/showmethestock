#!/usr/bin/env python3
"""
3선 시스템 테스트: TEMA20 + DEMA10 + EMA60

목표:
1. 기존 TEMA20/DEMA10 유지
2. EMA60 장기 추세 필터 추가
3. 11월 데이터로 성과 비교
"""

import os
import sys
from datetime import datetime
from typing import List, Dict, Any

import pandas as pd
import numpy as np

# Environment prep
os.environ.setdefault("SKIP_DB_PATCH", "1")

from config import config  # noqa: E402
from db_manager import db_manager  # noqa: E402
from indicators import ema  # noqa: E402

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "test_3line_system_results")


def ensure_output_dir():
    """출력 디렉토리 생성"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def load_scan_data_with_prices() -> List[Dict]:
    """스캔 데이터 + 가격 데이터 로드"""
    try:
        with db_manager.get_cursor() as cur:
            cur.execute("""
                SELECT date, code, name, score, indicators
                FROM scan_rank
                WHERE score < 100
                ORDER BY date ASC, score DESC
            """)
            
            rows = cur.fetchall()
            
            results = []
            for row in rows:
                date_str = row[0].strftime("%Y%m%d") if hasattr(row[0], 'strftime') else row[0]
                indicators = row[4] if isinstance(row[4], dict) else {}
                
                # indicators에서 필요한 값 추출
                tema20 = indicators.get("TEMA20", 0)
                dema10 = indicators.get("DEMA10", 0)
                close = indicators.get("close", 0)
                
                results.append({
                    "date": date_str,
                    "code": row[1],
                    "name": row[2],
                    "score": row[3],
                    "tema20": tema20,
                    "dema10": dema10,
                    "close": close,
                })
            
            print(f"✅ {len(results)}개 스캔 데이터 로드 완료")
            return results
    
    except Exception as e:
        print(f"❌ 스캔 데이터 로드 실패: {e}")
        return []


def fetch_ohlcv_for_ema60(code: str, date: str) -> float:
    """EMA60 계산을 위한 OHLCV 데이터 조회"""
    try:
        from kiwoom_api import api
        
        # 60일 + 여유분 = 80일치 데이터
        df = api.get_ohlcv(code, 80, date)
        
        if df.empty or len(df) < 60:
            return 0.0
        
        # EMA60 계산
        close_series = df["close"].astype(float)
        ema60_series = ema(close_series, 60)
        
        # 가장 최근 EMA60 값
        ema60_value = float(ema60_series.iloc[-1])
        
        return ema60_value
    
    except Exception as e:
        print(f"⚠️ {code} EMA60 계산 실패: {e}")
        return 0.0


def apply_3line_filter(scan_data: List[Dict]) -> tuple:
    """3선 시스템 필터 적용
    
    조건:
    1. TEMA20 > DEMA10 (골든크로스 - 기존)
    2. close > EMA60 (장기 상승 추세)
    
    Returns:
        (filtered_data, filter_stats)
    """
    filtered = []
    stats = {
        "total": len(scan_data),
        "tema_dema_ok": 0,
        "ema60_ok": 0,
        "both_ok": 0,
        "ema60_fetch_failed": 0,
    }
    
    print("\n🔄 3선 시스템 필터 적용 중...")
    
    for i, item in enumerate(scan_data, 1):
        code = item["code"]
        date = item["date"]
        tema20 = item["tema20"]
        dema10 = item["dema10"]
        close = item["close"]
        
        # 조건 1: TEMA20 > DEMA10
        tema_dema_ok = tema20 > dema10
        if tema_dema_ok:
            stats["tema_dema_ok"] += 1
        
        # 조건 2: close > EMA60
        ema60 = fetch_ohlcv_for_ema60(code, date)
        
        if ema60 == 0.0:
            stats["ema60_fetch_failed"] += 1
            continue
        
        ema60_ok = close > ema60
        if ema60_ok:
            stats["ema60_ok"] += 1
        
        # 두 조건 모두 충족
        if tema_dema_ok and ema60_ok:
            stats["both_ok"] += 1
            filtered.append({
                **item,
                "ema60": ema60,
                "ema60_ok": True,
            })
        
        if i % 10 == 0:
            print(f"   진행: {i}/{len(scan_data)}")
    
    print(f"\n📊 필터링 결과:")
    print(f"   전체: {stats['total']}개")
    print(f"   TEMA20 > DEMA10: {stats['tema_dema_ok']}개")
    print(f"   close > EMA60: {stats['ema60_ok']}개")
    print(f"   두 조건 충족: {stats['both_ok']}개")
    print(f"   EMA60 계산 실패: {stats['ema60_fetch_failed']}개")
    
    return filtered, stats


def compare_with_baseline(scan_data: List[Dict], filtered_data: List[Dict]) -> Dict:
    """기존 방식과 3선 시스템 비교"""
    
    baseline_codes = set(item["code"] for item in scan_data)
    filtered_codes = set(item["code"] for item in filtered_data)
    
    removed_codes = baseline_codes - filtered_codes
    
    comparison = {
        "baseline_count": len(baseline_codes),
        "filtered_count": len(filtered_codes),
        "removed_count": len(removed_codes),
        "removal_rate": len(removed_codes) / len(baseline_codes) if baseline_codes else 0,
    }
    
    print(f"\n📊 기존 vs 3선 시스템 비교:")
    print(f"   기존 추천: {comparison['baseline_count']}개")
    print(f"   3선 필터 후: {comparison['filtered_count']}개")
    print(f"   제거된 종목: {comparison['removed_count']}개 ({comparison['removal_rate']*100:.1f}%)")
    
    return comparison


def main():
    ensure_output_dir()
    
    print("=" * 80)
    print("📊 3선 시스템 테스트: TEMA20 + DEMA10 + EMA60")
    print("=" * 80)
    
    # 1. 스캔 데이터 로드
    print("\n[1단계] 스캔 데이터 로드")
    scan_data = load_scan_data_with_prices()
    
    if not scan_data:
        print("❌ 스캔 데이터가 없습니다.")
        return
    
    # 날짜별 통계
    dates = set(item["date"] for item in scan_data)
    print(f"   기간: {min(dates)} ~ {max(dates)} ({len(dates)}일)")
    
    # 2. 3선 시스템 필터 적용
    print("\n[2단계] 3선 시스템 필터 적용")
    filtered_data, filter_stats = apply_3line_filter(scan_data)
    
    # 3. 비교 분석
    print("\n[3단계] 비교 분석")
    comparison = compare_with_baseline(scan_data, filtered_data)
    
    # 4. 결과 출력
    print("\n" + "=" * 80)
    print("💡 3선 시스템 평가")
    print("=" * 80)
    
    if comparison["filtered_count"] == 0:
        print("\n❌ 3선 시스템: 추천 종목 0개")
        print("   → EMA60 조건이 너무 엄격함")
        print("   → 현재 시장이 장기 하락 추세일 가능성")
    elif comparison["removal_rate"] > 0.8:
        print(f"\n⚠️ 3선 시스템: {comparison['removal_rate']*100:.0f}% 제거")
        print("   → EMA60 필터가 너무 강력함")
        print("   → 조건 완화 필요 (예: close > EMA40)")
    elif comparison["removal_rate"] > 0.5:
        print(f"\n✅ 3선 시스템: {comparison['removal_rate']*100:.0f}% 제거")
        print("   → 적절한 필터링 효과")
        print("   → 장기 하락 추세 종목 제거")
    else:
        print(f"\n⚠️ 3선 시스템: {comparison['removal_rate']*100:.0f}% 제거")
        print("   → 필터링 효과가 약함")
        print("   → 대부분 종목이 이미 장기 상승 추세")
    
    print("\n📌 결론:")
    if comparison["filtered_count"] >= 1 and comparison["removal_rate"] >= 0.3:
        print("   ✅ 3선 시스템 도입 권장")
        print("   → 장기 추세 필터로 안정성 향상")
        print("   → 가짜 신호 감소 효과")
    elif comparison["filtered_count"] == 0:
        print("   ❌ 3선 시스템 도입 불가")
        print("   → EMA60 대신 EMA40 또는 EMA30 시도")
        print("   → 또는 다른 조건 완화 필요")
    else:
        print("   ⚠️ 3선 시스템 효과 미미")
        print("   → 현재 종목들이 이미 장기 상승 추세")
        print("   → 다른 조건 완화가 더 효과적")


if __name__ == "__main__":
    main()




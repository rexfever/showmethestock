#!/usr/bin/env python3
"""
11월 V2 스캔 테스트 및 V1 비교
"""
import os
import sys
import json
from datetime import datetime, timedelta

# 경로 설정
sys.path.insert(0, '/Users/rexsmac/workspace/stock-finder/backend')

from scanner_factory import scan_with_scanner
from kiwoom_api import api
from market_analyzer import market_analyzer
from db_manager import db_manager

def test_november_scans():
    """11월 V1, V2 스캔 비교 테스트"""
    
    # 11월 테스트 날짜들 (거래일만)
    test_dates = [
        '20241101', '20241104', '20241105', '20241106', '20241107',
        '20241111', '20241112', '20241113', '20241114', '20241115',
        '20241118', '20241119', '20241120', '20241121', '20241122',
        '20241125', '20241126', '20241127', '20241128', '20241129'
    ]
    
    # 유니버스 설정 (소규모 테스트)
    kospi = api.get_top_codes('KOSPI', 50)
    kosdaq = api.get_top_codes('KOSDAQ', 50)
    universe = kospi + kosdaq
    
    results = {}
    
    for date in test_dates[:3]:  # 처음 3일만 테스트
        print(f"\n📅 {date} 스캔 테스트")
        
        # 시장 상황 분석
        try:
            market_condition = market_analyzer.analyze_market_condition(date)
            print(f"📊 시장 상황: {market_condition.market_sentiment} (KOSPI: {market_condition.kospi_return*100:.2f}%)")
        except Exception as e:
            print(f"⚠️ 시장 분석 실패: {e}")
            market_condition = None
        
        # V1 스캔
        print("🔄 V1 스캔 실행...")
        try:
            v1_results = scan_with_scanner(universe, {}, date, market_condition, version='v1')
            v1_count = len(v1_results)
            print(f"✅ V1 결과: {v1_count}개 종목")
        except Exception as e:
            print(f"❌ V1 스캔 실패: {e}")
            v1_results = []
            v1_count = 0
        
        # V2 스캔 (직접 사용)
        print("🔄 V2 스캔 실행...")
        try:
            from scanner_v2 import ScannerV2
            from scanner_v2.config_v2 import scanner_v2_config
            from config import config
            
            # V2 스캔 설정
            scanner_v2_config.market_analysis_enable = config.market_analysis_enable
            v2_scanner = ScannerV2(scanner_v2_config, market_analyzer)
            
            v2_scan_results = v2_scanner.scan(universe, date, market_condition)
            
            # ScanResult를 dict로 변환
            v2_results = []
            for r in v2_scan_results:
                v2_results.append({
                    "ticker": r.ticker,
                    "name": r.name,
                    "match": r.match,
                    "score": r.score,
                    "indicators": r.indicators.__dict__ if hasattr(r.indicators, '__dict__') else {},
                    "trend": r.trend.__dict__ if hasattr(r.trend, '__dict__') else {},
                    "strategy": r.strategy,
                    "flags": r.flags.__dict__ if hasattr(r.flags, '__dict__') else {},
                    "score_label": r.score_label,
                })
            
            v2_count = len(v2_results)
            print(f"✅ V2 결과: {v2_count}개 종목")
        except Exception as e:
            print(f"❌ V2 스캔 실패: {e}")
            import traceback
            traceback.print_exc()
            v2_results = []
            v2_count = 0
        
        # 결과 비교
        v1_tickers = set([r.get('ticker', '') for r in v1_results])
        v2_tickers = set([r.get('ticker', '') for r in v2_results])
        
        common = v1_tickers & v2_tickers
        v1_only = v1_tickers - v2_tickers
        v2_only = v2_tickers - v1_tickers
        
        results[date] = {
            'market_condition': {
                'sentiment': market_condition.market_sentiment if market_condition else None,
                'kospi_return': market_condition.kospi_return if market_condition else None
            },
            'v1_count': v1_count,
            'v2_count': v2_count,
            'common_count': len(common),
            'v1_only_count': len(v1_only),
            'v2_only_count': len(v2_only),
            'v1_tickers': list(v1_tickers),
            'v2_tickers': list(v2_tickers),
            'common_tickers': list(common),
            'v1_only_tickers': list(v1_only),
            'v2_only_tickers': list(v2_only)
        }
        
        print(f"📈 공통: {len(common)}개, V1만: {len(v1_only)}개, V2만: {len(v2_only)}개")
        
        # 장세 정보 DB 저장
        save_market_condition_to_db(date, market_condition)
        
        # 장세 정보 DB 저장 확인
        check_market_conditions_storage(date)
    
    # 결과 저장
    with open('/Users/rexsmac/workspace/stock-finder/v1_v2_comparison_nov.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n📊 비교 결과가 저장되었습니다: v1_v2_comparison_nov.json")
    return results

def check_market_conditions_storage(date):
    """장세 정보 저장 확인"""
    try:
        with db_manager.get_cursor(commit=False) as cur:
            cur.execute("""
                SELECT market_sentiment, kospi_return, rsi_threshold, 
                       foreign_flow, volume_trend, analysis_notes
                FROM market_conditions 
                WHERE date = %s
            """, (date,))
            row = cur.fetchone()
            
            if row:
                kospi_return = row[1] * 100 if row[1] else 0
                print(f"💾 장세 정보 저장됨: {row[0]} (KOSPI: {kospi_return:.2f}%, RSI: {row[2]})")
            else:
                print(f"❌ 장세 정보 저장 안됨: {date}")
                
    except Exception as e:
        print(f"⚠️ 장세 정보 확인 실패: {e}")

def save_market_condition_to_db(date, market_condition):
    """장세 정보를 DB에 저장"""
    if not market_condition:
        return
        
    try:
        from main import create_market_conditions_table
        import json
        
        with db_manager.get_cursor(commit=True) as cur:
            create_market_conditions_table(cur)
            cur.execute("""
                INSERT INTO market_conditions(
                    date, market_sentiment, sentiment_score, kospi_return, volatility, rsi_threshold,
                    sector_rotation, foreign_flow, volume_trend,
                    min_signals, macd_osc_min, vol_ma5_mult, gap_max, ext_from_tema20_max,
                    trend_metrics, breadth_metrics, flow_metrics, sector_metrics, volatility_metrics,
                    foreign_flow_label, volume_trend_label, adjusted_params, analysis_notes
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (date) DO UPDATE SET
                    market_sentiment = EXCLUDED.market_sentiment,
                    kospi_return = EXCLUDED.kospi_return,
                    rsi_threshold = EXCLUDED.rsi_threshold,
                    updated_at = NOW()
            """, (
                date,
                market_condition.market_sentiment,
                getattr(market_condition, 'sentiment_score', 0.0),
                market_condition.kospi_return,
                market_condition.volatility,
                market_condition.rsi_threshold,
                market_condition.sector_rotation,
                market_condition.foreign_flow,
                market_condition.volume_trend,
                market_condition.min_signals,
                market_condition.macd_osc_min,
                market_condition.vol_ma5_mult,
                market_condition.gap_max,
                market_condition.ext_from_tema20_max,
                json.dumps(getattr(market_condition, 'trend_metrics', {})),
                json.dumps(getattr(market_condition, 'breadth_metrics', {})),
                json.dumps(getattr(market_condition, 'flow_metrics', {})),
                json.dumps(getattr(market_condition, 'sector_metrics', {})),
                json.dumps(getattr(market_condition, 'volatility_metrics', {})),
                getattr(market_condition, 'foreign_flow_label', market_condition.foreign_flow),
                getattr(market_condition, 'volume_trend_label', market_condition.volume_trend),
                json.dumps(getattr(market_condition, 'adjusted_params', {})),
                getattr(market_condition, 'analysis_notes', '')
            ))
        print(f"💾 장세 정보 저장 완료: {date}")
    except Exception as e:
        print(f"⚠️ 장세 정보 저장 실패: {e}")

if __name__ == "__main__":
    print("🚀 11월 V1/V2 스캔 비교 테스트 시작")
    results = test_november_scans()
    
    # 요약 출력
    print("\n📋 전체 요약:")
    for date, data in results.items():
        print(f"{date}: V1({data['v1_count']}) vs V2({data['v2_count']}) - 공통({data['common_count']})")
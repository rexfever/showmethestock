#!/usr/bin/env python3
"""10월 27일부터 31일까지 스캔 실행 및 성과 분석 (서버용)"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.scan_service import execute_scan_with_fallback
from services.returns_service import calculate_returns_batch
from kiwoom_api import api
from config import config
from market_analyzer import market_analyzer
from datetime import datetime
import json

def run_scan_and_analyze(date_str: str):
    """특정 날짜로 스캔 실행 및 성과 분석"""
    print(f"\n{'='*60}")
    print(f"📅 {date_str} 스캔 실행 중...")
    print(f"{'='*60}")
    
    try:
        # 유니버스 가져오기
        universe = api.get_top_codes('KOSPI', config.universe_kospi) + api.get_top_codes('KOSDAQ', config.universe_kosdaq)
        
        # 장세 분석
        market_condition = None
        if config.market_analysis_enable:
            try:
                market_analyzer.clear_cache()
                market_condition = market_analyzer.analyze_market_condition(date_str)
                print(f"📊 시장 상황: {market_condition.market_sentiment} (KOSPI: {market_condition.kospi_return*100:+.2f}%)")
            except Exception as e:
                print(f"⚠️ 시장 분석 실패: {e}")
        
        # 스캔 실행
        items, chosen_step = execute_scan_with_fallback(universe, date_str, market_condition)
        print(f"✅ 스캔 완료: {len(items)}개 종목 발견 (Step: {chosen_step})")
        
        if not items:
            return {
                'date': date_str,
                'matched_count': 0,
                'items': [],
                'performance': {
                    'total_items': 0,
                    'items_with_returns': 0,
                    'win_rate': 0.0,
                    'avg_return': 0.0
                },
                'success': True
            }
        
        # 수익률 계산
        tickers = [item["ticker"] for item in items]
        print(f"💰 수익률 계산 시작: {len(tickers)}개 종목")
        
        current_date = datetime.now().strftime('%Y%m%d')
        returns_data = calculate_returns_batch(tickers, date_str, current_date)
        print(f"💰 수익률 계산 완료: {len(returns_data)}개 결과")
        
        # 성과 분석
        items_with_returns = []
        for item in items:
            ticker = item.get('ticker')
            if ticker in returns_data and returns_data[ticker]:
                ret = returns_data[ticker]
                items_with_returns.append({
                    'ticker': ticker,
                    'name': item.get('name', 'N/A'),
                    'score': item.get('score', 0),
                    'current_return': ret['current_return'],
                    'max_return': ret['max_return'],
                    'min_return': ret['min_return'],
                    'days_elapsed': ret.get('days_elapsed', 0)
                })
        
        # 승률 계산 (3% 이상 익절 기준)
        wins = sum(1 for item in items_with_returns if item['max_return'] >= 0.03)
        win_rate = (wins / len(items_with_returns)) * 100 if items_with_returns else 0.0
        
        # 평균 수익률
        avg_return = sum(item['current_return'] for item in items_with_returns) / len(items_with_returns) * 100 if items_with_returns else 0.0
        max_return = max(item['max_return'] for item in items_with_returns) * 100 if items_with_returns else 0.0
        min_return = min(item['min_return'] for item in items_with_returns) * 100 if items_with_returns else 0.0
        
        performance = {
            'total_items': len(items),
            'items_with_returns': len(items_with_returns),
            'win_rate': win_rate,
            'avg_return': avg_return,
            'max_return': max_return,
            'min_return': min_return,
            'wins': wins,
            'losses': len(items_with_returns) - wins
        }
        
        print(f"\n📊 성과 분석:")
        print(f"  - 추천 종목: {performance['total_items']}개")
        print(f"  - 수익률 데이터: {performance['items_with_returns']}개")
        print(f"  - 승률 (3% 이상): {performance['win_rate']:.2f}%")
        print(f"  - 평균 수익률: {performance['avg_return']:.2f}%")
        print(f"  - 최대 수익률: {performance['max_return']:.2f}%")
        print(f"  - 최소 수익률: {performance['min_return']:.2f}%")
        
        return {
            'date': date_str,
            'matched_count': len(items),
            'items': items_with_returns,
            'performance': performance,
            'market_sentiment': market_condition.market_sentiment if market_condition else None,
            'chosen_step': chosen_step,
            'success': True
        }
        
    except Exception as e:
        print(f"❌ 스캔 실패: {e}")
        import traceback
        traceback.print_exc()
        return {
            'date': date_str,
            'matched_count': 0,
            'items': [],
            'success': False,
            'error': str(e)
        }

def main():
    """메인 실행 함수"""
    dates = ['20251027', '20251028', '20251029', '20251030', '20251031']
    
    results = []
    
    for date_str in dates:
        result = run_scan_and_analyze(date_str)
        results.append(result)
    
    # 전체 요약
    print(f"\n{'='*60}")
    print(f"📈 전체 기간 요약 (10월 27일 ~ 31일)")
    print(f"{'='*60}")
    
    total_items = sum(r['matched_count'] for r in results if r['success'])
    total_with_returns = sum(r.get('performance', {}).get('items_with_returns', 0) for r in results)
    total_wins = sum(r.get('performance', {}).get('wins', 0) for r in results)
    total_losses = sum(r.get('performance', {}).get('losses', 0) for r in results)
    
    overall_win_rate = (total_wins / total_with_returns * 100) if total_with_returns > 0 else 0.0
    
    avg_returns = [r.get('performance', {}).get('avg_return', 0) for r in results if r.get('performance', {}).get('items_with_returns', 0) > 0]
    overall_avg_return = sum(avg_returns) / len(avg_returns) if avg_returns else 0.0
    
    print(f"\n📊 전체 통계:")
    print(f"  - 총 추천 종목: {total_items}개")
    print(f"  - 수익률 데이터: {total_with_returns}개")
    print(f"  - 승 (3% 이상): {total_wins}개")
    print(f"  - 패: {total_losses}개")
    print(f"  - 전체 승률: {overall_win_rate:.2f}%")
    print(f"  - 평균 수익률: {overall_avg_return:.2f}%")
    
    # 날짜별 상세
    print(f"\n📅 날짜별 상세:")
    for result in results:
        date = result['date']
        if result['success']:
            perf = result.get('performance', {})
            market = result.get('market_sentiment', 'N/A')
            step = result.get('chosen_step', 'N/A')
            print(f"\n  {date} ({market}, Step {step}):")
            print(f"    - 추천: {perf.get('total_items', 0)}개")
            print(f"    - 수익률 데이터: {perf.get('items_with_returns', 0)}개")
            print(f"    - 승률: {perf.get('win_rate', 0):.2f}%")
            print(f"    - 평균 수익률: {perf.get('avg_return', 0):.2f}%")
        else:
            print(f"\n  {date}: 스캔 실패 - {result.get('error', '알 수 없는 오류')}")
    
    # 결과를 파일로 저장
    output_file = "/home/ubuntu/showmethestock/backend/OCTOBER_SCAN_ANALYSIS_20251027_20251031.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"\n✅ 결과 저장: {output_file}")

if __name__ == '__main__':
    main()


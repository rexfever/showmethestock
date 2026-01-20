#!/usr/bin/env python3
"""10월 27일부터 31일까지 스캔 실행 및 성과 분석 (서버 API 호출)"""

import requests
import json
from datetime import datetime
from typing import Dict, List, Any

# 서버 URL (서버 내부에서 실행 시 localhost 사용)
import os
if os.getenv('SSH_CONNECTION'):
    SERVER_URL = "http://localhost:8010"
else:
    SERVER_URL = "http://52.79.145.238:8010"

def run_scan_for_date(date_str: str) -> Dict[str, Any]:
    """특정 날짜로 스캔 실행"""
    url = f"{SERVER_URL}/scan"
    params = {
        "date": date_str,
        "save_snapshot": True,
        "kospi_limit": 200,
        "kosdaq_limit": 200
    }
    
    print(f"\n{'='*60}")
    print(f"📅 {date_str} 스캔 실행 중...")
    print(f"{'='*60}")
    
    try:
        response = requests.get(url, params=params, timeout=600)
        response.raise_for_status()
        data = response.json()
        
        matched_count = data.get('matched_count', 0)
        items = data.get('items', [])
        market_condition = data.get('market_condition', {})
        chosen_step = data.get('chosen_step')
        
        print(f"✅ 스캔 완료: {matched_count}개 종목 발견")
        if market_condition:
            sentiment = market_condition.get('market_sentiment', 'N/A')
            kospi_return = market_condition.get('kospi_return', 0) * 100
            print(f"📊 시장 상황: {sentiment} (KOSPI: {kospi_return:+.2f}%)")
        if chosen_step is not None:
            print(f"🔄 Fallback Step: {chosen_step}")
        
        return {
            'date': date_str,
            'matched_count': matched_count,
            'items': items,
            'market_condition': market_condition,
            'chosen_step': chosen_step,
            'success': True
        }
    except Exception as e:
        print(f"❌ 스캔 실패: {e}")
        return {
            'date': date_str,
            'matched_count': 0,
            'items': [],
            'success': False,
            'error': str(e)
        }

def analyze_performance(items: List[Dict], scan_date: str) -> Dict[str, Any]:
    """스캔 결과의 성과 분석"""
    if not items:
        return {
            'total_items': 0,
            'items_with_returns': 0,
            'win_rate': 0.0,
            'avg_return': 0.0,
            'max_return': 0.0,
            'min_return': 0.0
        }
    
    items_with_returns = []
    for item in items:
        returns = item.get('returns', {})
        if returns:
            current_return = returns.get('current_return', 0)
            max_return = returns.get('max_return', 0)
            min_return = returns.get('min_return', 0)
            
            items_with_returns.append({
                'ticker': item.get('ticker'),
                'name': item.get('name'),
                'score': item.get('score', 0),
                'current_return': current_return,
                'max_return': max_return,
                'min_return': min_return,
                'days_elapsed': returns.get('days_elapsed', 0)
            })
    
    if not items_with_returns:
        return {
            'total_items': len(items),
            'items_with_returns': 0,
            'win_rate': 0.0,
            'avg_return': 0.0,
            'max_return': 0.0,
            'min_return': 0.0
        }
    
    # 승률 계산 (3% 이상 익절 기준)
    wins = sum(1 for item in items_with_returns if item['max_return'] >= 0.03)
    win_rate = (wins / len(items_with_returns)) * 100 if items_with_returns else 0.0
    
    # 평균 수익률
    avg_return = sum(item['current_return'] for item in items_with_returns) / len(items_with_returns) * 100
    max_return = max(item['max_return'] for item in items_with_returns) * 100
    min_return = min(item['min_return'] for item in items_with_returns) * 100
    
    return {
        'total_items': len(items),
        'items_with_returns': len(items_with_returns),
        'win_rate': win_rate,
        'avg_return': avg_return,
        'max_return': max_return,
        'min_return': min_return,
        'wins': wins,
        'losses': len(items_with_returns) - wins
    }

def main():
    """메인 실행 함수"""
    dates = ['20251027', '20251028', '20251029', '20251030', '20251031']
    
    results = []
    
    for date_str in dates:
        # 스캔 실행
        scan_result = run_scan_for_date(date_str)
        
        if scan_result['success']:
            # 성과 분석
            performance = analyze_performance(scan_result['items'], date_str)
            scan_result['performance'] = performance
            
            print(f"\n📊 성과 분석:")
            print(f"  - 추천 종목: {performance['total_items']}개")
            print(f"  - 수익률 데이터: {performance['items_with_returns']}개")
            print(f"  - 승률 (3% 이상): {performance['win_rate']:.2f}%")
            print(f"  - 평균 수익률: {performance['avg_return']:.2f}%")
            print(f"  - 최대 수익률: {performance['max_return']:.2f}%")
            print(f"  - 최소 수익률: {performance['min_return']:.2f}%")
        
        results.append(scan_result)
    
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
            market = result.get('market_condition', {}).get('market_sentiment', 'N/A')
            step = result.get('chosen_step', 'N/A')
            print(f"\n  {date} ({market}, Step {step}):")
            print(f"    - 추천: {perf.get('total_items', 0)}개")
            print(f"    - 수익률 데이터: {perf.get('items_with_returns', 0)}개")
            print(f"    - 승률: {perf.get('win_rate', 0):.2f}%")
            print(f"    - 평균 수익률: {perf.get('avg_return', 0):.2f}%")
        else:
            print(f"\n  {date}: 스캔 실패 - {result.get('error', '알 수 없는 오류')}")
    
    # 결과를 파일로 저장
    output_file = "backend/OCTOBER_SCAN_ANALYSIS_20251027_20251031.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"\n✅ 결과 저장: {output_file}")
    
    return results

if __name__ == '__main__':
    main()


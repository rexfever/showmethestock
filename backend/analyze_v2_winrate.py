#!/usr/bin/env python3
"""
V2 스캔 종목의 승률 분석 스크립트
진입일 기준 5일 후, 10일 후 수익률 계산 및 승률 분석
"""

import json
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pandas as pd

# 로컬 모듈 import
sys.path.insert(0, '/Users/rexsmac/workspace/stock-finder/backend')
from data_loader import load_price_data
from kiwoom_api import api


def get_exit_price(symbol: str, entry_date: str, days: int) -> Optional[float]:
    """
    진입일 기준 N일 후의 종가를 가져옵니다.
    주말을 고려하여 실제 거래일 기준으로 계산합니다.
    """
    try:
        entry_dt = datetime.strptime(entry_date, '%Y-%m-%d')
        # 주말을 포함하여 충분한 날짜 계산 (거래일 5일 = 캘린더일 약 7일)
        end_date = entry_dt + timedelta(days=days * 1.5 + 10)
        start_date = entry_dt - timedelta(days=5)  # 버퍼 포함
        
        # OHLCV 데이터 가져오기
        df = load_price_data(
            symbol,
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            cache=True
        )
        
        if df is None or df.empty:
            return None
        
        # 날짜 컬럼 확인
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
        elif df.index.name == 'date' or isinstance(df.index, pd.DatetimeIndex):
            df = df.reset_index()
            df['date'] = pd.to_datetime(df['date'])
        
        # 진입일 이후 데이터만 필터링
        df_filtered = df[df['date'] > entry_dt].copy()
        
        if df_filtered.empty:
            return None
        
        # 거래일 기준으로 정렬 후 N번째 거래일 가격
        df_filtered = df_filtered.sort_values('date')
        
        # 거래량이 있는 것만 (실제 거래일)
        if 'volume' in df_filtered.columns:
            df_filtered = df_filtered[df_filtered['volume'] > 0]
        
        if df_filtered.empty:
            return None
        
        # N일 후 (days 거래일)
        if len(df_filtered) >= days:
            exit_price = df_filtered.iloc[days - 1]['close']
            return float(exit_price)
        else:
            # 데이터가 부족한 경우 마지막 가격
            exit_price = df_filtered.iloc[-1]['close']
            return float(exit_price)
            
    except Exception as e:
        print(f"   ⚠️  {symbol} 가격 조회 실패: {e}", file=sys.stderr)
        return None


def analyze_winrate(v2_trades: List[Dict]) -> Dict:
    """V2 트레이드 승률 분석"""
    print("=" * 70)
    print("📊 V2 종목 승률 분석 시작")
    print("=" * 70)
    print()
    
    results_5d = []
    results_10d = []
    
    total = len(v2_trades)
    print(f"📈 총 {total}개 트레이드 분석 중...")
    print()
    
    for idx, trade in enumerate(v2_trades, 1):
        date = trade['date']
        code = trade['code']
        name = trade['name']
        entry_price = trade['entry_price']
        score = trade.get('score', 0)
        
        if not entry_price or entry_price <= 0:
            continue
        
        # 5일 후 가격
        exit_5d_price = get_exit_price(code, date, 5)
        if exit_5d_price:
            return_5d = (exit_5d_price - entry_price) / entry_price * 100
            results_5d.append({
                'date': date,
                'code': code,
                'name': name,
                'score': score,
                'entry_price': entry_price,
                'exit_5d_price': exit_5d_price,
                'return_5d': return_5d,
                'win': return_5d > 0
            })
        
        # 10일 후 가격
        exit_10d_price = get_exit_price(code, date, 10)
        if exit_10d_price:
            return_10d = (exit_10d_price - entry_price) / entry_price * 100
            results_10d.append({
                'date': date,
                'code': code,
                'name': name,
                'score': score,
                'entry_price': entry_price,
                'exit_10d_price': exit_10d_price,
                'return_10d': return_10d,
                'win': return_10d > 0
            })
        
        if idx % 20 == 0:
            print(f"   진행 중: {idx}/{total}... ({len(results_5d)}개 5일 후, {len(results_10d)}개 10일 후)")
    
    print()
    print("=" * 70)
    print("📊 승률 분석 결과")
    print("=" * 70)
    print()
    
    # 5일 후 승률
    stats_5d = {}
    if results_5d:
        wins_5d = sum(1 for r in results_5d if r['win'])
        total_5d = len(results_5d)
        win_rate_5d = wins_5d / total_5d * 100
        avg_return_5d = sum(r['return_5d'] for r in results_5d) / total_5d
        max_return_5d = max(r['return_5d'] for r in results_5d)
        min_return_5d = min(r['return_5d'] for r in results_5d)
        
        stats_5d = {
            'total': total_5d,
            'wins': wins_5d,
            'losses': total_5d - wins_5d,
            'win_rate': win_rate_5d,
            'avg_return': avg_return_5d,
            'max_return': max_return_5d,
            'min_return': min_return_5d
        }
        
        print(f"📈 5일 후 승률:")
        print(f"   총 트레이드: {total_5d}개")
        print(f"   승리: {wins_5d}개")
        print(f"   패배: {total_5d - wins_5d}개")
        print(f"   승률: {win_rate_5d:.2f}%")
        print(f"   평균 수익률: {avg_return_5d:.2f}%")
        print(f"   최대 수익률: {max_return_5d:.2f}%")
        print(f"   최소 수익률: {min_return_5d:.2f}%")
        print()
    
    # 10일 후 승률
    stats_10d = {}
    if results_10d:
        wins_10d = sum(1 for r in results_10d if r['win'])
        total_10d = len(results_10d)
        win_rate_10d = wins_10d / total_10d * 100
        avg_return_10d = sum(r['return_10d'] for r in results_10d) / total_10d
        max_return_10d = max(r['return_10d'] for r in results_10d)
        min_return_10d = min(r['return_10d'] for r in results_10d)
        
        stats_10d = {
            'total': total_10d,
            'wins': wins_10d,
            'losses': total_10d - wins_10d,
            'win_rate': win_rate_10d,
            'avg_return': avg_return_10d,
            'max_return': max_return_10d,
            'min_return': min_return_10d
        }
        
        print(f"📈 10일 후 승률:")
        print(f"   총 트레이드: {total_10d}개")
        print(f"   승리: {wins_10d}개")
        print(f"   패배: {total_10d - wins_10d}개")
        print(f"   승률: {win_rate_10d:.2f}%")
        print(f"   평균 수익률: {avg_return_10d:.2f}%")
        print(f"   최대 수익률: {max_return_10d:.2f}%")
        print(f"   최소 수익률: {min_return_10d:.2f}%")
        print()
    
    # 점수별 승률 분석
    print("=" * 70)
    print("📊 점수별 승률 분석 (5일 후)")
    print("=" * 70)
    print()
    
    if results_5d:
        score_groups = {}
        for r in results_5d:
            score_range = f"{int(r['score'])}"
            if score_range not in score_groups:
                score_groups[score_range] = []
            score_groups[score_range].append(r)
        
        for score in sorted(score_groups.keys(), reverse=True):
            group = score_groups[score]
            wins = sum(1 for r in group if r['win'])
            total = len(group)
            win_rate = wins / total * 100
            avg_return = sum(r['return_5d'] for r in group) / total
            
            print(f"   점수 {score}점: {total}개, 승률 {win_rate:.2f}%, 평균 수익률 {avg_return:.2f}%")
        print()
    
    return {
        'stats_5d': stats_5d,
        'stats_10d': stats_10d,
        'results_5d': results_5d,
        'results_10d': results_10d
    }


def main():
    # 서버에서 가져온 V2 데이터 읽기
    print("📥 V2 트레이드 데이터 로딩 중...")
    
    # SSH로 서버에서 데이터 가져오기
    import subprocess
    result = subprocess.run(
        ['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=10',
         'ubuntu@52.79.145.238', 'cd /home/ubuntu/showmethestock/backend && source venv/bin/activate 2>/dev/null || true && python3 << \'PYEOF\'\nimport sys\nimport json\nsys.path.insert(0, \'/home/ubuntu/showmethestock/backend\')\nfrom db_manager import db_manager\nwith db_manager.get_cursor(commit=False) as cur:\n    cur.execute(\'\'\'\n        SELECT date, code, name, score, close_price, details\n        FROM scan_rank\n        WHERE scanner_version = \'v2\'\n        AND close_price IS NOT NULL AND close_price > 0\n        ORDER BY date ASC, score DESC\n    \'\'\')\n    trades = cur.fetchall()\n    results = []\n    for row in trades:\n        results.append({\n            \'date\': row[0].strftime(\'%Y-%m-%d\') if row[0] else None,\n            \'code\': row[1], \'name\': row[2],\n            \'score\': float(row[3]) if row[3] else None,\n            \'entry_price\': float(row[4]) if row[4] else None,\n            \'details\': row[5]\n        })\n    print(json.dumps(results, ensure_ascii=False, default=str))\nPYEOF'],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"❌ 서버 데이터 로딩 실패: {result.stderr}")
        return
    
    try:
        v2_trades = json.loads(result.stdout.strip())
        print(f"✅ {len(v2_trades)}개 트레이드 데이터 로드 완료")
        print()
    except json.JSONDecodeError as e:
        print(f"❌ JSON 파싱 실패: {e}")
        print(f"출력: {result.stdout[:500]}")
        return
    
    # 승률 분석
    analysis = analyze_winrate(v2_trades)
    
    # 결과 저장
    output_file = '/Users/rexsmac/workspace/stock-finder/backend/v2_winrate_analysis.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"✅ 결과 저장: {output_file}")


if __name__ == '__main__':
    main()


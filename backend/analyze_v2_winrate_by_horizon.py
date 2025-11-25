#!/usr/bin/env python3
"""
V2 스캔 종목의 Horizon별(스윙/포지션/롱텀) 승률 분석 스크립트
final_output JSON 파일에서 horizon 정보를 추출하여 분석
"""

import json
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pandas as pd
from pathlib import Path
import glob

sys.path.insert(0, '/Users/rexsmac/workspace/stock-finder/backend')
from data_loader import load_price_data


def get_exit_price(symbol: str, entry_date: str, days: int) -> Optional[float]:
    """
    진입일 기준 N일 후의 종가를 가져옵니다.
    """
    try:
        entry_dt = datetime.strptime(entry_date, '%Y%m%d')
        end_date = entry_dt + timedelta(days=days * 1.5 + 10)
        start_date = entry_dt - timedelta(days=5)
        
        df = load_price_data(
            symbol,
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            cache=True
        )
        
        if df is None or df.empty:
            return None
        
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
        elif df.index.name == 'date' or isinstance(df.index, pd.DatetimeIndex):
            df = df.reset_index()
            df['date'] = pd.to_datetime(df['date'])
        
        df_filtered = df[df['date'] > entry_dt].copy()
        
        if df_filtered.empty:
            return None
        
        df_filtered = df_filtered.sort_values('date')
        
        if 'volume' in df_filtered.columns:
            df_filtered = df_filtered[df_filtered['volume'] > 0]
        
        if df_filtered.empty:
            return None
        
        if len(df_filtered) >= days:
            exit_price = df_filtered.iloc[days - 1]['close']
            return float(exit_price)
        else:
            exit_price = df_filtered.iloc[-1]['close']
            return float(exit_price)
            
    except Exception as e:
        return None


def load_final_output_files(data_dir: str) -> List[Dict]:
    """final_output JSON 파일들을 로드"""
    data_path = Path(data_dir)
    files = sorted(data_path.glob('final_output_*.json'))
    
    all_results = []
    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                all_results.append(data)
        except Exception as e:
            print(f"⚠️  {file_path.name} 로딩 실패: {e}")
            continue
    
    return all_results


def analyze_by_horizon(final_outputs: List[Dict], horizon: str, hold_days: int):
    """특정 Horizon의 승률 분석"""
    trades = []
    
    for result in final_outputs:
        date = result.get('date', '')
        candidates_key = f'{horizon}_candidates'
        candidates = result.get(candidates_key, [])
        
        for candidate in candidates:
            symbol = candidate.get('symbol', '')
            score = candidate.get('score', 0)
            risk_score = candidate.get('risk_score', 0)
            
            # 진입일 당일 종가를 진입가로 사용 (다음날 시가는 나중에 개선)
            try:
                entry_date_dt = datetime.strptime(date, '%Y%m%d')
                
                # 당일 종가를 진입가로 사용
                entry_df = load_price_data(
                    symbol,
                    start_date=entry_date_dt.strftime('%Y-%m-%d'),
                    end_date=(entry_date_dt + timedelta(days=2)).strftime('%Y-%m-%d'),
                    cache=True
                )
                
                if entry_df is None or entry_df.empty:
                    continue
                
                entry_df['date'] = pd.to_datetime(entry_df['date'])
                entry_row = entry_df[entry_df['date'] == pd.Timestamp(entry_date_dt)]
                
                if entry_row.empty:
                    continue
                
                entry_price = float(entry_row.iloc[0]['close'])
                
                if not entry_price or entry_price <= 0:
                    continue
                
                # N일 후 가격
                exit_price = get_exit_price(symbol, date, hold_days)
                
                if exit_price:
                    return_pct = (exit_price - entry_price) / entry_price * 100
                    trades.append({
                        'date': date,
                        'symbol': symbol,
                        'score': score,
                        'risk_score': risk_score,
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'return_pct': return_pct,
                        'win': return_pct > 0
                    })
            except Exception as e:
                continue
    
    return trades


def analyze_winrate_by_horizon():
    """Horizon별 승률 분석"""
    data_dir = '/Users/rexsmac/workspace/stock-finder/backend/scanner_v2/data'
    
    print("=" * 70)
    print("📊 V2 Horizon별 승률 분석")
    print("=" * 70)
    print()
    
    # final_output 파일들 로드
    print("📥 final_output JSON 파일 로딩 중...")
    final_outputs = load_final_output_files(data_dir)
    print(f"✅ {len(final_outputs)}개 파일 로드 완료")
    print()
    
    # Horizon별 분석
    horizons = {
        'swing': 5,      # 5일 보유
        'position': 10,  # 10일 보유
        'longterm': 20   # 20일 보유
    }
    
    all_stats = {}
    
    for horizon, hold_days in horizons.items():
        print(f"📈 {horizon.upper()} Horizon 분석 중... (보유기간: {hold_days}일)")
        trades = analyze_by_horizon(final_outputs, horizon, hold_days)
        
        if not trades:
            print(f"   ⚠️  {horizon} 데이터가 없습니다.")
            print()
            continue
        
        wins = sum(1 for t in trades if t['win'])
        total = len(trades)
        win_rate = wins / total * 100
        avg_return = sum(t['return_pct'] for t in trades) / total
        max_return = max(t['return_pct'] for t in trades)
        min_return = min(t['return_pct'] for t in trades)
        
        stats = {
            'horizon': horizon,
            'hold_days': hold_days,
            'total': total,
            'wins': wins,
            'losses': total - wins,
            'win_rate': win_rate,
            'avg_return': avg_return,
            'max_return': max_return,
            'min_return': min_return,
            'trades': trades
        }
        all_stats[horizon] = stats
        
        print(f"   총 트레이드: {total}개")
        print(f"   승리: {wins}개")
        print(f"   패배: {total - wins}개")
        print(f"   승률: {win_rate:.2f}%")
        print(f"   평균 수익률: {avg_return:.2f}%")
        print(f"   최대 수익률: {max_return:.2f}%")
        print(f"   최소 수익률: {min_return:.2f}%")
        print()
    
    # 요약 출력
    print("=" * 70)
    print("📊 Horizon별 승률 비교")
    print("=" * 70)
    print()
    
    print(f"{'Horizon':<12} {'보유기간':<10} {'총계':<8} {'승리':<8} {'승률':<10} {'평균수익률':<12} {'최대':<10} {'최소':<10}")
    print("-" * 70)
    
    for horizon in ['swing', 'position', 'longterm']:
        if horizon in all_stats:
            stats = all_stats[horizon]
            print(f"{horizon:<12} {stats['hold_days']}일{'':<6} "
                  f"{stats['total']:<8} {stats['wins']:<8} "
                  f"{stats['win_rate']:<10.2f} {stats['avg_return']:<12.2f} "
                  f"{stats['max_return']:<10.2f} {stats['min_return']:<10.2f}")
    
    # 결과 저장
    output_file = '/Users/rexsmac/workspace/stock-finder/backend/v2_winrate_by_horizon.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_stats, f, ensure_ascii=False, indent=2, default=str)
    
    print()
    print(f"✅ 결과 저장: {output_file}")


if __name__ == '__main__':
    analyze_winrate_by_horizon()


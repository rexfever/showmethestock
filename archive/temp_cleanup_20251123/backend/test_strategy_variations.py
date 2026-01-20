#!/usr/bin/env python3
"""
매매 전략 파라미터 조합 비교 분석
"""
import subprocess
import sys
from datetime import datetime

def test_strategy_combination(name, stop_loss, take_profit, preserve, max_days=60):
    """전략 조합 테스트"""
    print(f"\n{'='*80}")
    print(f"테스트: {name}")
    print(f"손절: {stop_loss}%, 익절: {take_profit}%, 보존: {preserve}%")
    print(f"{'='*80}")
    
    cmd = [
        sys.executable, 
        "validate_trading_strategy.py",
        "--stop-loss", str(stop_loss),
        "--take-profit", str(take_profit),
        "--preserve", str(preserve),
        "--max-days", str(max_days),
        "--max-stocks", "100"  # 빠른 테스트를 위해 100개만
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    
    # 결과 파싱
    output = result.stdout
    lines = output.split('\n')
    
    stats = {}
    for i, line in enumerate(lines):
        if '총 검증:' in line:
            try:
                stats['total'] = int(line.split('총 검증:')[1].split('개')[0].strip())
            except:
                pass
        elif '익절:' in line and '%' in line:
            try:
                stats['take_profit_count'] = int(line.split('익절:')[1].split('개')[0].strip())
                stats['take_profit_pct'] = float(line.split('(')[1].split('%')[0])
            except:
                pass
        elif '손절:' in line and '%' in line:
            try:
                stats['stop_loss_count'] = int(line.split('손절:')[1].split('개')[0].strip())
                stats['stop_loss_pct'] = float(line.split('(')[1].split('%')[0])
            except:
                pass
        elif '보존:' in line and '%' in line:
            try:
                stats['preserve_count'] = int(line.split('보존:')[1].split('개')[0].strip())
                stats['preserve_pct'] = float(line.split('(')[1].split('%')[0])
            except:
                pass
        elif '평균 수익률:' in line:
            try:
                stats['avg_return'] = float(line.split('평균 수익률:')[1].split('%')[0].strip())
            except:
                pass
        elif '승률:' in line and '%' in line:
            try:
                stats['win_rate'] = float(line.split('승률:')[1].split('%')[0].strip())
            except:
                pass
        elif '평균 보유 기간:' in line:
            try:
                stats['avg_days'] = float(line.split('평균 보유 기간:')[1].split('일')[0].strip())
            except:
                pass
    
    stats['name'] = name
    stats['stop_loss'] = stop_loss
    stats['take_profit'] = take_profit
    stats['preserve'] = preserve
    
    return stats

if __name__ == "__main__":
    # 다양한 전략 조합 테스트
    strategies = [
        # 원본
        ("원본", -5.0, 8.0, 3.0),
        
        # 손절 완화 (더 관대한 손절)
        ("손절 완화 1", -7.0, 8.0, 3.0),
        ("손절 완화 2", -10.0, 8.0, 3.0),
        
        # 익절 완화 (더 빠른 익절)
        ("익절 완화 1", -5.0, 6.0, 3.0),
        ("익절 완화 2", -5.0, 5.0, 3.0),
        ("익절 완화 3", -5.0, 4.0, 3.0),
        ("익절 완화 4", -5.0, 3.0, 3.0),
        
        # 보존 완화 (더 빠른 보존)
        ("보존 완화 1", -5.0, 8.0, 2.0),
        ("보존 완화 2", -5.0, 8.0, 1.0),
        
        # 조합 1: 손절 완화 + 익절 완화
        ("조합 1", -7.0, 6.0, 3.0),
        ("조합 2", -7.0, 5.0, 3.0),
        ("조합 3", -7.0, 4.0, 3.0),
        
        # 조합 2: 손절 완화 + 보존 완화
        ("조합 4", -7.0, 8.0, 2.0),
        ("조합 5", -7.0, 8.0, 1.0),
        
        # 조합 3: 익절 완화 + 보존 완화
        ("조합 6", -5.0, 5.0, 2.0),
        ("조합 7", -5.0, 4.0, 2.0),
        ("조합 8", -5.0, 3.0, 2.0),
        
        # 조합 4: 모두 완화
        ("조합 9", -7.0, 5.0, 2.0),
        ("조합 10", -7.0, 4.0, 2.0),
        ("조합 11", -7.0, 3.0, 2.0),
        ("조합 12", -10.0, 5.0, 3.0),
        ("조합 13", -10.0, 4.0, 2.0),
        
        # 극단적 완화
        ("극단 1", -10.0, 3.0, 1.0),
        ("극단 2", -10.0, 2.0, 1.0),
    ]
    
    results = []
    
    print("\n" + "="*80)
    print("매매 전략 파라미터 조합 비교 분석")
    print("="*80)
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    for name, stop_loss, take_profit, preserve in strategies:
        try:
            stats = test_strategy_combination(name, stop_loss, take_profit, preserve)
            results.append(stats)
        except Exception as e:
            print(f"오류: {name} - {e}")
            continue
    
    # 결과 요약
    print("\n" + "="*80)
    print("결과 요약 (익절률 기준 정렬)")
    print("="*80)
    print(f"{'전략명':<15} {'손절':<8} {'익절':<8} {'보존':<8} {'익절':<8} {'손절':<8} {'평균수익':<10} {'승률':<8} {'보유일':<8}")
    print("-"*80)
    
    # 익절률이 있는 것만 필터링하고 정렬
    with_profit = [r for r in results if r.get('take_profit_count', 0) > 0]
    without_profit = [r for r in results if r.get('take_profit_count', 0) == 0]
    
    # 익절률 기준 정렬
    with_profit.sort(key=lambda x: (x.get('take_profit_pct', 0), x.get('avg_return', -999)), reverse=True)
    
    for r in with_profit:
        print(f"{r.get('name', 'N/A'):<15} "
              f"{r.get('stop_loss', 0):>6.1f}% "
              f"{r.get('take_profit', 0):>6.1f}% "
              f"{r.get('preserve', 0):>6.1f}% "
              f"{r.get('take_profit_pct', 0):>6.1f}% "
              f"{r.get('stop_loss_pct', 0):>6.1f}% "
              f"{r.get('avg_return', 0):>8.2f}% "
              f"{r.get('win_rate', 0):>6.1f}% "
              f"{r.get('avg_days', 0):>6.1f}일")
    
    print("\n익절 없는 전략 (평균 수익률 기준 정렬):")
    without_profit.sort(key=lambda x: x.get('avg_return', -999), reverse=True)
    for r in without_profit[:5]:  # 상위 5개만
        print(f"{r.get('name', 'N/A'):<15} "
              f"{r.get('stop_loss', 0):>6.1f}% "
              f"{r.get('take_profit', 0):>6.1f}% "
              f"{r.get('preserve', 0):>6.1f}% "
              f"{r.get('take_profit_pct', 0):>6.1f}% "
              f"{r.get('stop_loss_pct', 0):>6.1f}% "
              f"{r.get('avg_return', 0):>8.2f}% "
              f"{r.get('win_rate', 0):>6.1f}% "
              f"{r.get('avg_days', 0):>6.1f}일")
    
    print(f"\n완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


"""
승률 계산 상세 분석
3% 익절 기준의 실제 의미 분석
"""
import sys
import os
from datetime import datetime, timedelta
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from calculate_win_rate_improved import get_recent_scan_results
from services.returns_service import calculate_returns_batch
import time


def analyze_win_rate_detailed(returns_data, take_profit_pct=3.0, stop_loss_pct=-7.0, preserve_pct=1.5, min_hold_days=5, max_hold_days=45, min_days_for_validation=10):
    """
    승률 상세 분석
    """
    if not returns_data:
        return None
    
    # 보유 기간이 충분한 종목만 필터링
    validated_returns = [r for r in returns_data if r.get('days_elapsed', 0) >= min_days_for_validation]
    
    if not validated_returns:
        return None
    
    # 카테고리별 분류
    take_profit_actual = []  # 실제로 3% 이상 도달했고, 현재도 3% 이상
    take_profit_missed = []  # 3% 이상 도달했지만, 현재는 3% 미만
    stop_loss_actual = []    # 실제로 -7% 이하 하락
    preserve_actual = []      # 보존 조건 충족
    unresolved = []          # 아직 판단 불가
    
    for ret in validated_returns:
        days = ret.get('days_elapsed', 0)
        max_ret = ret.get('max_return', 0)
        min_ret = ret.get('min_return', 0)
        current_ret = ret.get('current_return', 0)
        
        # 익절: +3% 도달
        if max_ret >= take_profit_pct:
            if current_ret >= take_profit_pct:
                # 실제로 3% 이상 도달했고, 현재도 3% 이상 유지
                take_profit_actual.append(ret)
            else:
                # 3% 이상 도달했지만, 현재는 3% 미만 (기회를 놓침)
                take_profit_missed.append(ret)
        # 손절: -7% 하락 (5일 후부터)
        elif days >= min_hold_days and min_ret <= stop_loss_pct:
            stop_loss_actual.append(ret)
        # 보존: +1.5% 도달 후 원가 이하로 하락
        elif max_ret >= preserve_pct and current_ret <= 0:
            preserve_actual.append(ret)
        # 최대 보유 기간 초과
        elif days >= max_hold_days:
            unresolved.append(ret)
        else:
            unresolved.append(ret)
    
    total_validated = len(validated_returns)
    
    # 기존 계산 방식 (최대 수익률 기준)
    win_count_max_ret = len(take_profit_actual) + len(take_profit_missed) + len(preserve_actual)
    win_rate_max_ret = (win_count_max_ret / total_validated * 100) if total_validated > 0 else 0
    
    # 실제 익절 기준 (3% 이상 도달했고 현재도 3% 이상)
    win_count_actual = len(take_profit_actual) + len(preserve_actual)
    win_rate_actual = (win_count_actual / total_validated * 100) if total_validated > 0 else 0
    
    # 현재 수익률 기준 (양수면 승리)
    win_count_current = sum(1 for r in validated_returns if r.get('current_return', 0) > 0)
    win_rate_current = (win_count_current / total_validated * 100) if total_validated > 0 else 0
    
    return {
        'total_validated': total_validated,
        'take_profit_actual': len(take_profit_actual),
        'take_profit_missed': len(take_profit_missed),
        'stop_loss_actual': len(stop_loss_actual),
        'preserve_actual': len(preserve_actual),
        'unresolved': len(unresolved),
        'win_rate_max_ret': round(win_rate_max_ret, 2),  # 최대 수익률 기준 승률
        'win_rate_actual': round(win_rate_actual, 2),    # 실제 익절 기준 승률
        'win_rate_current': round(win_rate_current, 2),   # 현재 수익률 기준 승률
        'take_profit_actual_list': take_profit_actual,
        'take_profit_missed_list': take_profit_missed,
    }


def main():
    print("🔍 승률 계산 상세 분석")
    print("=" * 60)
    
    # 최근 60일 스캔 결과 조회
    scan_results = get_recent_scan_results(days=60)
    
    # 수익률 계산
    all_returns = []
    validation_date = datetime.now().strftime('%Y%m%d')
    
    for date_str, result in scan_results.items():
        if 'error' in result or not result.get('items'):
            continue
        
        items = result['items']
        tickers = [item['ticker'] for item in items]
        
        returns_data = calculate_returns_batch(tickers, date_str, validation_date)
        
        for ticker in tickers:
            if ticker in returns_data and returns_data[ticker]:
                ret = returns_data[ticker]
                item = next((item for item in items if item['ticker'] == ticker), {})
                all_returns.append({
                    'ticker': ticker,
                    'name': item.get('name', 'N/A'),
                    'score': item.get('score', 0),
                    'scan_date': date_str,
                    'current_return': ret['current_return'],
                    'max_return': ret['max_return'],
                    'min_return': ret['min_return'],
                    'days_elapsed': ret['days_elapsed']
                })
        
        time.sleep(0.1)
    
    if not all_returns:
        print("❌ 수익률 데이터가 없습니다.")
        return
    
    print(f"\n📊 전체 데이터: {len(all_returns)}개 종목")
    
    # 상세 분석
    analysis = analyze_win_rate_detailed(all_returns, min_days_for_validation=10)
    
    if analysis:
        print(f"\n{'='*60}")
        print("📊 승률 계산 방식별 비교")
        print(f"{'='*60}")
        print(f"검증 가능 종목: {analysis['total_validated']}개")
        print()
        print(f"1️⃣ 최대 수익률 기준 (기존 방식)")
        print(f"   - 3% 이상 도달한 종목: {analysis['take_profit_actual'] + analysis['take_profit_missed']}개")
        print(f"   - 승률: {analysis['win_rate_max_ret']}%")
        print(f"   - ⚠️ 문제: 최대 수익률이 3% 이상이면 익절로 카운트")
        print(f"   - ⚠️ 실제로는 그 시점에 매도하지 않았을 수 있음")
        print()
        print(f"2️⃣ 실제 익절 기준 (3% 이상 도달 + 현재도 3% 이상)")
        print(f"   - 실제 익절: {analysis['take_profit_actual']}개")
        print(f"   - 기회 놓침: {analysis['take_profit_missed']}개 (3% 도달했지만 현재는 3% 미만)")
        print(f"   - 승률: {analysis['win_rate_actual']}%")
        print()
        print(f"3️⃣ 현재 수익률 기준 (양수면 승리)")
        print(f"   - 승률: {analysis['win_rate_current']}%")
        print()
        print(f"{'='*60}")
        print("📊 상세 분류")
        print(f"{'='*60}")
        print(f"✅ 실제 익절 (3% 이상 도달 + 현재도 3% 이상): {analysis['take_profit_actual']}개")
        print(f"⚠️ 기회 놓침 (3% 이상 도달했지만 현재는 3% 미만): {analysis['take_profit_missed']}개")
        print(f"❌ 손절 (-7% 이하): {analysis['stop_loss_actual']}개")
        print(f"💾 보존 (1.5% 도달 후 원가 이하): {analysis['preserve_actual']}개")
        print(f"⏳ 미결정: {analysis['unresolved']}개")
        
        # 기회 놓친 종목 상세
        if analysis['take_profit_missed_list']:
            print(f"\n{'='*60}")
            print("⚠️ 기회 놓친 종목 (3% 이상 도달했지만 현재는 3% 미만)")
            print(f"{'='*60}")
            for ret in analysis['take_profit_missed_list'][:10]:  # 상위 10개만
                print(f"  - {ret['name']} ({ret['ticker']}): 최대 {ret['max_return']:.2f}% → 현재 {ret['current_return']:.2f}%")
        
        print(f"\n{'='*60}")
        print("💡 결론")
        print(f"{'='*60}")
        print(f"• 기존 계산 방식 (최대 수익률 기준): {analysis['win_rate_max_ret']}%")
        print(f"  → 최대 수익률이 3% 이상이면 익절로 카운트")
        print(f"  → 실제로는 그 시점에 매도하지 않았을 수 있음")
        print()
        print(f"• 실제 익절 기준: {analysis['win_rate_actual']}%")
        print(f"  → 3% 이상 도달했고, 현재도 3% 이상 유지")
        print(f"  → 더 현실적인 승률")
        print()
        print(f"• 현재 수익률 기준: {analysis['win_rate_current']}%")
        print(f"  → 현재 수익률이 양수면 승리로 카운트")
        print(f"  → 가장 보수적인 승률")


if __name__ == '__main__':
    main()


"""
승률 계산 정확성 검증
보유중 종목을 제외하고 실제 매매 완료된 종목만으로 승률 재계산
"""
import sys
import os
from datetime import datetime, timedelta
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from calculate_win_rate_improved import get_recent_scan_results, calculate_trading_strategy_win_rate
from services.returns_service import calculate_returns_batch
import time


def calculate_actual_win_rate(returns_data, take_profit_pct=3.0, stop_loss_pct=-7.0, preserve_pct=1.5, min_hold_days=5, max_hold_days=45, min_days_for_validation=10):
    """
    실제 매매 완료된 종목만으로 승률 계산
    보유 기간이 충분한 종목만 포함 (min_days_for_validation일 이상)
    """
    if not returns_data:
        return None
    
    # 보유 기간이 충분한 종목만 필터링
    validated_returns = [r for r in returns_data if r.get('days_elapsed', 0) >= min_days_for_validation]
    
    if not validated_returns:
        return None
    
    take_profit_count = 0
    stop_loss_count = 0
    preserve_count = 0
    unresolved_count = 0  # 아직 판단 불가
    
    for ret in validated_returns:
        days = ret.get('days_elapsed', 0)
        max_ret = ret.get('max_return', 0)
        min_ret = ret.get('min_return', 0)
        current_ret = ret.get('current_return', 0)
        
        # 익절: +3% 도달
        if max_ret >= take_profit_pct:
            take_profit_count += 1
        # 손절: -7% 하락 (5일 후부터)
        elif days >= min_hold_days and min_ret <= stop_loss_pct:
            stop_loss_count += 1
        # 보존: +1.5% 도달 후 원가 이하로 하락
        elif max_ret >= preserve_pct and current_ret <= 0:
            preserve_count += 1
        # 최대 보유 기간 초과
        elif days >= max_hold_days:
            if current_ret > 0:
                take_profit_count += 1  # 최대 보유 기간 초과 시 현재 수익률로 판단
            else:
                stop_loss_count += 1
        else:
            unresolved_count += 1
    
    total_validated = len(validated_returns)
    win_count = take_profit_count + preserve_count
    
    return {
        'total_validated': total_validated,
        'take_profit_count': take_profit_count,
        'stop_loss_count': stop_loss_count,
        'preserve_count': preserve_count,
        'unresolved_count': unresolved_count,
        'win_count': win_count,
        'win_rate': round((win_count / total_validated * 100) if total_validated > 0 else 0, 2),
        'take_profit_rate': round((take_profit_count / total_validated * 100) if total_validated > 0 else 0, 2),
        'stop_loss_rate': round((stop_loss_count / total_validated * 100) if total_validated > 0 else 0, 2),
        'preserve_rate': round((preserve_count / total_validated * 100) if total_validated > 0 else 0, 2),
    }


def main():
    print("🔍 승률 계산 정확성 검증")
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
    
    # 기존 계산 (보유중 포함)
    original_stats = calculate_trading_strategy_win_rate(all_returns)
    print(f"\n{'='*60}")
    print("📊 기존 계산 (보유중 포함)")
    print(f"{'='*60}")
    print(f"총 종목 수: {original_stats['total_count']}개")
    print(f"승률: {original_stats['win_rate']}%")
    print(f"익절률: {original_stats['take_profit_rate']}%")
    print(f"손절률: {original_stats['stop_loss_rate']}%")
    print(f"보존률: {original_stats['preserve_rate']}%")
    print(f"보유중: {original_stats['holding_count']}개 ({original_stats['holding_rate']}%)")
    
    # 실제 승률 (보유 기간 10일 이상만)
    actual_stats = calculate_actual_win_rate(all_returns, min_days_for_validation=10)
    if actual_stats:
        print(f"\n{'='*60}")
        print("📊 실제 승률 (보유 기간 10일 이상만)")
        print(f"{'='*60}")
        print(f"검증 가능 종목: {actual_stats['total_validated']}개")
        print(f"승률: {actual_stats['win_rate']}% ({actual_stats['win_count']}/{actual_stats['total_validated']})")
        print(f"익절: {actual_stats['take_profit_count']}개 ({actual_stats['take_profit_rate']}%)")
        print(f"손절: {actual_stats['stop_loss_count']}개 ({actual_stats['stop_loss_rate']}%)")
        print(f"보존: {actual_stats['preserve_count']}개 ({actual_stats['preserve_rate']}%)")
        print(f"미결정: {actual_stats['unresolved_count']}개")
    
    # 보유 기간별 분포
    days_dist = {}
    for r in all_returns:
        days = r.get('days_elapsed', 0)
        days_dist.setdefault(days, []).append(r)
    
    print(f"\n{'='*60}")
    print("📊 보유 기간별 분포")
    print(f"{'='*60}")
    for days in sorted(days_dist.keys())[:20]:
        count = len(days_dist[days])
        avg_return = sum(r['current_return'] for r in days_dist[days]) / count
        print(f"{days:2d}일: {count:3d}개 (평균 수익률: {avg_return:+.2f}%)")
    
    # 보유 기간 5일 이하 (전략 미적용)
    recent = [r for r in all_returns if r.get('days_elapsed', 0) <= 5]
    if recent:
        print(f"\n⚠️ 보유 기간 5일 이하: {len(recent)}개 (전략 미적용, 승률 계산에서 제외 권장)")
        print(f"  평균 수익률: {sum(r['current_return'] for r in recent)/len(recent):.2f}%")
    
    # 보유 기간 10일 이상 (전략 적용 가능)
    mature = [r for r in all_returns if r.get('days_elapsed', 0) >= 10]
    if mature:
        print(f"\n✅ 보유 기간 10일 이상: {len(mature)}개 (전략 적용 가능)")
        mature_avg = sum(r['current_return'] for r in mature) / len(mature)
        print(f"  평균 수익률: {mature_avg:.2f}%")
        print(f"  현재 수익률 기준 승률: {sum(1 for r in mature if r['current_return'] > 0)/len(mature)*100:.1f}%")


if __name__ == '__main__':
    main()


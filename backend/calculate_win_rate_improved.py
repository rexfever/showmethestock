"""
개선된 스캔 로직(Step 0~3)으로 승률 재계산
"""
import sys
import os
from datetime import datetime, timedelta
import json

# 경로 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.scan_service import execute_scan_with_fallback
from services.returns_service import calculate_returns_batch
from market_analyzer import MarketAnalyzer
from kiwoom_api import KiwoomAPI
from config import config


def calculate_trading_strategy_win_rate(returns_data, take_profit_pct=3.0, stop_loss_pct=-7.0, preserve_pct=1.5, min_hold_days=5, max_hold_days=45):
    """
    매매 전략 승률 계산
    
    Args:
        returns_data: 수익률 데이터 리스트
        take_profit_pct: 익절 기준 (+3%)
        stop_loss_pct: 손절 기준 (-7%)
        preserve_pct: 보존 기준 (+1.5%)
        min_hold_days: 최소 보유 기간 (5일)
        max_hold_days: 최대 보유 기간 (45일)
    
    Returns:
        dict: 승률 및 통계 정보
    """
    if not returns_data:
        return {
            'total_count': 0,
            'win_rate': 0,
            'take_profit_rate': 0,
            'stop_loss_rate': 0,
            'preserve_rate': 0,
            'holding_rate': 0,
            'avg_return': 0,
            'avg_win': 0,
            'avg_loss': 0,
            'avg_hold_days': 0,
            'avg_take_profit_days': 0
        }
    
    take_profit_count = 0  # 익절
    stop_loss_count = 0    # 손절
    preserve_count = 0     # 보존
    holding_count = 0      # 보유중
    win_count = 0          # 승리 (익절 + 보존)
    
    take_profit_days = []
    all_returns = []
    win_returns = []
    loss_returns = []
    all_hold_days = []
    
    for ret in returns_data:
        days = ret.get('days_elapsed', 0)
        max_ret = ret.get('max_return', 0)
        min_ret = ret.get('min_return', 0)
        current_ret = ret.get('current_return', 0)
        
        all_returns.append(current_ret)
        all_hold_days.append(days)
        
        # 익절: +3% 도달
        if max_ret >= take_profit_pct:
            take_profit_count += 1
            win_count += 1
            # 익절 날짜 추정 (최대 수익률 도달 시점)
            # 실제로는 정확하지 않지만, 대략적으로 추정
            take_profit_days.append(days)
            win_returns.append(max_ret)
        # 손절: -7% 하락 (5일 후부터)
        elif days >= min_hold_days and min_ret <= stop_loss_pct:
            stop_loss_count += 1
            loss_returns.append(min_ret)
        # 보존: +1.5% 도달 후 원가 이하로 하락
        elif max_ret >= preserve_pct and current_ret <= 0:
            preserve_count += 1
            win_count += 1
            win_returns.append(current_ret if current_ret > 0 else preserve_pct)
        # 보유중: 아직 판단 불가
        elif days < max_hold_days:
            holding_count += 1
            if current_ret > 0:
                win_returns.append(current_ret)
            else:
                loss_returns.append(current_ret)
        # 최대 보유 기간 초과
        else:
            if current_ret > 0:
                win_count += 1
                win_returns.append(current_ret)
            else:
                loss_returns.append(current_ret)
    
    total_count = len(returns_data)
    win_rate = (win_count / total_count * 100) if total_count > 0 else 0
    take_profit_rate = (take_profit_count / total_count * 100) if total_count > 0 else 0
    stop_loss_rate = (stop_loss_count / total_count * 100) if total_count > 0 else 0
    preserve_rate = (preserve_count / total_count * 100) if total_count > 0 else 0
    holding_rate = (holding_count / total_count * 100) if total_count > 0 else 0
    
    avg_return = sum(all_returns) / len(all_returns) if all_returns else 0
    avg_win = sum(win_returns) / len(win_returns) if win_returns else 0
    avg_loss = abs(sum(loss_returns) / len(loss_returns)) if loss_returns else 0
    avg_hold_days = sum(all_hold_days) / len(all_hold_days) if all_hold_days else 0
    avg_take_profit_days = sum(take_profit_days) / len(take_profit_days) if take_profit_days else 0
    
    return {
        'total_count': total_count,
        'win_rate': round(win_rate, 2),
        'take_profit_rate': round(take_profit_rate, 2),
        'stop_loss_rate': round(stop_loss_rate, 2),
        'preserve_rate': round(preserve_rate, 2),
        'holding_rate': round(holding_rate, 2),
        'avg_return': round(avg_return, 2),
        'avg_win': round(avg_win, 2),
        'avg_loss': round(avg_loss, 2),
        'avg_hold_days': round(avg_hold_days, 1),
        'avg_take_profit_days': round(avg_take_profit_days, 1),
        'take_profit_count': take_profit_count,
        'stop_loss_count': stop_loss_count,
        'preserve_count': preserve_count,
        'holding_count': holding_count,
        'win_count': win_count
    }


def scan_recent_period(days=60):
    """최근 N일간 스캔 실행"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    results = {}
    api = KiwoomAPI()
    analyzer = MarketAnalyzer()
    
    # 유니버스 가져오기
    kospi = api.get_top_codes('KOSPI', config.universe_kospi)
    kosdaq = api.get_top_codes('KOSDAQ', config.universe_kosdaq)
    universe = [*kospi, *kosdaq]
    
    print(f"📊 유니버스: KOSPI {len(kospi)}개, KOSDAQ {len(kosdaq)}개, 총 {len(universe)}개")
    print(f"📅 스캔 기간: {start_date.strftime('%Y%m%d')} ~ {end_date.strftime('%Y%m%d')} ({days}일)")
    
    current_date = start_date
    scan_count = 0
    
    while current_date <= end_date:
        date_str = current_date.strftime('%Y%m%d')
        
        # 주말 제외
        if current_date.weekday() >= 5:  # 토요일(5), 일요일(6)
            current_date += timedelta(days=1)
            continue
        
        try:
            # 시장 분석
            market_condition = None
            try:
                market_condition = analyzer.analyze_market_condition(date_str)
            except Exception as e:
                print(f"⚠️ 시장 분석 실패 ({date_str}): {e}")
            
            # 스캔 실행 (개선된 로직: Step 0~3만 사용)
            items, chosen_step = execute_scan_with_fallback(universe, date_str, market_condition)
            
            if items:
                results[date_str] = {
                    'items': items,
                    'chosen_step': chosen_step,
                    'market_condition': {
                        'sentiment': market_condition.market_sentiment if market_condition else None,
                        'kospi_return': market_condition.kospi_return if market_condition else None
                    } if market_condition else None
                }
                scan_count += 1
                if scan_count % 10 == 0:
                    print(f"  진행: {scan_count}일 스캔 완료...")
            else:
                results[date_str] = {
                    'items': [],
                    'chosen_step': chosen_step,
                    'market_condition': None
                }
        
        except Exception as e:
            print(f"❌ 스캔 오류 ({date_str}): {e}")
            results[date_str] = {
                'items': [],
                'chosen_step': None,
                'error': str(e)
            }
        
        current_date += timedelta(days=1)
    
    print(f"\n✅ 스캔 완료: {scan_count}일")
    return results


def validate_trading_strategy_performance(scan_results: dict, validation_date: str = None):
    """매매 전략 성과 검증"""
    if validation_date is None:
        validation_date = datetime.now().strftime('%Y%m%d')
    
    print(f"\n{'='*60}")
    print(f"📊 매매 전략 성과 검증 (검증 기준일: {validation_date})")
    print(f"전략: 익절 +3%, 손절 -7% (5일 후), 보존 +1.5%")
    print(f"{'='*60}")
    
    all_returns = []
    
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
                    'chosen_step': result.get('chosen_step'),
                    'current_return': ret['current_return'],
                    'max_return': ret['max_return'],
                    'min_return': ret['min_return'],
                    'days_elapsed': ret['days_elapsed']
                })
    
    if not all_returns:
        print("❌ 수익률 데이터가 없습니다.")
        return None
    
    # 승률 계산
    stats = calculate_trading_strategy_win_rate(all_returns)
    
    print(f"\n📊 전체 통계")
    print(f"  총 종목 수: {stats['total_count']}개")
    print(f"  승률: {stats['win_rate']}% ({stats['win_count']}/{stats['total_count']})")
    print(f"  익절률: {stats['take_profit_rate']}% ({stats['take_profit_count']}개)")
    print(f"  손절률: {stats['stop_loss_rate']}% ({stats['stop_loss_count']}개)")
    print(f"  보존률: {stats['preserve_rate']}% ({stats['preserve_count']}개)")
    print(f"  보유중: {stats['holding_rate']}% ({stats['holding_count']}개)")
    print(f"  평균 수익률: {stats['avg_return']}%")
    print(f"  평균 수익: {stats['avg_win']}%")
    print(f"  평균 손실: {stats['avg_loss']}%")
    print(f"  평균 보유 기간: {stats['avg_hold_days']}일")
    print(f"  평균 익절 기간: {stats['avg_take_profit_days']}일")
    
    # 점수별 통계
    score_10_plus = [r for r in all_returns if r['score'] >= 10]
    score_8_9 = [r for r in all_returns if 8 <= r['score'] < 10]
    score_below_8 = [r for r in all_returns if r['score'] < 8]
    
    if score_10_plus:
        stats_10 = calculate_trading_strategy_win_rate(score_10_plus)
        print(f"\n📊 10점 이상 ({len(score_10_plus)}개)")
        print(f"  승률: {stats_10['win_rate']}%")
        print(f"  익절률: {stats_10['take_profit_rate']}%")
        print(f"  평균 수익률: {stats_10['avg_return']}%")
    
    if score_8_9:
        stats_8 = calculate_trading_strategy_win_rate(score_8_9)
        print(f"\n📊 8-9점 ({len(score_8_9)}개)")
        print(f"  승률: {stats_8['win_rate']}%")
        print(f"  익절률: {stats_8['take_profit_rate']}%")
        print(f"  평균 수익률: {stats_8['avg_return']}%")
    
    if score_below_8:
        stats_below = calculate_trading_strategy_win_rate(score_below_8)
        print(f"\n📊 8점 미만 ({len(score_below_8)}개)")
        print(f"  승률: {stats_below['win_rate']}%")
        print(f"  익절률: {stats_below['take_profit_rate']}%")
        print(f"  평균 수익률: {stats_below['avg_return']}%")
    
    # Step별 통계
    step_stats = {}
    for ret in all_returns:
        step = ret.get('chosen_step')
        if step is not None:
            if step not in step_stats:
                step_stats[step] = []
            step_stats[step].append(ret)
    
    if step_stats:
        print(f"\n📊 Step별 통계")
        for step in sorted(step_stats.keys()):
            step_returns = step_stats[step]
            step_stat = calculate_trading_strategy_win_rate(step_returns)
            print(f"  Step {step} ({len(step_returns)}개): 승률 {step_stat['win_rate']}%, 익절률 {step_stat['take_profit_rate']}%, 평균 {step_stat['avg_return']}%")
    
    return {
        'all_returns': all_returns,
        'stats': stats,
        'score_stats': {
            '10_plus': calculate_trading_strategy_win_rate(score_10_plus) if score_10_plus else None,
            '8_9': calculate_trading_strategy_win_rate(score_8_9) if score_8_9 else None,
            'below_8': calculate_trading_strategy_win_rate(score_below_8) if score_below_8 else None
        },
        'step_stats': {step: calculate_trading_strategy_win_rate(returns) for step, returns in step_stats.items()}
    }


def main():
    """메인 실행"""
    print(f"🚀 개선된 스캔 로직(Step 0~3)으로 승률 재계산 시작")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 최근 60일 스캔
    scan_results = scan_recent_period(days=60)
    
    # 결과 저장
    output_file = f"scan_results_improved_{datetime.now().strftime('%Y%m%d')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(scan_results, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n💾 스캔 결과 저장: {output_file}")
    
    # 성과 검증
    validation_results = validate_trading_strategy_performance(scan_results)
    
    if validation_results:
        # 검증 결과 저장
        validation_file = f"win_rate_calculation_{datetime.now().strftime('%Y%m%d')}.json"
        with open(validation_file, 'w', encoding='utf-8') as f:
            json.dump(validation_results, f, ensure_ascii=False, indent=2, default=str)
        print(f"\n💾 검증 결과 저장: {validation_file}")
        
        # 승률 요약 출력
        stats = validation_results['stats']
        print(f"\n{'='*60}")
        print(f"📊 최종 승률 요약")
        print(f"{'='*60}")
        print(f"승률: {stats['win_rate']}%")
        print(f"익절률: {stats['take_profit_rate']}%")
        print(f"손절률: {stats['stop_loss_rate']}%")
        print(f"보존률: {stats['preserve_rate']}%")
        print(f"평균 수익률: {stats['avg_return']}%")
        print(f"평균 보유 기간: {stats['avg_hold_days']}일")
        print(f"평균 익절 기간: {stats['avg_take_profit_days']}일")
    
    print(f"\n✅ 완료!")


if __name__ == '__main__':
    main()


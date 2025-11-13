#!/usr/bin/env python3
"""
스캔 종목들의 가격 변동을 추적하여 매매 전략의 유효성 검증
전략: 손절 -5%, 익절 +8%, 보존 +3%
"""
import sys
import os
from datetime import datetime, timedelta
import time
import pandas as pd

# 프로젝트 루트 디렉토리를 PYTHONPATH에 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from kiwoom_api import api
from db_manager import db_manager


def validate_trading_strategy(
    date_limit=None,
    max_stocks=None,
    stop_loss_pct=-5.0,
    take_profit_pct=8.0,
    preserve_pct=3.0,
    max_days=60,
    min_hold_days=0
):
    """
    매매 전략 유효성 검증
    
    Args:
        date_limit: 검증할 최근 날짜 수 (None이면 최근 30일)
        max_stocks: 검증할 최대 종목 수
        stop_loss_pct: 손절 비율 (%)
        take_profit_pct: 익절 비율 (%)
        preserve_pct: 보존 비율 (%)
        max_days: 최대 추적 일수
        min_hold_days: 최소 보유 기간 (일) - 이 기간 동안은 손절 제외
    """
    print("=" * 80)
    print("📊 매매 전략 유효성 검증")
    print("=" * 80)
    print(f"전략:")
    print(f"  - 손절: {stop_loss_pct}%")
    print(f"  - 익절: {take_profit_pct}%")
    print(f"  - 보존: {preserve_pct}%")
    print(f"  - 최대 추적: {max_days}일")
    print(f"  - 최소 보유: {min_hold_days}일")
    print()
    
    # 스캔된 종목 조회 (전체 기간)
    with db_manager.get_cursor(commit=False) as cur:
        if date_limit:
            date_threshold = (datetime.now() - timedelta(days=date_limit)).strftime('%Y-%m-%d')
            query = """
                SELECT date, code, name, current_price
                FROM scan_rank
                WHERE date >= %s
                  AND code != 'NORESULT'
                  AND current_price IS NOT NULL
                  AND current_price > 0
                ORDER BY date DESC, code
            """
            if max_stocks:
                query += f" LIMIT {max_stocks}"
            cur.execute(query, (date_threshold,))
        else:
            # 전체 기간 조회 (DISTINCT 제거)
            query = """
                SELECT date, code, name, current_price
                FROM scan_rank
                WHERE code != 'NORESULT'
                  AND current_price IS NOT NULL
                  AND current_price > 0
                ORDER BY date DESC, code
            """
            if max_stocks:
                query += f" LIMIT {max_stocks}"
            cur.execute(query)
        
        rows = cur.fetchall()
    
    if not rows:
        print("❌ 검증할 데이터가 없습니다.")
        return
    
    print(f"📊 검증 대상: {len(rows)}개 종목")
    print()
    
    # 결과 저장
    results = []
    
    # 각 종목 추적
    for idx, row in enumerate(rows, 1):
        if isinstance(row, dict):
            scan_date = row['date']
            code = row['code']
            name = row['name']
            entry_price = row['current_price']
        else:
            scan_date = row[0]
            code = row[1]
            name = row[2]
            entry_price = row[3]
        
        print(f"[{idx}/{len(rows)}] {code} ({name}) - 스캔일: {scan_date}, 매수가: {entry_price:,.0f}원", end=" ... ")
        
        try:
            # 날짜 형식 변환
            if hasattr(scan_date, 'strftime'):
                scan_date_str = scan_date.strftime('%Y%m%d')
            elif isinstance(scan_date, str):
                scan_date_str = scan_date.replace('-', '')
            else:
                scan_date_str = str(scan_date).replace('-', '')
            
            # 스캔일 이후 가격 데이터 조회
            today_str = datetime.now().strftime('%Y%m%d')
            days_diff = (datetime.now() - datetime.strptime(scan_date_str, '%Y%m%d')).days
            count = min(days_diff + 10, max_days + 10)  # 여유분 포함
            
            df = api.get_ohlcv(code, count=count, base_dt=today_str)
            
            if df.empty:
                print("❌ 데이터 없음")
                results.append({
                    'code': code,
                    'name': name,
                    'scan_date': scan_date,
                    'entry_price': entry_price,
                    'status': 'NO_DATA',
                    'exit_price': None,
                    'return_pct': None,
                    'exit_date': None,
                    'days_to_exit': None,
                    'max_gain_pct': None,
                    'max_loss_pct': None
                })
                time.sleep(0.2)
                continue
            
            # 날짜 형식 정규화
            def normalize_date(date_val):
                try:
                    if hasattr(date_val, 'strftime'):
                        return date_val.strftime('%Y%m%d')
                    elif isinstance(date_val, str):
                        return date_val.replace('-', '').replace('/', '')[:8]
                    else:
                        return str(date_val).replace('-', '').replace('/', '')[:8]
                except:
                    return None
            
            df['date_normalized'] = df['date'].apply(normalize_date)
            scan_date_normalized = normalize_date(scan_date_str)
            
            # 스캔일 이후 데이터만 필터링
            df_filtered = df[df['date_normalized'] >= scan_date_normalized].copy()
            
            if df_filtered.empty:
                print("❌ 스캔일 이후 데이터 없음")
                results.append({
                    'code': code,
                    'name': name,
                    'scan_date': scan_date,
                    'entry_price': entry_price,
                    'status': 'NO_DATA_AFTER_SCAN',
                    'exit_price': None,
                    'return_pct': None,
                    'exit_date': None,
                    'days_to_exit': None,
                    'max_gain_pct': None,
                    'max_loss_pct': None
                })
                time.sleep(0.2)
                continue
            
            # 날짜순 정렬
            df_filtered = df_filtered.sort_values('date_normalized').reset_index(drop=True)
            
            # 스캔일부터 추적 (성과보고서와 동일하게)
            # 스캔일의 최고가도 익절에 포함되어야 함
            df_tracking = df_filtered[df_filtered['date_normalized'] >= scan_date_normalized].copy()
            
            if df_tracking.empty:
                print("❌ 추적 데이터 없음 (스캔일 데이터 없음)")
                results.append({
                    'code': code,
                    'name': name,
                    'scan_date': scan_date,
                    'entry_price': entry_price,
                    'status': 'NO_TRACKING_DATA',
                    'exit_price': None,
                    'return_pct': None,
                    'exit_date': None,
                    'days_to_exit': None,
                    'max_gain_pct': None,
                    'max_loss_pct': None
                })
                time.sleep(0.2)
                continue
            
            # 전략 추적 (스캔일부터)
            status = 'HOLDING'  # HOLDING, STOP_LOSS, TAKE_PROFIT, PRESERVED, MAX_DAYS
            exit_price = None
            exit_date = None
            days_to_exit = None
            max_gain_pct = 0
            max_loss_pct = 0
            preserve_triggered = False
            
            for i, price_row in df_tracking.iterrows():
                close_price = float(price_row['close'])
                # API에서 high/low가 0인 경우 close를 사용 (성과보고서와 동일)
                high_price = float(price_row['high']) if price_row['high'] > 0 else close_price
                low_price = float(price_row['low']) if price_row['low'] > 0 else close_price
                current_date = price_row['date_normalized']
                
                # 수익률 계산
                return_pct = ((close_price - entry_price) / entry_price) * 100
                high_return_pct = ((high_price - entry_price) / entry_price) * 100
                low_return_pct = ((low_price - entry_price) / entry_price) * 100
                
                # 최고/최저 수익률 업데이트
                max_gain_pct = max(max_gain_pct, high_return_pct)
                max_loss_pct = min(max_loss_pct, low_return_pct)
                
                # 보존 조건 체크 (+3% 도달 시 손절선을 매수가로 올림)
                if not preserve_triggered and return_pct >= preserve_pct:
                    preserve_triggered = True
                    # 손절선을 매수가로 변경 (이제 0% 미만이면 손절)
                
                # 최소 보유 기간 체크
                current_days = (datetime.strptime(current_date, '%Y%m%d') - 
                               datetime.strptime(scan_date_normalized, '%Y%m%d')).days
                
                # 최소 보유 기간 전에는 손절 제외
                can_stop_loss = current_days >= min_hold_days
                
                # 손절 조건 체크 (최소 보유 기간 경과 후에만)
                if can_stop_loss:
                    if preserve_triggered:
                        # 보존 후에는 0% 미만이면 손절
                        if low_return_pct < 0:
                            status = 'STOP_LOSS'
                            exit_price = entry_price  # 보존 후 손절은 매수가
                            exit_date = current_date
                            days_to_exit = current_days
                            break
                    else:
                        # 보존 전에는 손절 기준으로 손절
                        if low_return_pct <= stop_loss_pct:
                            status = 'STOP_LOSS'
                            exit_price = entry_price * (1 + stop_loss_pct / 100)
                            exit_date = current_date
                            days_to_exit = current_days
                            break
                
                # 익절 조건 체크 (스캔일 포함)
                if high_return_pct >= take_profit_pct:
                    status = 'TAKE_PROFIT'
                    exit_price = entry_price * (1 + take_profit_pct / 100)
                    exit_date = current_date
                    days_to_exit = current_days  # current_days는 이미 계산됨
                    break
                
                # 최대 일수 체크 (current_days는 이미 위에서 계산됨)
                if current_days >= max_days:
                    status = 'MAX_DAYS'
                    exit_price = close_price
                    exit_date = current_date
                    days_to_exit = max_days
                    break
            
            # 최종 결과
            if status == 'HOLDING':
                # 아직 보유 중 (최신 데이터)
                latest_price = float(df_tracking.iloc[-1]['close'])
                return_pct = ((latest_price - entry_price) / entry_price) * 100
                exit_price = latest_price
                exit_date = df_tracking.iloc[-1]['date_normalized']
                days_to_exit = (datetime.strptime(exit_date, '%Y%m%d') - 
                               datetime.strptime(scan_date_normalized, '%Y%m%d')).days
            else:
                return_pct = ((exit_price - entry_price) / entry_price) * 100
            
            # 보존 여부 추가
            if preserve_triggered and status != 'TAKE_PROFIT':
                status_label = f"{status}_PRESERVED" if status != 'STOP_LOSS' else status
            else:
                status_label = status
            
            results.append({
                'code': code,
                'name': name,
                'scan_date': scan_date,
                'entry_price': entry_price,
                'status': status_label,
                'exit_price': exit_price,
                'return_pct': return_pct,
                'exit_date': exit_date,
                'days_to_exit': days_to_exit,
                'max_gain_pct': max_gain_pct,
                'max_loss_pct': max_loss_pct,
                'preserved': preserve_triggered
            })
            
            status_emoji = {
                'STOP_LOSS': '❌',
                'TAKE_PROFIT': '✅',
                'PRESERVED': '🔒',
                'HOLDING': '📊',
                'MAX_DAYS': '⏰'
            }
            emoji = status_emoji.get(status_label.split('_')[0], '❓')
            print(f"{emoji} {status_label} ({return_pct:+.2f}%, {days_to_exit}일)")
            
            time.sleep(0.2)
            
        except Exception as e:
            print(f"❌ 오류: {str(e)}")
            results.append({
                'code': code,
                'name': name,
                'scan_date': scan_date,
                'entry_price': entry_price,
                'status': 'ERROR',
                'exit_price': None,
                'return_pct': None,
                'exit_date': None,
                'days_to_exit': None,
                'max_gain_pct': None,
                'max_loss_pct': None,
                'error': str(e)
            })
            time.sleep(1)
    
    print()
    print("=" * 80)
    print("📊 검증 결과 요약")
    print("=" * 80)
    
    # 통계 계산
    valid_results = [r for r in results if r['status'] not in ['NO_DATA', 'NO_DATA_AFTER_SCAN', 'ERROR']]
    
    if not valid_results:
        print("❌ 검증 가능한 결과가 없습니다.")
        return
    
    total_count = len(valid_results)
    stop_loss_count = len([r for r in valid_results if 'STOP_LOSS' in r['status']])
    take_profit_count = len([r for r in valid_results if 'TAKE_PROFIT' in r['status']])
    preserved_count = len([r for r in valid_results if r.get('preserved', False)])
    holding_count = len([r for r in valid_results if r['status'] == 'HOLDING'])
    max_days_count = len([r for r in valid_results if r['status'] == 'MAX_DAYS'])
    
    print(f"📊 총 검증: {total_count}개")
    print(f"✅ 익절: {take_profit_count}개 ({take_profit_count/total_count*100:.1f}%)")
    print(f"❌ 손절: {stop_loss_count}개 ({stop_loss_count/total_count*100:.1f}%)")
    print(f"🔒 보존: {preserved_count}개 ({preserved_count/total_count*100:.1f}%)")
    print(f"📊 보유중: {holding_count}개 ({holding_count/total_count*100:.1f}%)")
    print(f"⏰ 최대일수: {max_days_count}개 ({max_days_count/total_count*100:.1f}%)")
    print()
    
    # 수익률 통계
    returns = [r['return_pct'] for r in valid_results if r['return_pct'] is not None]
    if returns:
        avg_return = sum(returns) / len(returns)
        win_rate = len([r for r in returns if r > 0]) / len(returns) * 100
        avg_win = sum([r for r in returns if r > 0]) / len([r for r in returns if r > 0]) if [r for r in returns if r > 0] else 0
        avg_loss = sum([r for r in returns if r < 0]) / len([r for r in returns if r < 0]) if [r for r in returns if r < 0] else 0
        
        print(f"📈 평균 수익률: {avg_return:+.2f}%")
        print(f"📊 승률: {win_rate:.1f}%")
        print(f"✅ 평균 수익: {avg_win:+.2f}%")
        print(f"❌ 평균 손실: {avg_loss:+.2f}%")
        if avg_loss != 0:
            print(f"⚖️ 손익비: {abs(avg_win / avg_loss):.2f}:1")
        print()
    
    # 기간 통계
    days_list = [r['days_to_exit'] for r in valid_results if r['days_to_exit'] is not None]
    if days_list:
        avg_days = sum(days_list) / len(days_list)
        print(f"⏱️ 평균 보유 기간: {avg_days:.1f}일")
        
        take_profit_days = [r['days_to_exit'] for r in valid_results 
                           if 'TAKE_PROFIT' in r['status'] and r['days_to_exit'] is not None]
        if take_profit_days:
            avg_tp_days = sum(take_profit_days) / len(take_profit_days)
            print(f"✅ 평균 익절 기간: {avg_tp_days:.1f}일")
        
        stop_loss_days = [r['days_to_exit'] for r in valid_results 
                         if 'STOP_LOSS' in r['status'] and r['days_to_exit'] is not None]
        if stop_loss_days:
            avg_sl_days = sum(stop_loss_days) / len(stop_loss_days)
            print(f"❌ 평균 손절 기간: {avg_sl_days:.1f}일")
        print()
    
    # 상세 결과 표시 (최대 20개)
    print("=" * 80)
    print("📋 상세 결과 (최대 20개)")
    print("=" * 80)
    for r in valid_results[:20]:
        status_emoji = {
            'STOP_LOSS': '❌',
            'TAKE_PROFIT': '✅',
            'PRESERVED': '🔒',
            'HOLDING': '📊',
            'MAX_DAYS': '⏰'
        }
        emoji = status_emoji.get(r['status'].split('_')[0], '❓')
        print(f"{emoji} {r['code']} ({r['name']}) | {r['scan_date']}")
        print(f"   매수가: {r['entry_price']:,.0f}원")
        if r['exit_price']:
            print(f"   매도가: {r['exit_price']:,.0f}원")
        if r['return_pct'] is not None:
            print(f"   수익률: {r['return_pct']:+.2f}%")
        if r['days_to_exit'] is not None:
            print(f"   보유기간: {r['days_to_exit']}일")
        if r['max_gain_pct'] is not None:
            print(f"   최대수익: {r['max_gain_pct']:+.2f}%")
        if r.get('preserved'):
            print(f"   🔒 보존 조건 도달")
        print()
    
    if len(valid_results) > 20:
        print(f"... 외 {len(valid_results) - 20}개 종목")
        print()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="매매 전략 유효성 검증")
    parser.add_argument("--date-limit", type=int, help="검증할 최근 날짜 수 (기본: 30일)")
    parser.add_argument("--max-stocks", type=int, help="검증할 최대 종목 수")
    parser.add_argument("--stop-loss", type=float, default=-5.0, help="손절 비율 %% (기본: -5.0%%)")
    parser.add_argument("--take-profit", type=float, default=8.0, help="익절 비율 %% (기본: 8.0%%)")
    parser.add_argument("--preserve", type=float, default=3.0, help="보존 비율 %% (기본: 3.0%%)")
    parser.add_argument("--max-days", type=int, default=60, help="최대 추적 일수 (기본: 60일)")
    parser.add_argument("--min-hold-days", type=int, default=0, help="최소 보유 기간 일 (기본: 0일)")
    
    args = parser.parse_args()
    
    validate_trading_strategy(
        date_limit=args.date_limit,
        max_stocks=args.max_stocks,
        stop_loss_pct=args.stop_loss,
        take_profit_pct=args.take_profit,
        preserve_pct=args.preserve,
        max_days=args.max_days,
        min_hold_days=args.min_hold_days
    )


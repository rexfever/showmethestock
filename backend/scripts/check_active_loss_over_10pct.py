"""
ACTIVE 상태인데 손실이 -10% 이상인 종목 확인
"""
import sys
import os
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
os.chdir(backend_dir)

from db_manager import db_manager
from date_helper import yyyymmdd_to_date, get_kst_now
from services.state_transition_service import get_trading_days_since
from kiwoom_api import api
import holidays
from datetime import datetime, timedelta

def check_active_loss_over_10pct():
    """ACTIVE 상태인데 손실이 -10% 이상인 종목 확인"""
    try:
        with db_manager.get_cursor(commit=False) as cur:
            # ACTIVE 상태인 추천 조회
            cur.execute("""
                SELECT 
                    r.recommendation_id,
                    r.ticker,
                    r.name,
                    r.anchor_date,
                    r.anchor_close,
                    r.strategy,
                    r.status,
                    r.created_at,
                    r.flags
                FROM recommendations r
                WHERE r.status IN ('ACTIVE', 'WEAK_WARNING')
                AND r.scanner_version = 'v3'
                ORDER BY r.anchor_date DESC
            """)
            
            rows = cur.fetchall()
            
            if not rows:
                print("ACTIVE 상태인 추천이 없습니다.")
                return
            
            print(f"ACTIVE 상태인 추천: {len(rows)}개\n")
            print("=" * 150)
            
            loss_over_10pct = []
            
            for idx, row in enumerate(rows, 1):
                rec_id = row[0]
                ticker = row[1]
                name = row[2]
                anchor_date = row[3]
                anchor_close = row[4]
                strategy = row[5]
                status = row[6]
                created_at = row[7]
                flags = row[8]
                
                # 현재 가격 조회
                try:
                    today_str = datetime.now().strftime('%Y%m%d')
                    df = api.get_ohlcv(ticker, 10, today_str)
                    
                    if df.empty:
                        continue
                    
                    # 최신 가격
                    if 'date' in df.columns:
                        latest_price = float(df.iloc[-1]['close'])
                        latest_date = df.iloc[-1]['date']
                    else:
                        latest_price = float(df.iloc[-1]['close']) if 'close' in df.columns else None
                        latest_date = None
                    
                    if latest_price and anchor_close:
                        anchor_close_float = float(anchor_close)
                        current_return = ((latest_price - anchor_close_float) / anchor_close_float) * 100
                        
                        if current_return < -10.0:
                            # 거래일 수 계산
                            trading_days = get_trading_days_since(anchor_date)
                            
                            # 전략별 TTL 확인
                            ttl_days = 20
                            if strategy == "v2_lite" or strategy == "PULLBACK_V2_LITE":
                                ttl_days = 15
                            elif strategy == "midterm" or strategy == "MIDTERM":
                                ttl_days = 25
                            
                            loss_over_10pct.append({
                                'rec_id': rec_id,
                                'ticker': ticker,
                                'name': name,
                                'anchor_date': anchor_date,
                                'anchor_close': anchor_close,
                                'strategy': strategy,
                                'status': status,
                                'current_price': latest_price,
                                'current_return': current_return,
                                'trading_days': trading_days,
                                'ttl_days': ttl_days,
                                'latest_date': latest_date
                            })
                except Exception as e:
                    print(f"    ⚠️  {ticker} 가격 조회 실패: {e}")
                    continue
            
            if not loss_over_10pct:
                print("손실이 -10% 이상인 ACTIVE 종목이 없습니다.")
                return
            
            print(f"손실이 -10% 이상인 ACTIVE 종목: {len(loss_over_10pct)}개\n")
            print("=" * 150)
            
            for idx, item in enumerate(sorted(loss_over_10pct, key=lambda x: x['current_return']), 1):
                print(f"\n[{idx}] {item['ticker']} ({item['name']})")
                print(f"    상태: {item['status']}")
                print(f"    전략: {item['strategy']}")
                print(f"    추천일: {item['anchor_date']}")
                print(f"    추천 시점 가격: {item['anchor_close']:,.0f}원")
                print(f"    현재 가격 ({item['latest_date']}): {item['current_price']:,.0f}원")
                print(f"    현재 수익률: {item['current_return']:,.2f}%")
                print(f"    거래일 수: {item['trading_days']}일")
                print(f"    TTL: {item['ttl_days']}거래일")
                
                # TTL 초과 여부
                if item['trading_days'] >= item['ttl_days']:
                    print(f"    ⚠️  TTL 초과: {item['trading_days'] - item['ttl_days']}거래일 초과")
                else:
                    print(f"    TTL 남은 거래일: {item['ttl_days'] - item['trading_days']}일")
                
                # 손절 조건 확인
                if item['current_return'] < -10.0:
                    print(f"    ⚠️  손실이 -10%를 초과했습니다. BROKEN 상태로 전환되어야 합니다.")
                
                print("-" * 150)
            
            print(f"\n[요약]")
            print(f"  총 {len(loss_over_10pct)}개의 종목이 -10% 이상 손실")
            print(f"  평균 손실: {sum(x['current_return'] for x in loss_over_10pct) / len(loss_over_10pct):.2f}%")
            print(f"  최대 손실: {min(x['current_return'] for x in loss_over_10pct):.2f}%")
            print(f"  TTL 초과: {sum(1 for x in loss_over_10pct if x['trading_days'] >= x['ttl_days'])}개")
                
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("ACTIVE 상태인데 손실이 -10% 이상인 종목 확인...")
    print("=" * 150)
    check_active_loss_over_10pct()
    print("\n완료!")


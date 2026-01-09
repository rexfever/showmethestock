"""
ARCHIVED 데이터 중 수익률이 20% 이상인 항목의 정책 준수 여부 점검
- TTL_EXPIRED 케이스: TTL 만료 시점의 수익률이어야 함
- REPLACED 케이스: REPLACED 전환 시점의 수익률이어야 함
- NO_MOMENTUM 케이스: 손절 조건 만족 시점의 수익률이어야 함
"""
import sys
import os
from pathlib import Path
from decimal import Decimal

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
os.chdir(backend_dir)

from db_manager import db_manager
from date_helper import yyyymmdd_to_date, get_kst_now
from kiwoom_api import api
from datetime import datetime, timedelta
import holidays

def get_nth_trading_day_after(start_date, n):
    """시작일로부터 n번째 거래일 계산"""
    if isinstance(start_date, str):
        start_date = yyyymmdd_to_date(start_date.replace('-', '')[:8])
    if isinstance(start_date, datetime):
        start_date = start_date.date()
    
    kr_holidays = holidays.SouthKorea(years=range(start_date.year, start_date.year + 2))
    
    current = start_date
    trading_days_count = 0
    
    while trading_days_count < n:
        if current.weekday() < 5 and current not in kr_holidays:
            trading_days_count += 1
        if trading_days_count < n:
            current += timedelta(days=1)
    
    return current

def get_ttl_expiry_date(anchor_date, strategy):
    """TTL 만료일 계산"""
    if isinstance(anchor_date, str):
        anchor_date = yyyymmdd_to_date(anchor_date.replace('-', '')[:8])
    if isinstance(anchor_date, datetime):
        anchor_date = anchor_date.date()
    
    # 전략별 TTL 설정
    ttl_days = 20  # 기본값
    if strategy == "v2_lite" or strategy == "PULLBACK_V2_LITE":
        ttl_days = 15
    elif strategy == "midterm" or strategy == "MIDTERM":
        ttl_days = 25
    
    # TTL 만료일 계산 (anchor_date + ttl_days 거래일)
    ttl_expiry_date = get_nth_trading_day_after(anchor_date, ttl_days)
    
    return ttl_expiry_date, ttl_days

def check_archived_high_profit_violations():
    """ARCHIVED 데이터 중 수익률이 20% 이상인 항목 점검"""
    try:
        with db_manager.get_cursor(commit=False) as cur:
            # 수익률이 20% 이상인 ARCHIVED 항목 조회
            cur.execute("""
                SELECT 
                    r.recommendation_id,
                    r.ticker,
                    r.name,
                    r.anchor_date,
                    r.anchor_close,
                    r.strategy,
                    r.broken_at,
                    r.broken_return_pct,
                    r.status_changed_at,
                    r.archived_at,
                    r.archive_return_pct,
                    r.archive_price,
                    r.archive_phase,
                    r.archive_reason
                FROM recommendations r
                WHERE r.status = 'ARCHIVED'
                AND r.scanner_version = 'v3'
                AND r.archive_return_pct IS NOT NULL
                AND r.archive_return_pct >= 20.0
                ORDER BY r.archive_return_pct DESC
            """)
            
            rows = cur.fetchall()
            
            if not rows:
                print("수익률이 20% 이상인 ARCHIVED 항목이 없습니다.")
                return
            
            print(f"수익률이 20% 이상인 ARCHIVED 항목: {len(rows)}개\n")
            print("=" * 150)
            
            violations = []
            potential_issues = []
            
            for row in rows:
                rec_id, ticker, name, anchor_date, anchor_close, strategy, broken_at, broken_return_pct, \
                status_changed_at, archived_at, archive_return_pct, archive_price, archive_phase, \
                archive_reason = row
                
                archive_return_pct_float = float(archive_return_pct) if archive_return_pct else None
                anchor_close_float = float(anchor_close) if anchor_close else None
                
                print(f"\n[항목] {ticker} ({name if name else 'N/A'})")
                print(f"  전략: {strategy}")
                print(f"  archive_reason: {archive_reason}")
                print(f"  archive_return_pct: {archive_return_pct_float:.2f}%")
                print(f"  anchor_date: {anchor_date}")
                print(f"  archived_at: {archived_at}")
                print(f"  broken_at: {broken_at}")
                
                if not anchor_close_float:
                    print("  ⚠️ anchor_close가 없어 분석 불가")
                    potential_issues.append({
                        'rec_id': rec_id,
                        'ticker': ticker,
                        'issue': 'anchor_close 없음'
                    })
                    continue
                
                # anchor_date 파싱
                if isinstance(anchor_date, str):
                    anchor_date_obj = yyyymmdd_to_date(anchor_date.replace('-', '')[:8])
                else:
                    anchor_date_obj = anchor_date
                
                if isinstance(anchor_date_obj, datetime):
                    anchor_date_obj = anchor_date_obj.date()
                
                # archived_at 파싱
                if isinstance(archived_at, str):
                    archived_at_obj = yyyymmdd_to_date(archived_at.replace('-', '')[:8])
                elif archived_at:
                    archived_at_obj = archived_at.date() if isinstance(archived_at, datetime) else archived_at
                else:
                    archived_at_obj = get_kst_now().date()
                
                # archive_reason에 따른 정책 확인
                is_violation = False
                violation_reasons = []
                expected_return_pct = None
                expected_date = None
                
                if archive_reason == 'TTL_EXPIRED':
                    # TTL 만료 시점의 수익률이어야 함
                    ttl_expiry_date, ttl_days = get_ttl_expiry_date(anchor_date_obj, strategy)
                    expected_date = ttl_expiry_date
                    
                    # TTL 만료일과 archived_at 비교
                    if archived_at_obj > ttl_expiry_date:
                        # TTL을 초과했으므로 TTL 시점의 수익률을 확인해야 함
                        print(f"  TTL 만료일: {ttl_expiry_date} (TTL: {ttl_days}거래일)")
                        print(f"  archived_at: {archived_at_obj}")
                        print(f"  ⚠️ TTL을 초과했으므로 TTL 시점의 수익률을 확인해야 함")
                        
                        # TTL 시점의 가격 조회
                        try:
                            days_diff = (ttl_expiry_date - anchor_date_obj).days
                            df = api.get_ohlcv(ticker, days_diff + 30, ttl_expiry_date.strftime('%Y%m%d'))
                            
                            if not df.empty and 'date' in df.columns:
                                df['date_str'] = df['date'].astype(str).str.replace('-', '').str[:8]
                                ttl_date_str = ttl_expiry_date.strftime('%Y%m%d')
                                df_filtered = df[df['date_str'] <= ttl_date_str].sort_values('date_str')
                                
                                if not df_filtered.empty:
                                    last_row = df_filtered.iloc[-1]
                                    ttl_close = float(last_row['close']) if 'close' in last_row else None
                                    
                                    if ttl_close:
                                        expected_return_pct = round(((ttl_close - anchor_close_float) / anchor_close_float) * 100, 2)
                                        print(f"  TTL 시점 수익률: {expected_return_pct:.2f}%")
                                        
                                        # 현재 archive_return_pct와 비교
                                        if abs(expected_return_pct - archive_return_pct_float) > 0.5:
                                            is_violation = True
                                            violation_reasons.append(f"TTL 시점 수익률({expected_return_pct:.2f}%)과 archive_return_pct({archive_return_pct_float:.2f}%) 불일치")
                                else:
                                    print(f"  ⚠️ TTL 시점 데이터 없음")
                            else:
                                print(f"  ⚠️ 가격 데이터 조회 실패")
                        except Exception as e:
                            print(f"  ❌ 오류: {e}")
                
                elif archive_reason == 'REPLACED':
                    # REPLACED 전환 시점(status_changed_at)의 수익률이어야 함
                    if status_changed_at:
                        if isinstance(status_changed_at, str):
                            expected_date = yyyymmdd_to_date(status_changed_at.replace('-', '')[:8])
                        elif isinstance(status_changed_at, datetime):
                            expected_date = status_changed_at.date()
                        else:
                            expected_date = status_changed_at
                        
                        print(f"  REPLACED 전환일: {expected_date}")
                        
                        # REPLACED 시점의 가격 조회
                        try:
                            days_diff = (expected_date - anchor_date_obj).days
                            df = api.get_ohlcv(ticker, days_diff + 30, expected_date.strftime('%Y%m%d'))
                            
                            if not df.empty and 'date' in df.columns:
                                df['date_str'] = df['date'].astype(str).str.replace('-', '').str[:8]
                                replaced_date_str = expected_date.strftime('%Y%m%d')
                                df_filtered = df[df['date_str'] <= replaced_date_str].sort_values('date_str')
                                
                                if not df_filtered.empty:
                                    last_row = df_filtered.iloc[-1]
                                    replaced_close = float(last_row['close']) if 'close' in last_row else None
                                    
                                    if replaced_close:
                                        expected_return_pct = round(((replaced_close - anchor_close_float) / anchor_close_float) * 100, 2)
                                        print(f"  REPLACED 시점 수익률: {expected_return_pct:.2f}%")
                                        
                                        # 현재 archive_return_pct와 비교
                                        if abs(expected_return_pct - archive_return_pct_float) > 0.5:
                                            is_violation = True
                                            violation_reasons.append(f"REPLACED 시점 수익률({expected_return_pct:.2f}%)과 archive_return_pct({archive_return_pct_float:.2f}%) 불일치")
                                else:
                                    print(f"  ⚠️ REPLACED 시점 데이터 없음")
                            else:
                                print(f"  ⚠️ 가격 데이터 조회 실패")
                        except Exception as e:
                            print(f"  ❌ 오류: {e}")
                    else:
                        print(f"  ⚠️ status_changed_at이 없음")
                
                elif archive_reason == 'NO_MOMENTUM':
                    # 손절 조건 만족 시점의 수익률이어야 함 (broken_return_pct 사용)
                    if broken_return_pct is not None:
                        expected_return_pct = float(broken_return_pct)
                        print(f"  broken_return_pct: {expected_return_pct:.2f}%")
                        
                        if abs(expected_return_pct - archive_return_pct_float) > 0.01:
                            is_violation = True
                            violation_reasons.append(f"broken_return_pct({expected_return_pct:.2f}%)과 archive_return_pct({archive_return_pct_float:.2f}%) 불일치")
                    else:
                        print(f"  ⚠️ broken_return_pct가 없음 (손절 조건 만족 시점 정보 없음)")
                
                if is_violation:
                    violations.append({
                        'rec_id': rec_id,
                        'ticker': ticker,
                        'name': name,
                        'strategy': strategy,
                        'archive_reason': archive_reason,
                        'current_archive_return_pct': archive_return_pct_float,
                        'expected_return_pct': expected_return_pct,
                        'expected_date': expected_date,
                        'violation_reasons': violation_reasons,
                        'anchor_date': anchor_date,
                        'archived_at': archived_at
                    })
                    print(f"  ❌ 정책 위반:")
                    for reason in violation_reasons:
                        print(f"    - {reason}")
                else:
                    print(f"  ✅ 정책 준수")
                
                print("-" * 150)
            
            # 결과 출력
            print(f"\n\n[결과]")
            print(f"  전체 조회 항목: {len(rows)}개")
            print(f"  정책 위반 항목: {len(violations)}개")
            print(f"  잠재적 문제 항목: {len(potential_issues)}개")
            
            if violations:
                print(f"\n[정책 위반 항목 상세]")
                for v in violations:
                    print(f"\n  티커: {v['ticker']} ({v['name']})")
                    print(f"    archive_reason: {v['archive_reason']}")
                    print(f"    현재 archive_return_pct: {v['current_archive_return_pct']:.2f}%")
                    print(f"    예상 수익률: {v['expected_return_pct']:.2f}%" if v['expected_return_pct'] else "    예상 수익률: 계산 불가")
                    print(f"    예상 날짜: {v['expected_date']}")
                    print(f"    위반 사유:")
                    for reason in v['violation_reasons']:
                        print(f"      - {reason}")
                    print(f"    recommendation_id: {v['rec_id']}")
            
            return violations, potential_issues
            
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return None, None

if __name__ == '__main__':
    check_archived_high_profit_violations()


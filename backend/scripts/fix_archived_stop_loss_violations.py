"""
ARCHIVED 데이터 중 손절 정책 위반 항목을 정책에 맞게 수정
- 손절 조건을 만족한 시점의 손익률을 broken_return_pct와 archive_return_pct로 업데이트
- v2_lite: -2.0% 손절 기준
- midterm: -7.0% 손절 기준
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

def get_stop_loss_pct(strategy):
    """전략별 손절 기준 반환"""
    if strategy == "v2_lite" or strategy == "PULLBACK_V2_LITE":
        return -2.0
    elif strategy == "midterm" or strategy == "MIDTERM":
        return -7.0
    else:
        return -2.0  # 기본값

def is_trading_day(date_str):
    """거래일 여부 확인"""
    if isinstance(date_str, str):
        date_obj = yyyymmdd_to_date(date_str.replace('-', '')[:8])
    else:
        date_obj = date_str
    
    if isinstance(date_obj, datetime):
        date_obj = date_obj.date()
    
    kr_holidays = holidays.SouthKorea(years=date_obj.year)
    return date_obj.weekday() < 5 and date_obj not in kr_holidays

def find_first_stop_loss_date(ticker, anchor_date, anchor_close, stop_loss_pct, end_date):
    """첫 손절 조건 만족일 찾기 (손절 기준에 가장 가까운 날짜)"""
    try:
        # anchor_date부터 end_date까지의 일별 가격 조회
        days_diff = (end_date - anchor_date).days
        df = api.get_ohlcv(ticker, days_diff + 30, end_date.strftime('%Y%m%d'))
        
        if df.empty:
            return None, None, None
        
        # 날짜 컬럼 정리
        if 'date' in df.columns:
            df['date_str'] = df['date'].astype(str).str.replace('-', '').str[:8]
            df = df.sort_values('date_str')
        else:
            return None, None, None
        
        # anchor_date 이후 데이터만 필터링
        anchor_date_str = anchor_date.strftime('%Y%m%d')
        df_filtered = df[df['date_str'] >= anchor_date_str].copy()
        
        if df_filtered.empty:
            return None, None, None
        
        # 각 날짜별 손익률 계산
        best_date = None
        best_price = None
        best_return = None
        min_diff = float('inf')
        
        for idx, row_data in df_filtered.iterrows():
            date_str = row_data['date_str']
            close = float(row_data['close']) if 'close' in row_data else None
            
            if not close:
                continue
            
            # 손익률 계산
            return_pct = ((close - anchor_close) / anchor_close) * 100
            
            # 손절 조건 만족 확인
            if return_pct <= stop_loss_pct:
                # 손절 기준과의 차이 계산
                diff = abs(return_pct - stop_loss_pct)
                
                # 손절 기준에 가장 가까운 날짜 찾기
                if diff < min_diff:
                    min_diff = diff
                    best_date = date_str
                    best_price = close
                    best_return = return_pct
        
        if best_date:
            return best_date, best_price, best_return
        
        return None, None, None
        
    except Exception as e:
        print(f"    ❌ 오류: {e}")
        return None, None, None

def fix_archived_stop_loss_violations(dry_run=True):
    """ARCHIVED 데이터 중 손절 정책 위반 항목 수정"""
    try:
        with db_manager.get_cursor(commit=False) as cur:
            # 손실이 -7%를 넘는 ARCHIVED 항목 조회
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
                    r.archive_return_pct,
                    r.archive_reason,
                    r.archive_price
                FROM recommendations r
                WHERE r.status = 'ARCHIVED'
                AND r.scanner_version = 'v3'
                AND r.archive_return_pct IS NOT NULL
                AND r.archive_return_pct < -7.0
                ORDER BY r.archive_return_pct ASC
            """)
            
            rows = cur.fetchall()
            
            if not rows:
                print("수정할 항목이 없습니다.")
                return
            
            print(f"수정 대상: {len(rows)}개")
            if dry_run:
                print("⚠️ DRY RUN 모드: 실제 업데이트는 수행하지 않습니다.\n")
            else:
                print("✅ 실제 업데이트를 수행합니다.\n")
            print("=" * 150)
            
            update_count = 0
            skip_count = 0
            error_count = 0
            
            for row in rows:
                rec_id, ticker, name, anchor_date, anchor_close, strategy, broken_at, \
                broken_return_pct, archive_return_pct, archive_reason, archive_price = row
                
                stop_loss_pct = get_stop_loss_pct(strategy)
                archive_return_pct_float = float(archive_return_pct) if archive_return_pct else None
                anchor_close_float = float(anchor_close) if anchor_close else None
                
                print(f"\n[{update_count + skip_count + error_count + 1}/{len(rows)}] {ticker} ({name if name else 'N/A'})")
                print(f"  전략: {strategy} (손절 기준: {stop_loss_pct}%)")
                print(f"  현재 archive_return_pct: {archive_return_pct_float:.2f}%")
                
                if not anchor_close_float:
                    print("  ⚠️ anchor_close가 없어 건너뜀")
                    skip_count += 1
                    continue
                
                # anchor_date 파싱
                if isinstance(anchor_date, str):
                    anchor_date_obj = yyyymmdd_to_date(anchor_date.replace('-', '')[:8])
                else:
                    anchor_date_obj = anchor_date
                
                if isinstance(anchor_date_obj, datetime):
                    anchor_date_obj = anchor_date_obj.date()
                
                # broken_at 파싱 (end_date로 사용)
                if isinstance(broken_at, str):
                    broken_at_obj = yyyymmdd_to_date(broken_at.replace('-', '')[:8])
                elif broken_at:
                    broken_at_obj = broken_at.date() if isinstance(broken_at, datetime) else broken_at
                else:
                    broken_at_obj = get_kst_now().date()
                
                # 첫 손절 조건 만족일 찾기
                print(f"  첫 손절 조건 만족일 찾는 중...")
                first_stop_loss_date, first_stop_loss_price, first_stop_loss_return = find_first_stop_loss_date(
                    ticker, anchor_date_obj, anchor_close_float, stop_loss_pct, broken_at_obj
                )
                
                if not first_stop_loss_date:
                    print("  ⚠️ 첫 손절 조건 만족일을 찾을 수 없음 (건너뜀)")
                    skip_count += 1
                    continue
                
                print(f"  ✅ 첫 손절 조건 만족일: {first_stop_loss_date} (손익률: {first_stop_loss_return:.2f}%)")
                
                # 손절 기준과 비교 (손절 기준보다 낮으면 손절 기준 값 사용)
                if first_stop_loss_return < stop_loss_pct:
                    # 손절 기준보다 낮게 떨어진 경우, 손절 기준 값 사용
                    print(f"  ⚠️ 손절 기준({stop_loss_pct}%)보다 낮음 ({first_stop_loss_return:.2f}%), 손절 기준 값 사용")
                    new_broken_return_pct = round(stop_loss_pct, 2)
                    # 손절 기준에 맞는 가격 계산
                    new_broken_price = round(anchor_close_float * (1 + stop_loss_pct / 100), 0)
                else:
                    # 손절 기준 근처면 실제 손익률 사용
                    new_broken_return_pct = round(first_stop_loss_return, 2)
                    new_broken_price = first_stop_loss_price
                
                # 업데이트할 값 계산
                new_archive_return_pct = new_broken_return_pct  # 정책: broken_return_pct를 archive_return_pct로 사용
                new_broken_at = first_stop_loss_date
                new_archive_price = round(anchor_close_float * (1 + new_archive_return_pct / 100), 0)
                
                print(f"  업데이트 내용:")
                print(f"    broken_at: {broken_at} → {new_broken_at}")
                print(f"    broken_return_pct: {broken_return_pct:.2f}% → {new_broken_return_pct:.2f}%")
                print(f"    archive_return_pct: {archive_return_pct_float:.2f}% → {new_archive_return_pct:.2f}%")
                print(f"    archive_price: {archive_price} → {new_archive_price}")
                
                if not dry_run:
                    # 실제 업데이트
                    try:
                        with db_manager.get_cursor(commit=True) as update_cur:
                            update_cur.execute("""
                                UPDATE recommendations
                                SET broken_at = %s,
                                    broken_return_pct = %s,
                                    archive_return_pct = %s,
                                    archive_price = %s,
                                    updated_at = NOW()
                                WHERE recommendation_id = %s
                            """, (
                                new_broken_at,
                                new_broken_return_pct,
                                new_archive_return_pct,
                                new_archive_price,
                                rec_id
                            ))
                        print(f"  ✅ 업데이트 완료")
                        update_count += 1
                    except Exception as e:
                        print(f"  ❌ 업데이트 실패: {e}")
                        error_count += 1
                else:
                    print(f"  [DRY RUN] 업데이트 예정")
                    update_count += 1
                
                print("-" * 150)
            
            # 결과 출력
            print(f"\n\n[결과]")
            print(f"  전체 항목: {len(rows)}개")
            print(f"  업데이트: {update_count}개")
            print(f"  건너뜀: {skip_count}개")
            print(f"  오류: {error_count}개")
            
            if dry_run:
                print(f"\n⚠️ DRY RUN 모드였습니다. 실제 업데이트를 수행하려면 dry_run=False로 실행하세요.")
            
            return {
                'total': len(rows),
                'updated': update_count,
                'skipped': skip_count,
                'errors': error_count
            }
            
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == '__main__':
    import sys
    
    # 명령줄 인자로 dry_run 모드 제어
    dry_run = True
    if len(sys.argv) > 1 and sys.argv[1] == '--execute':
        dry_run = False
        print("⚠️ 실제 업데이트를 수행합니다!\n")
    else:
        print("⚠️ DRY RUN 모드입니다. 실제 업데이트를 수행하려면 --execute 옵션을 사용하세요.\n")
    
    fix_archived_stop_loss_violations(dry_run=dry_run)


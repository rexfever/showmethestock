#!/usr/bin/env python3
"""
스캔된 종목의 가격 정보를 검증하는 스크립트
DB에 저장된 가격과 키움 API의 실제 가격을 비교
"""
import sys
import os
from datetime import datetime, timedelta, date
import time

# 프로젝트 루트 디렉토리를 PYTHONPATH에 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from kiwoom_api import api
from db_manager import db_manager
import pytz
import holidays

def is_trading_day(check_date: str = None):
    """거래일인지 확인 (주말과 공휴일 제외)"""
    
    if check_date:
        # 지정된 날짜 확인
        try:
            if len(check_date) == 8 and check_date.isdigit():  # YYYYMMDD 형식
                date_str = f"{check_date[:4]}-{check_date[4:6]}-{check_date[6:8]}"
                check_dt = datetime.strptime(date_str, '%Y-%m-%d').date()
            elif len(check_date) == 10 and check_date.count('-') == 2:  # YYYY-MM-DD 형식
                check_dt = datetime.strptime(check_date, '%Y-%m-%d').date()
            else:
                return False
        except:
            return False
    else:
        # 오늘 날짜 확인
        kst = pytz.timezone('Asia/Seoul')
        check_dt = datetime.now(kst).date()
    
    # 주말 체크
    if check_dt.weekday() >= 5:  # 토요일(5), 일요일(6)
        return False
    
    # 한국 공휴일 체크
    kr_holidays = holidays.SouthKorea()
    if check_dt in kr_holidays:
        return False
    
    return True


def validate_scan_prices(date_limit=None, max_records=None, tolerance_percent=1.0, tolerance_amount=100, fix_mismatches=False):
    """
    스캔된 종목의 가격 정보 검증
    
    Args:
        date_limit: 검증할 최근 날짜 수 (None이면 최근 30일)
        max_records: 검증할 최대 레코드 수 (None이면 전체)
        tolerance_percent: 허용 오차율 (%)
        tolerance_amount: 허용 오차 금액 (원)
        fix_mismatches: True면 불일치 레코드를 자동으로 수정
    """
    print("=" * 80)
    print("🔍 스캔된 종목의 가격 정보 검증")
    print("=" * 80)
    print(f"허용 오차: ±{tolerance_percent}% 또는 ±{tolerance_amount:,}원")
    print()
    
    # 검증할 데이터 조회
    with db_manager.get_cursor(commit=False) as cur:
        if date_limit:
            # 최근 N일 데이터만 조회
            date_threshold = (datetime.now() - timedelta(days=date_limit)).strftime('%Y-%m-%d')
            query = """
                SELECT date, code, name, current_price, close_price
                FROM scan_rank
                WHERE date >= %s
                  AND code != 'NORESULT'
                  AND (current_price IS NOT NULL AND current_price > 0)
                ORDER BY date DESC, code
            """
            if max_records:
                query += f" LIMIT {max_records}"
            cur.execute(query, (date_threshold,))
        else:
            # 최근 30일 데이터만 기본 조회
            date_threshold = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            query = """
                SELECT date, code, name, current_price, close_price
                FROM scan_rank
                WHERE date >= %s
                  AND code != 'NORESULT'
                  AND (current_price IS NOT NULL AND current_price > 0)
                ORDER BY date DESC, code
            """
            if max_records:
                query += f" LIMIT {max_records}"
            cur.execute(query, (date_threshold,))
        
        rows = cur.fetchall()
    
    if not rows:
        print("❌ 검증할 데이터가 없습니다.")
        return
    
    print(f"📊 검증 대상: {len(rows)}개 레코드")
    print()
    
    # 날짜별로 그룹화
    by_date = {}
    for row in rows:
        if isinstance(row, dict):
            date_val = row['date']
            code = row['code']
            name = row['name']
            db_price = row['current_price'] or row['close_price']
        else:
            date_val = row[0]
            code = row[1]
            name = row[2]
            db_price = row[3] or row[4]
        
        if date_val not in by_date:
            by_date[date_val] = []
        by_date[date_val].append((code, name, db_price))
    
    print(f"📅 날짜별 분류: {len(by_date)}개 날짜")
    print()
    
    # 검증 통계
    total_checked = 0
    valid_count = 0
    invalid_count = 0
    error_count = 0
    skipped_count = 0
    
    invalid_records = []
    
    # 날짜순으로 처리 (최신 날짜부터)
    for date_str in sorted(by_date.keys(), reverse=True):
        codes = by_date[date_str]
        print(f"📅 {date_str}: {len(codes)}개 종목 검증 중...")
        
        # 날짜 형식 변환 (YYYY-MM-DD -> YYYYMMDD)
        try:
            if hasattr(date_str, 'strftime'):
                date_formatted = date_str.strftime('%Y%m%d')
            elif isinstance(date_str, str):
                if '-' in date_str:
                    date_formatted = date_str.replace('-', '')
                else:
                    date_formatted = date_str
            else:
                date_formatted = str(date_str).replace('-', '')
        except Exception as e:
            print(f"  ⚠️ 날짜 형식 오류: {date_str}, 건너뜀")
            skipped_count += len(codes)
            continue
        
        # 거래일 체크
        if not is_trading_day(date_formatted):
            print(f"  ⚠️ 거래일이 아닙니다: {date_str}, 건너뜀")
            skipped_count += len(codes)
            continue
        
        # 각 종목 검증
        for code, name, db_price in codes:
            total_checked += 1
            print(f"  🔍 {code} ({name}): DB 가격 {db_price:,.0f}원", end="")
            
            try:
                # 키움 API로 해당 날짜의 종가 조회 (base_dt 파라미터 사용)
                df = api.get_ohlcv(code, count=250, base_dt=date_formatted)
                
                if df.empty:
                    print(f" ❌ API 데이터 없음")
                    error_count += 1
                    invalid_records.append({
                        'date': date_str,
                        'code': code,
                        'name': name,
                        'db_price': db_price,
                        'api_price': None,
                        'error': 'API 데이터 없음'
                    })
                    time.sleep(0.2)
                    continue
                
                # 해당 날짜의 종가 찾기
                api_price = None
                
                # 날짜 형식 정규화 함수
                def normalize_date(date_val):
                    """날짜를 YYYYMMDD 형식으로 정규화"""
                    try:
                        if hasattr(date_val, 'strftime'):
                            return date_val.strftime('%Y%m%d')
                        elif isinstance(date_val, str):
                            return date_val.replace('-', '').replace('/', '')[:8]
                        else:
                            return str(date_val).replace('-', '').replace('/', '')[:8]
                    except:
                        return None
                
                target_date = normalize_date(date_formatted)
                
                # 정확히 일치하는 날짜 찾기
                for _, row in df.iterrows():
                    try:
                        row_date = normalize_date(row['date'])
                        if row_date and row_date == target_date:
                            api_price = float(row['close'])
                            break
                    except:
                        continue
                
                # 정확히 일치하는 날짜가 없으면 가장 가까운 날짜 사용
                if api_price is None and not df.empty:
                    closest_row = None
                    min_date_diff = None
                    
                    for _, row in df.iterrows():
                        try:
                            row_date_str = normalize_date(row['date'])
                            if not row_date_str or not target_date:
                                continue
                            
                            # 날짜 차이 계산 (YYYYMMDD 형식 문자열을 날짜 객체로 변환)
                            try:
                                row_date_obj = datetime.strptime(row_date_str, '%Y%m%d').date()
                                target_date_obj = datetime.strptime(target_date, '%Y%m%d').date()
                                date_diff = abs((row_date_obj - target_date_obj).days)
                                
                                if min_date_diff is None or date_diff < min_date_diff:
                                    min_date_diff = date_diff
                                    closest_row = row
                            except:
                                continue
                        except:
                            continue
                    
                    if closest_row is not None:
                        api_price = float(closest_row['close'])
                
                if api_price is None or api_price <= 0:
                    print(f" ❌ API 가격 없음")
                    error_count += 1
                    invalid_records.append({
                        'date': date_str,
                        'code': code,
                        'name': name,
                        'db_price': db_price,
                        'api_price': None,
                        'error': 'API 가격 없음'
                    })
                    time.sleep(0.2)
                    continue
                
                # 가격 비교
                diff = abs(db_price - api_price)
                diff_percent = (diff / api_price * 100) if api_price > 0 else 0
                
                is_valid = (diff_percent <= tolerance_percent) or (diff <= tolerance_amount)
                
                if is_valid:
                    print(f" ✅ API: {api_price:,.0f}원 (차이: {diff:,.0f}원, {diff_percent:.2f}%)")
                    valid_count += 1
                else:
                    print(f" ❌ API: {api_price:,.0f}원 (차이: {diff:,.0f}원, {diff_percent:.2f}%)", end="")
                    invalid_count += 1
                    invalid_records.append({
                        'date': date_str,
                        'code': code,
                        'name': name,
                        'db_price': db_price,
                        'api_price': api_price,
                        'diff': diff,
                        'diff_percent': diff_percent,
                        'error': None
                    })
                    
                    # 불일치 수정 옵션이 켜져 있으면 자동 수정
                    if fix_mismatches:
                        try:
                            with db_manager.get_cursor(commit=True) as cur_fix:
                                cur_fix.execute("""
                                    UPDATE scan_rank
                                    SET current_price = %s,
                                        close_price = %s
                                    WHERE date = %s AND code = %s
                                """, (api_price, api_price, date_str, code))
                            
                            if cur_fix.rowcount > 0:
                                print(f" → ✅ 수정됨 (DB: {db_price:,.0f}원 → API: {api_price:,.0f}원)")
                                invalid_count -= 1  # 수정되었으므로 불일치에서 제외
                                valid_count += 1  # 정상으로 변경
                                invalid_records[-1]['fixed'] = True
                            else:
                                print(f" → ⚠️ 수정 실패 (레코드 없음)")
                        except Exception as fix_error:
                            print(f" → ❌ 수정 오류: {str(fix_error)}")
                    else:
                        print()
                
                # API 호출 제한 고려
                time.sleep(0.2)
                
            except Exception as e:
                import traceback
                error_detail = f"{str(e)}\n{traceback.format_exc()}"
                print(f" ❌ 오류: {str(e)}")
                error_count += 1
                invalid_records.append({
                    'date': date_str,
                    'code': code,
                    'name': name,
                    'db_price': db_price,
                    'api_price': None,
                    'error': error_detail
                })
                time.sleep(1)  # 오류 시 더 긴 지연
        
        print()
    
    # 결과 요약
    print("=" * 80)
    print("📊 검증 결과 요약")
    print("=" * 80)
    print(f"✅ 정상: {valid_count}개 ({valid_count/total_checked*100:.1f}%)" if total_checked > 0 else "✅ 정상: 0개")
    print(f"❌ 불일치: {invalid_count}개 ({invalid_count/total_checked*100:.1f}%)" if total_checked > 0 else "❌ 불일치: 0개")
    print(f"⚠️ 오류: {error_count}개 ({error_count/total_checked*100:.1f}%)" if total_checked > 0 else "⚠️ 오류: 0개")
    print(f"⏭️ 건너뜀: {skipped_count}개")
    print(f"📊 총 검증: {total_checked}개")
    print()
    
    # 불일치 레코드 상세 리포트 (수정되지 않은 것만 표시)
    unfixed_records = [r for r in invalid_records if not r.get('fixed', False)]
    if unfixed_records:
        print("=" * 80)
        print("❌ 불일치 또는 오류 레코드 상세")
        print("=" * 80)
        for record in unfixed_records[:20]:  # 최대 20개만 표시
            if record.get('error'):
                print(f"📅 {record['date']} | {record['code']} ({record['name']})")
                print(f"   DB 가격: {record['db_price']:,.0f}원")
                print(f"   오류: {record['error']}")
            else:
                print(f"📅 {record['date']} | {record['code']} ({record['name']})")
                print(f"   DB 가격: {record['db_price']:,.0f}원")
                print(f"   API 가격: {record['api_price']:,.0f}원")
                print(f"   차이: {record['diff']:,.0f}원 ({record['diff_percent']:.2f}%)")
            print()
        
        if len(unfixed_records) > 20:
            print(f"... 외 {len(unfixed_records) - 20}개 레코드")
        print()
    
    # 통계 요약
    if invalid_count > 0 and invalid_records:
        unfixed_records = [r for r in invalid_records if not r.get('fixed', False) and r.get('diff') is not None]
        if unfixed_records:
            avg_diff = sum(r.get('diff', 0) for r in unfixed_records) / len(unfixed_records)
            max_diff = max((r.get('diff', 0) for r in unfixed_records), default=0)
            print(f"📊 불일치 평균 차이: {avg_diff:,.0f}원")
            print(f"📊 불일치 최대 차이: {max_diff:,.0f}원")
        
        if fix_mismatches:
            fixed_count = sum(1 for r in invalid_records if r.get('fixed', False))
            if fixed_count > 0:
                print(f"🔧 수정된 레코드: {fixed_count}개")
        print()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="스캔된 종목의 가격 정보 검증")
    parser.add_argument("--date-limit", type=int, help="검증할 최근 날짜 수 (기본: 30일)")
    parser.add_argument("--max-records", type=int, help="검증할 최대 레코드 수")
    parser.add_argument("--tolerance-percent", type=float, default=1.0, help="허용 오차율 %% (기본: 1.0%%)")
    parser.add_argument("--tolerance-amount", type=int, default=100, help="허용 오차 금액 원 (기본: 100원)")
    parser.add_argument("--fix", action="store_true", help="불일치 레코드를 자동으로 수정")
    
    args = parser.parse_args()
    
    validate_scan_prices(
        date_limit=args.date_limit,
        max_records=args.max_records,
        tolerance_percent=args.tolerance_percent,
        tolerance_amount=args.tolerance_amount,
        fix_mismatches=args.fix
    )


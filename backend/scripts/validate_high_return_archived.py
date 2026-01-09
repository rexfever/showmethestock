"""
ARCHIVED 종목 중 수익률이 20% 이상인 종목들의 유효성 검사
"""
import sys
import os
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
os.chdir(backend_dir)

from db_manager import db_manager
from date_helper import yyyymmdd_to_date
from kiwoom_api import api
import json
from datetime import datetime

def validate_high_return_archived():
    """수익률 20% 이상인 ARCHIVED 종목 검증"""
    try:
        with db_manager.get_cursor(commit=False) as cur:
            # 수익률 20% 이상인 ARCHIVED 종목 조회
            cur.execute("""
                SELECT 
                    r.recommendation_id,
                    r.ticker,
                    r.name,
                    r.anchor_date,
                    r.anchor_close,
                    r.broken_at,
                    r.broken_return_pct,
                    r.status_changed_at,
                    r.archived_at,
                    r.archive_return_pct,
                    r.archive_price,
                    r.archive_phase,
                    r.archive_reason,
                    r.replaced_by_recommendation_id
                FROM recommendations r
                WHERE r.status = 'ARCHIVED'
                AND r.scanner_version = 'v3'
                AND r.archive_return_pct >= 20.0
                ORDER BY r.archive_return_pct DESC
            """)
            
            rows = cur.fetchall()
            
            if not rows:
                print("수익률 20% 이상인 ARCHIVED 종목이 없습니다.")
                return
            
            print(f"총 {len(rows)}개의 수익률 20% 이상 ARCHIVED 종목 발견\n")
            print("=" * 150)
            
            valid_count = 0
            invalid_count = 0
            needs_fix_count = 0
            
            for idx, row in enumerate(rows, 1):
                rec_id = row[0]
                ticker = row[1]
                name = row[2]
                anchor_date = row[3]
                anchor_close = row[4]
                broken_at = row[5]
                broken_return_pct = row[6]
                status_changed_at = row[7]
                archived_at = row[8]
                archive_return_pct = row[9]
                archive_price = row[10]
                archive_phase = row[11]
                archive_reason = row[12]
                replaced_by_id = row[13]
                
                print(f"\n[{idx}] 추천 ID: {rec_id}")
                print(f"    종목: {ticker} ({name})")
                print(f"    추천일: {anchor_date}")
                print(f"    추천 시점 가격: {anchor_close:,.0f}원")
                print(f"    ARCHIVED 수익률: {archive_return_pct:,.2f}%")
                print(f"    ARCHIVED 가격: {archive_price:,.0f}원" if archive_price else "    ARCHIVED 가격: None")
                print(f"    ARCHIVED 사유: {archive_reason}")
                
                issues = []
                expected_return_pct = None
                expected_price = None
                
                # 1. archive_reason에 따른 검증
                if archive_reason == 'REPLACED':
                    print(f"    → REPLACED 케이스: status_changed_at 시점 스냅샷 사용해야 함")
                    if status_changed_at:
                        # status_changed_at 시점의 가격 조회
                        if isinstance(status_changed_at, str):
                            changed_date = yyyymmdd_to_date(status_changed_at.replace('-', '')[:8])
                        elif isinstance(status_changed_at, datetime):
                            changed_date = status_changed_at.date()
                        else:
                            changed_date = status_changed_at
                        
                        changed_date_str = changed_date.strftime('%Y%m%d')
                        
                        try:
                            df = api.get_ohlcv(ticker, 10, changed_date_str)
                            if not df.empty:
                                if 'date' in df.columns:
                                    df['date_str'] = df['date'].astype(str).str.replace('-', '').str[:8]
                                    df_filtered = df[df['date_str'] == changed_date_str]
                                    if not df_filtered.empty:
                                        expected_price = float(df_filtered.iloc[-1]['close'])
                                    else:
                                        df_sorted = df.sort_values('date_str')
                                        df_before = df_sorted[df_sorted['date_str'] <= changed_date_str]
                                        if not df_before.empty:
                                            expected_price = float(df_before.iloc[-1]['close'])
                                        else:
                                            expected_price = float(df.iloc[-1]['close']) if 'close' in df.columns else float(df.iloc[-1].values[0])
                                else:
                                    expected_price = float(df.iloc[-1]['close']) if 'close' in df.columns else float(df.iloc[-1].values[0])
                                
                                if expected_price and anchor_close:
                                    anchor_close_float = float(anchor_close)
                                    expected_return_pct = round(((expected_price - anchor_close_float) / anchor_close_float) * 100, 2)
                                    print(f"    REPLACED 시점 가격 (OHLCV): {expected_price:,.0f}원")
                                    print(f"    REPLACED 시점 수익률 (계산): {expected_return_pct:,.2f}%")
                                    
                                    if abs(expected_return_pct - float(archive_return_pct)) > 0.01:
                                        issues.append(f"REPLACED 시점 수익률 불일치: 저장={archive_return_pct:,.2f}%, 계산={expected_return_pct:,.2f}%")
                        except Exception as e:
                            issues.append(f"OHLCV 조회 실패: {e}")
                    else:
                        issues.append("status_changed_at이 없음")
                
                elif archive_reason == 'NO_MOMENTUM' or archive_reason == 'TTL_EXPIRED':
                    if broken_at and broken_return_pct is not None:
                        print(f"    → BROKEN을 거친 케이스: BROKEN 시점 스냅샷 사용해야 함")
                        print(f"    BROKEN 시점: {broken_at}")
                        print(f"    BROKEN 시점 수익률: {broken_return_pct}%")
                        
                        # BROKEN 시점의 스냅샷 사용
                        expected_return_pct = round(float(broken_return_pct), 2)
                        if anchor_close:
                            anchor_close_float = float(anchor_close)
                            expected_price = round(anchor_close_float * (1 + expected_return_pct / 100), 0)
                        
                        print(f"    예상 수익률 (BROKEN 스냅샷): {expected_return_pct:,.2f}%")
                        print(f"    예상 가격 (BROKEN 스냅샷): {expected_price:,.0f}원" if expected_price else "    예상 가격: None")
                        
                        if abs(expected_return_pct - float(archive_return_pct)) > 0.01:
                            issues.append(f"BROKEN 시점 수익률 불일치: 저장={archive_return_pct:,.2f}%, BROKEN={broken_return_pct}%")
                    else:
                        # BROKEN을 거치지 않은 경우, ARCHIVED 시점의 가격 사용
                        print(f"    → BROKEN을 거치지 않은 케이스: ARCHIVED 시점 가격 사용")
                        if archived_at and archive_price and anchor_close:
                            anchor_close_float = float(anchor_close)
                            expected_return_pct = round(((float(archive_price) - anchor_close_float) / anchor_close_float) * 100, 2)
                            print(f"    계산된 수익률: {expected_return_pct:,.2f}%")
                            
                            if abs(expected_return_pct - float(archive_return_pct)) > 0.01:
                                issues.append(f"계산된 수익률 불일치: 저장={archive_return_pct:,.2f}%, 계산={expected_return_pct:,.2f}%")
                
                # 2. archive_price와 archive_return_pct의 일관성 검증
                if archive_price and anchor_close:
                    anchor_close_float = float(anchor_close)
                    calculated_from_price = round(((float(archive_price) - anchor_close_float) / anchor_close_float) * 100, 2)
                    if abs(calculated_from_price - float(archive_return_pct)) > 0.01:
                        issues.append(f"가격-수익률 불일치: archive_price로 계산={calculated_from_price:,.2f}%, 저장된 수익률={archive_return_pct:,.2f}%")
                
                # 3. 비정상적으로 높은 수익률 검증 (100% 이상)
                if archive_return_pct >= 100.0:
                    print(f"    ⚠️  수익률이 100% 이상입니다. 실제 가격 변동 확인 필요")
                    # 실제 가격 변동 확인
                    if anchor_close and archive_price:
                        price_multiplier = float(archive_price) / float(anchor_close)
                        print(f"    가격 배수: {price_multiplier:.2f}배")
                        if price_multiplier > 5.0:
                            issues.append(f"가격 배수가 비정상적으로 높음: {price_multiplier:.2f}배")
                
                if issues:
                    print(f"\n    ❌ 문제 발견:")
                    for issue in issues:
                        print(f"      - {issue}")
                    invalid_count += 1
                    if expected_return_pct and abs(expected_return_pct - float(archive_return_pct)) > 0.01:
                        needs_fix_count += 1
                else:
                    print(f"\n    ✅ 유효한 데이터")
                    valid_count += 1
                
                print("-" * 150)
            
            print(f"\n[검증 결과]")
            print(f"  유효: {valid_count}개")
            print(f"  문제 발견: {invalid_count}개")
            print(f"  수정 필요: {needs_fix_count}개")
            print(f"  총: {len(rows)}개")
                
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("ARCHIVED 종목 수익률 검증 시작 (20% 이상)...")
    print("=" * 150)
    validate_high_return_archived()
    print("\n완료!")



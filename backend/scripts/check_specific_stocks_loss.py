"""
특정 종목들의 손실률 확인 및 문제 진단
"""
import sys
import os
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
os.chdir(backend_dir)

from db_manager import db_manager
from datetime import datetime

def check_specific_stocks_loss():
    """특정 종목들의 손실률 확인"""
    try:
        with db_manager.get_cursor(commit=False) as cur:
            # 한중엔시스, 대주전자재료 관련 종목 찾기
            cur.execute("""
                SELECT DISTINCT ticker, name
                FROM recommendations
                WHERE scanner_version = 'v3'
                AND (name LIKE '%한중%' OR name LIKE '%대주%' OR name LIKE '%엔시스%' OR name LIKE '%전자재료%')
                ORDER BY ticker
            """)
            
            tickers = cur.fetchall()
            
            if not tickers:
                print("해당 종목을 찾을 수 없습니다.")
                return
            
            print(f"찾은 종목: {len(tickers)}개\n")
            for ticker_row in tickers:
                print(f"  {ticker_row[0]}: {ticker_row[1]}")
            
            print("\n" + "=" * 150)
            
            for ticker_row in tickers:
                ticker = ticker_row[0]
                name = ticker_row[1]
                
                print(f"\n[{ticker}] {name}")
                print("=" * 150)
                
                # 해당 종목의 모든 추천 이력 조회
                cur.execute("""
                    SELECT 
                        recommendation_id,
                        anchor_date,
                        anchor_close,
                        strategy,
                        status,
                        broken_at,
                        broken_return_pct,
                        status_changed_at,
                        archived_at,
                        archive_return_pct,
                        archive_price,
                        archive_phase,
                        archive_reason,
                        reason
                    FROM recommendations
                    WHERE ticker = %s
                    AND scanner_version = 'v3'
                    ORDER BY anchor_date DESC, created_at DESC
                """, (ticker,))
                
                rows = cur.fetchall()
                
                if not rows:
                    print("  데이터 없음")
                    continue
                
                for idx, row in enumerate(rows, 1):
                    rec_id = row[0]
                    anchor_date = row[1]
                    anchor_close = row[2]
                    strategy = row[3]
                    status = row[4]
                    broken_at = row[5]
                    broken_return_pct = row[6]
                    status_changed_at = row[7]
                    archived_at = row[8]
                    archive_return_pct = row[9]
                    archive_price = row[10]
                    archive_phase = row[11]
                    archive_reason = row[12]
                    reason = row[13]
                    
                    print(f"\n  [{idx}] 추천 ID: {rec_id}")
                    print(f"      상태: {status}")
                    print(f"      추천일: {anchor_date}")
                    print(f"      추천 시점 가격: {anchor_close:,.0f}원")
                    print(f"      전략: {strategy}")
                    
                    # 전략별 손절 조건 확인
                    stop_loss = 0.02  # 기본값
                    if strategy == "v2_lite" or strategy == "PULLBACK_V2_LITE":
                        stop_loss = 0.02
                    elif strategy == "midterm" or strategy == "MIDTERM":
                        stop_loss = 0.07
                    stop_loss_pct = -abs(float(stop_loss) * 100)
                    
                    if status == 'ARCHIVED':
                        print(f"      ARCHIVED 수익률: {archive_return_pct:,.2f}%" if archive_return_pct else "      ARCHIVED 수익률: None")
                        print(f"      ARCHIVED 가격: {archive_price:,.0f}원" if archive_price else "      ARCHIVED 가격: None")
                        print(f"      ARCHIVED 사유: {archive_reason}")
                        print(f"      ARCHIVED 단계: {archive_phase}")
                        print(f"      BROKEN 시점: {broken_at}")
                        print(f"      BROKEN 수익률: {broken_return_pct}%")
                        print(f"      BROKEN 사유: {reason}")
                        
                        # 문제 분석
                        issues = []
                        
                        if archive_return_pct is not None:
                            archive_return_pct_float = float(archive_return_pct)
                            
                            # 손절 조건 체크
                            if archive_return_pct_float <= stop_loss_pct:
                                if archive_reason != 'NO_MOMENTUM':
                                    issues.append(f"손절 조건 만족({archive_return_pct_float:.2f}% <= {stop_loss_pct:.2f}%)인데 archive_reason이 '{archive_reason}'입니다. NO_MOMENTUM이어야 합니다.")
                            
                            # BROKEN을 거쳤는지 확인
                            if broken_at and broken_return_pct is not None:
                                broken_return_pct_float = float(broken_return_pct)
                                if abs(archive_return_pct_float - broken_return_pct_float) > 0.01:
                                    issues.append(f"BROKEN 시점 스냅샷 불일치: archive_return_pct={archive_return_pct_float:.2f}%, broken_return_pct={broken_return_pct_float:.2f}%")
                            elif broken_at is None and archive_return_pct_float <= stop_loss_pct:
                                issues.append(f"손절 조건 만족했는데 BROKEN을 거치지 않았습니다. (broken_at=None)")
                        
                        if issues:
                            print(f"\n      ⚠️  문제:")
                            for issue in issues:
                                print(f"        - {issue}")
                        else:
                            print(f"\n      ✅ 정상")
                    
                    elif status in ('ACTIVE', 'WEAK_WARNING'):
                        print(f"      현재 상태: {status}")
                        print(f"      ⚠️  ACTIVE 상태입니다. 현재 손실률 확인 필요")
                    
                    print("-" * 150)
                
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("특정 종목 손실률 확인...")
    print("=" * 150)
    check_specific_stocks_loss()
    print("\n완료!")



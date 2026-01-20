"""
특정 종목들의 상태 확인
"""
import sys
import os
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
os.chdir(backend_dir)

from db_manager import db_manager

def check_stocks_status(tickers):
    """특정 종목들의 상태 확인"""
    try:
        with db_manager.get_cursor(commit=False) as cur:
            for ticker in tickers:
                print(f"\n[{ticker}] 상태 확인")
                print("=" * 100)
                
                # 해당 종목의 모든 추천 이력 조회
                cur.execute("""
                    SELECT 
                        recommendation_id,
                        ticker,
                        name,
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
                    LIMIT 5
                """, (ticker,))
                
                rows = cur.fetchall()
                
                if not rows:
                    print("  데이터 없음")
                    continue
                
                for idx, row in enumerate(rows, 1):
                    rec_id = row[0]
                    name = row[2]
                    anchor_date = row[3]
                    anchor_close = row[4]
                    strategy = row[5]
                    status = row[6]
                    broken_at = row[7]
                    broken_return_pct = row[8]
                    status_changed_at = row[9]
                    archived_at = row[10]
                    archive_return_pct = row[11]
                    archive_price = row[12]
                    archive_phase = row[13]
                    archive_reason = row[14]
                    reason = row[15]
                    
                    print(f"\n  [{idx}] 추천 ID: {rec_id}")
                    print(f"      종목명: {name}")
                    print(f"      상태: {status}")
                    print(f"      추천일: {anchor_date}, 가격: {anchor_close:,.0f}원")
                    print(f"      전략: {strategy}")
                    
                    # 전략별 손절 조건 확인
                    stop_loss = 0.02  # 기본값
                    if strategy == "v2_lite" or strategy == "PULLBACK_V2_LITE":
                        stop_loss = 0.02
                    elif strategy == "midterm" or strategy == "MIDTERM":
                        stop_loss = 0.07
                    stop_loss_pct = -abs(float(stop_loss) * 100)
                    
                    issues = []
                    
                    if status == 'ARCHIVED':
                        print(f"      ARCHIVED 수익률: {archive_return_pct:,.2f}%" if archive_return_pct else "      ARCHIVED 수익률: None")
                        print(f"      ARCHIVED 가격: {archive_price:,.0f}원" if archive_price else "      ARCHIVED 가격: None")
                        print(f"      ARCHIVED 사유: {archive_reason}")
                        print(f"      ARCHIVED 단계: {archive_phase}")
                        print(f"      BROKEN 시점: {broken_at}")
                        print(f"      BROKEN 수익률: {broken_return_pct}%")
                        print(f"      BROKEN 사유: {reason}")
                        
                        # 문제 분석
                        if archive_return_pct is not None:
                            archive_return_pct_float = float(archive_return_pct)
                            
                            # 1. BROKEN을 거친 경우: broken_return_pct와 일치해야 함
                            if broken_at and broken_return_pct is not None:
                                broken_return_pct_float = float(broken_return_pct)
                                if abs(archive_return_pct_float - broken_return_pct_float) > 0.01:
                                    issues.append(f"BROKEN 스냅샷 불일치: archive_return_pct={archive_return_pct_float:.2f}%, broken_return_pct={broken_return_pct_float:.2f}%")
                            
                            # 2. broken_at이 None인데 broken_return_pct가 있는 경우
                            elif broken_at is None and broken_return_pct is not None:
                                broken_return_pct_float = float(broken_return_pct)
                                if abs(archive_return_pct_float - broken_return_pct_float) > 0.01:
                                    issues.append(f"broken_at=None인데 broken_return_pct와 불일치: archive_return_pct={archive_return_pct_float:.2f}%, broken_return_pct={broken_return_pct_float:.2f}%")
                            
                            # 3. 손절 조건 체크
                            if archive_return_pct_float <= stop_loss_pct:
                                if archive_reason != 'NO_MOMENTUM':
                                    issues.append(f"손절 조건 만족({archive_return_pct_float:.2f}% <= {stop_loss_pct:.2f}%)인데 archive_reason이 '{archive_reason}'입니다. NO_MOMENTUM이어야 합니다.")
                        
                        # 4. archive_return_pct가 None인 경우
                        if archive_return_pct is None:
                            issues.append("archive_return_pct가 None입니다.")
                        
                        # 5. archive_price가 None인 경우
                        if archive_price is None:
                            issues.append("archive_price가 None입니다.")
                    
                    elif status in ('ACTIVE', 'WEAK_WARNING'):
                        print(f"      BROKEN 시점: {broken_at}")
                        print(f"      BROKEN 수익률: {broken_return_pct}%")
                        print(f"      사유: {reason}")
                        print(f"      ⚠️  ACTIVE 상태입니다. 현재 손실률 확인 필요")
                    
                    elif status == 'BROKEN':
                        print(f"      BROKEN 시점: {broken_at}")
                        print(f"      BROKEN 수익률: {broken_return_pct}%")
                        print(f"      사유: {reason}")
                    
                    if issues:
                        print(f"\n      ⚠️  문제:")
                        for issue in issues:
                            print(f"        - {issue}")
                    else:
                        print(f"\n      ✅ 정상")
                    
                    print("-" * 100)
                
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import sys
    
    # 기본 종목: 대주전자재료
    tickers = ['078600']
    
    # 오스코텍 티커 찾기
    from db_manager import db_manager
    with db_manager.get_cursor(commit=False) as cur:
        cur.execute("""
            SELECT DISTINCT ticker
            FROM recommendations
            WHERE scanner_version = 'v3'
            AND (name LIKE '%오스코%' OR name LIKE '%OSCO%' OR name LIKE '%osco%')
            LIMIT 1
        """)
        row = cur.fetchone()
        if row:
            tickers.append(row[0])
            print(f"오스코텍 티커: {row[0]}")
    
    print(f"\n확인할 종목: {tickers}")
    print("=" * 100)
    check_stocks_status(tickers)


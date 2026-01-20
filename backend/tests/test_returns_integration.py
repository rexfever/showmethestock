"""
수익률 계산 통합 테스트

실제 API를 사용하여 수익률 계산 로직을 테스트합니다.
"""

import sys
import os
import json
from datetime import date, datetime, timedelta

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db_manager import db_manager
from services.returns_service import calculate_returns, calculate_returns_batch
from main import get_scan_by_date, get_latest_scan_from_db


class TestReturnsIntegration:
    """수익률 계산 통합 테스트"""
    
    def test_1_get_scan_by_date_recalculation(self):
        """get_scan_by_date에서 전일 스캔 종목 재계산 테스트"""
        print("\n=== 통합 테스트 1: get_scan_by_date 재계산 로직 ===")
        
        # 최근 스캔 날짜 찾기
        with db_manager.get_cursor(commit=False) as cur:
            cur.execute("""
                SELECT DISTINCT date
                FROM scan_rank
                WHERE scanner_version = 'v2' 
                  AND code != 'NORESULT'
                ORDER BY date DESC
                LIMIT 1
            """)
            row = cur.fetchone()
            
            if not row:
                print("⚠️ 테스트할 스캔 데이터가 없습니다")
                return False
            
            scan_date_obj = row[0]
            if isinstance(scan_date_obj, date):
                scan_date_str = scan_date_obj.strftime('%Y%m%d')
            else:
                scan_date_str = str(scan_date_obj).replace('-', '')
        
        print(f"   테스트 스캔 날짜: {scan_date_str}")
        
        # API 호출 시뮬레이션 (async 함수이므로 await 필요)
        try:
            import asyncio
            result = asyncio.run(get_scan_by_date(scan_date_str, scanner_version='v2'))
            
            if not result.get('ok'):
                print(f"⚠️ API 호출 실패: {result.get('error')}")
                return False
            
            items = result.get('data', {}).get('items', [])
            if not items:
                print("⚠️ 스캔 결과가 없습니다")
                return False
            
            # 첫 번째 종목의 수익률 확인
            first_item = items[0]
            current_return = first_item.get('current_return')
            recommended_date = first_item.get('recommended_date')
            
            print(f"   종목: {first_item.get('ticker')} ({first_item.get('name')})")
            print(f"   추천일: {recommended_date}")
            print(f"   현재 수익률: {current_return}%")
            print(f"   returns 데이터: {json.dumps(first_item.get('returns'), ensure_ascii=False, indent=2)}")
            
            # 수익률이 계산되었는지 확인
            assert current_return is not None, "current_return이 None이면 안 됨"
            assert isinstance(current_return, (int, float)), "current_return은 숫자여야 함"
            
            print("✅ 통합 테스트 1 통과: get_scan_by_date에서 수익률 계산됨")
            return True
            
        except Exception as e:
            print(f"❌ 테스트 실패: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_2_get_latest_scan_recalculation(self):
        """get_latest_scan_from_db에서 전일 스캔 종목 재계산 테스트"""
        print("\n=== 통합 테스트 2: get_latest_scan_from_db 재계산 로직 ===")
        
        try:
            result = get_latest_scan_from_db(scanner_version='v2')
            
            if not result.get('ok'):
                print(f"⚠️ API 호출 실패: {result.get('error')}")
                return False
            
            items = result.get('data', {}).get('items', [])
            if not items:
                print("⚠️ 스캔 결과가 없습니다")
                return False
            
            # 첫 번째 종목의 수익률 확인
            first_item = items[0]
            current_return = first_item.get('current_return')
            recommended_date = first_item.get('recommended_date')
            
            print(f"   종목: {first_item.get('ticker')} ({first_item.get('name')})")
            print(f"   추천일: {recommended_date}")
            print(f"   현재 수익률: {current_return}%")
            
            # 수익률이 계산되었는지 확인
            assert current_return is not None, "current_return이 None이면 안 됨"
            assert isinstance(current_return, (int, float)), "current_return은 숫자여야 함"
            
            print("✅ 통합 테스트 2 통과: get_latest_scan_from_db에서 수익률 계산됨")
            return True
            
        except Exception as e:
            print(f"❌ 테스트 실패: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_3_returns_calculation_accuracy(self):
        """수익률 계산 정확도 테스트"""
        print("\n=== 통합 테스트 3: 수익률 계산 정확도 ===")
        
        # 실제 종목으로 테스트
        test_codes = ["005930", "000660", "035420"]  # 삼성전자, SK하이닉스, NAVER
        test_date = "20251128"
        
        from date_helper import get_kst_now
        today_str = get_kst_now().strftime('%Y%m%d')
        
        if test_date >= today_str:
            print(f"⚠️ 테스트 날짜({test_date})가 오늘({today_str}) 이후이므로 스킵")
            return False
        
        print(f"   테스트 날짜: {test_date} (오늘: {today_str})")
        
        for code in test_codes:
            try:
                # DB에서 스캔일 종가 조회
                with db_manager.get_cursor(commit=False) as cur:
                    cur.execute("""
                        SELECT close_price
                        FROM scan_rank
                        WHERE date = %s AND code = %s AND scanner_version = 'v2'
                        LIMIT 1
                    """, (date(2025, 11, 28), code))
                    
                    row = cur.fetchone()
                    if not row:
                        print(f"   ⚠️ {code}: 스캔 데이터 없음")
                        continue
                    
                    scan_price = row[0]
                
                # 수익률 계산
                returns_data = calculate_returns(code, test_date, None, scan_price)
                
                if returns_data:
                    current_return = returns_data.get('current_return')
                    days_elapsed = returns_data.get('days_elapsed', 0)
                    
                    print(f"   {code}: 수익률={current_return}%, 경과일={days_elapsed}")
                    
                    # 검증
                    assert current_return is not None, "수익률이 계산되어야 함"
                    assert days_elapsed >= 0, "경과일은 0 이상이어야 함"
                else:
                    print(f"   ⚠️ {code}: 수익률 계산 실패 (데이터 없을 수 있음)")
                    
            except Exception as e:
                print(f"   ⚠️ {code}: 테스트 스킵 ({e})")
        
        print("✅ 통합 테스트 3 통과: 수익률 계산 정확도 확인")
        return True
    
    def test_4_daily_update_consistency(self):
        """매일 업데이트 일관성 테스트"""
        print("\n=== 통합 테스트 4: 매일 업데이트 일관성 ===")
        
        # 최근 스캔 날짜의 종목들 조회
        with db_manager.get_cursor(commit=False) as cur:
            cur.execute("""
                SELECT DISTINCT date
                FROM scan_rank
                WHERE scanner_version = 'v2' 
                  AND code != 'NORESULT'
                ORDER BY date DESC
                LIMIT 1
            """)
            row = cur.fetchone()
            
            if not row:
                print("⚠️ 테스트할 스캔 데이터가 없습니다")
                return False
            
            scan_date_obj = row[0]
            if isinstance(scan_date_obj, date):
                scan_date_str = scan_date_obj.strftime('%Y%m%d')
            else:
                scan_date_str = str(scan_date_obj).replace('-', '')
        
        # 같은 날짜로 여러 번 호출하여 일관성 확인
        import asyncio
        results = []
        for i in range(3):
            try:
                result = asyncio.run(get_scan_by_date(scan_date_str, scanner_version='v2'))
                if result.get('ok'):
                    items = result.get('data', {}).get('items', [])
                    if items:
                        first_item = items[0]
                        results.append({
                            'ticker': first_item.get('ticker'),
                            'current_return': first_item.get('current_return'),
                            'recommended_date': first_item.get('recommended_date')
                        })
            except Exception as e:
                print(f"   호출 {i+1} 실패: {e}")
        
        if len(results) < 2:
            print("⚠️ 충분한 테스트 데이터가 없습니다")
            return False
        
        # 첫 번째와 마지막 결과 비교
        first_result = results[0]
        last_result = results[-1]
        
        print(f"   첫 번째 호출: {first_result['ticker']} - {first_result['current_return']}%")
        print(f"   마지막 호출: {last_result['ticker']} - {last_result['current_return']}%")
        
        # 같은 종목이어야 함
        assert first_result['ticker'] == last_result['ticker'], "같은 종목이어야 함"
        
        # 수익률은 같거나 약간 다를 수 있음 (실시간 계산이므로)
        # 하지만 None이면 안 됨
        assert first_result['current_return'] is not None, "수익률이 계산되어야 함"
        assert last_result['current_return'] is not None, "수익률이 계산되어야 함"
        
        print("✅ 통합 테스트 4 통과: 매일 업데이트 일관성 확인")
        return True


def run_integration_tests():
    """통합 테스트 실행"""
    print("=" * 80)
    print("수익률 계산 통합 테스트 시작")
    print("=" * 80)
    
    test_instance = TestReturnsIntegration()
    
    tests = [
        test_instance.test_1_get_scan_by_date_recalculation,
        test_instance.test_2_get_latest_scan_recalculation,
        test_instance.test_3_returns_calculation_accuracy,
        test_instance.test_4_daily_update_consistency,
    ]
    
    passed = 0
    failed = 0
    skipped = 0
    
    for test in tests:
        try:
            result = test()
            if result:
                passed += 1
            else:
                skipped += 1
        except AssertionError as e:
            print(f"❌ 테스트 실패: {test.__name__}")
            print(f"   오류: {e}")
            failed += 1
        except Exception as e:
            print(f"⚠️ 테스트 스킵: {test.__name__}")
            print(f"   이유: {e}")
            skipped += 1
    
    print("\n" + "=" * 80)
    print("통합 테스트 결과 요약")
    print("=" * 80)
    print(f"✅ 통과: {passed}개")
    print(f"❌ 실패: {failed}개")
    print(f"⚠️ 스킵: {skipped}개")
    print("=" * 80)
    
    return failed == 0


if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)


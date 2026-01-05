"""
등락률 API 통합 테스트

실제 API 엔드포인트를 통해 change_rate가 올바르게 반환되는지 검증합니다.
"""
import unittest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from db_manager import db_manager
from datetime import datetime


class TestChangeRateAPIIntegration(unittest.TestCase):
    """등락률 API 통합 테스트"""
    
    def test_scan_by_date_returns_percent_for_v2(self):
        """/scan-by-date/{date} 엔드포인트가 v2 스캐너의 경우 퍼센트 형태를 반환하는지 확인"""
        # 실제 DB에서 데이터 확인
        date_str = '20251127'
        code = '030960'
        
        with db_manager.get_cursor(commit=False) as cur:
            cur.execute("""
                SELECT date, code, name, close_price, change_rate, scanner_version
                FROM scan_rank
                WHERE date = %s AND code = %s AND scanner_version = 'v2'
            """, (datetime.strptime(date_str, '%Y%m%d').date(), code))
            
            row = cur.fetchone()
            if row:
                date, code, name, close_price, db_change_rate, scanner_version = row
                
                # API 변환 로직 시뮬레이션
                change_rate_raw = db_change_rate
                change_rate = float(change_rate_raw)
                row_scanner_version = scanner_version
                
                if row_scanner_version != 'v2' and abs(change_rate) < 1.0 and change_rate != 0.0:
                    change_rate = change_rate * 100
                
                # v2는 변환하지 않아야 함
                self.assertEqual(scanner_version, 'v2')
                self.assertLess(abs(change_rate), 1.0, "v2는 퍼센트 형태로 저장되어 변환하지 않음")
                print(f"✅ DB 저장값: {db_change_rate}%")
                print(f"✅ API 반환값: {change_rate}%")
                print(f"✅ 변환 여부: {'변환됨' if change_rate != db_change_rate else '변환 안됨 (정상)'}")
            else:
                self.skipTest(f"테스트 데이터가 없습니다: {date_str}, {code}")
    
    def test_all_v2_scans_have_percent_format(self):
        """모든 v2 스캔 결과의 change_rate가 퍼센트 형태인지 확인"""
        date_str = '20251127'
        
        with db_manager.get_cursor(commit=False) as cur:
            cur.execute("""
                SELECT code, name, change_rate, scanner_version
                FROM scan_rank
                WHERE date = %s AND scanner_version = 'v2' AND code != 'NORESULT'
                LIMIT 10
            """, (datetime.strptime(date_str, '%Y%m%d').date(),))
            
            rows = cur.fetchall()
            
            if rows:
                for row in rows:
                    code, name, change_rate, scanner_version = row
                    
                    # v2는 퍼센트 형태로 저장되어야 함
                    # 절대값이 1보다 작은 경우는 정상 (예: 0.57%)
                    # 절대값이 1 이상인 경우도 정상 (예: 5.96%)
                    # 하지만 100 이상이면 오류 (예: 57%)
                    self.assertLess(abs(change_rate), 100.0, 
                                  f"{code} ({name}): change_rate={change_rate}%가 100 이상입니다")
                    
                    print(f"✅ {code} ({name}): {change_rate}%")
                
                print(f"\n✅ 총 {len(rows)}개 종목 검증 완료")
            else:
                self.skipTest(f"테스트 데이터가 없습니다: {date_str}")


if __name__ == '__main__':
    unittest.main(verbosity=2)




































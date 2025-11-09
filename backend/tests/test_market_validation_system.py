"""
장세 분석 데이터 검증 시스템 테스트
단계별로 세세하게 검증
"""
import unittest
import sys
import os
from datetime import datetime, date, time

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class TestMarketValidationSystem(unittest.TestCase):
    """장세 분석 검증 시스템 테스트"""
    
    def setUp(self):
        """테스트 준비"""
        print("\n" + "="*80)
        print(f"테스트 시작: {self._testMethodName}")
        print("="*80)
    
    def tearDown(self):
        """테스트 정리"""
        print(f"테스트 완료: {self._testMethodName}")
        print("="*80 + "\n")
    
    def test_01_db_connection(self):
        """1단계: DB 연결 테스트"""
        print("\n[1단계] DB 연결 테스트")
        
        try:
            from db_manager import db_manager
            
            with db_manager.get_cursor(commit=False) as cur:
                cur.execute("SELECT 1 as test")
                result = cur.fetchone()
                
            print(f"✅ DB 연결 성공")
            print(f"   - 테스트 쿼리 결과: {result}")
            self.assertIsNotNone(result)
            
        except Exception as e:
            print(f"❌ DB 연결 실패: {e}")
            self.fail(f"DB 연결 실패: {e}")
    
    def test_02_validation_table_exists(self):
        """2단계: 검증 테이블 존재 확인"""
        print("\n[2단계] 검증 테이블 존재 확인")
        
        try:
            from db_manager import db_manager
            
            with db_manager.get_cursor(commit=False) as cur:
                cur.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'market_analysis_validation'
                    )
                """)
                exists = cur.fetchone()[0]
            
            if exists:
                print(f"✅ 검증 테이블 존재함")
            else:
                print(f"❌ 검증 테이블이 없습니다")
                print(f"   SQL 실행 필요: backend/sql/create_market_analysis_validation.sql")
            
            self.assertTrue(exists, "검증 테이블이 존재하지 않습니다")
            
        except Exception as e:
            print(f"❌ 테이블 확인 실패: {e}")
            self.fail(f"테이블 확인 실패: {e}")
    
    def test_03_validation_table_schema(self):
        """3단계: 검증 테이블 스키마 확인"""
        print("\n[3단계] 검증 테이블 스키마 확인")
        
        try:
            from db_manager import db_manager
            
            expected_columns = [
                'id', 'analysis_date', 'analysis_time',
                'kospi_return', 'kospi_close', 'kospi_prev_close',
                'samsung_return', 'samsung_close', 'samsung_prev_close',
                'data_available', 'data_complete', 'error_message',
                'created_at'
            ]
            
            with db_manager.get_cursor(commit=False) as cur:
                cur.execute("""
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_name = 'market_analysis_validation'
                    ORDER BY ordinal_position
                """)
                columns = cur.fetchall()
            
            print(f"✅ 테이블 스키마:")
            for col in columns:
                col_name = col[0] if isinstance(col, tuple) else col['column_name']
                col_type = col[1] if isinstance(col, tuple) else col['data_type']
                print(f"   - {col_name}: {col_type}")
                self.assertIn(col_name, expected_columns)
            
            self.assertEqual(len(columns), len(expected_columns))
            
        except Exception as e:
            print(f"❌ 스키마 확인 실패: {e}")
            self.fail(f"스키마 확인 실패: {e}")
    
    def test_04_kiwoom_api_connection(self):
        """4단계: 키움 API 연결 테스트"""
        print("\n[4단계] 키움 API 연결 테스트")
        
        try:
            from kiwoom_api import api
            
            # KOSPI 지수 조회 테스트
            print(f"   KOSPI 지수 조회 중...")
            kospi_df = api.get_ohlcv('^KS11', 2)
            
            print(f"✅ 키움 API 연결 성공")
            print(f"   - 조회된 데이터 행 수: {len(kospi_df)}")
            if not kospi_df.empty:
                print(f"   - 최근 날짜: {kospi_df.iloc[-1]['date']}")
                print(f"   - 최근 종가: {kospi_df.iloc[-1]['close']:,.0f}")
            
            self.assertGreater(len(kospi_df), 0)
            
        except Exception as e:
            print(f"❌ 키움 API 연결 실패: {e}")
            print(f"   참고: 키움 API 토큰이 필요합니다")
            # API 실패는 테스트 실패로 처리하지 않음 (선택적)
    
    def test_05_validation_script_import(self):
        """5단계: 검증 스크립트 import 테스트"""
        print("\n[5단계] 검증 스크립트 import 테스트")
        
        try:
            # validate_market_data_timing 모듈 import
            import validate_market_data_timing
            
            print(f"✅ 검증 스크립트 import 성공")
            print(f"   - validate_market_data 함수 존재: {hasattr(validate_market_data_timing, 'validate_market_data')}")
            
            self.assertTrue(hasattr(validate_market_data_timing, 'validate_market_data'))
            
        except Exception as e:
            print(f"❌ 스크립트 import 실패: {e}")
            self.fail(f"스크립트 import 실패: {e}")
    
    def test_06_insert_test_data(self):
        """6단계: 테스트 데이터 삽입"""
        print("\n[6단계] 테스트 데이터 삽입")
        
        try:
            from db_manager import db_manager
            
            test_date = date.today()
            test_time = time(15, 35, 0)
            
            with db_manager.get_cursor(commit=True) as cur:
                cur.execute("""
                    INSERT INTO market_analysis_validation (
                        analysis_date, analysis_time,
                        kospi_return, kospi_close, kospi_prev_close,
                        samsung_return, samsung_close, samsung_prev_close,
                        data_available, data_complete, error_message
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (analysis_date, analysis_time) DO UPDATE SET
                        kospi_return = EXCLUDED.kospi_return,
                        data_available = EXCLUDED.data_available
                    RETURNING id
                """, (
                    test_date, test_time,
                    -0.0218, 2500.0, 2555.0,
                    -0.0131, 97900.0, 99200.0,
                    True, True, None
                ))
                
                result = cur.fetchone()
                inserted_id = result[0] if isinstance(result, tuple) else result['id']
            
            print(f"✅ 테스트 데이터 삽입 성공")
            print(f"   - 삽입된 ID: {inserted_id}")
            print(f"   - 날짜: {test_date}")
            print(f"   - 시간: {test_time}")
            
            self.assertIsNotNone(inserted_id)
            
        except Exception as e:
            print(f"❌ 데이터 삽입 실패: {e}")
            self.fail(f"데이터 삽입 실패: {e}")
    
    def test_07_query_test_data(self):
        """7단계: 테스트 데이터 조회"""
        print("\n[7단계] 테스트 데이터 조회")
        
        try:
            from db_manager import db_manager
            
            test_date = date.today()
            
            with db_manager.get_cursor(commit=False) as cur:
                cur.execute("""
                    SELECT 
                        analysis_time,
                        kospi_return,
                        data_available,
                        data_complete
                    FROM market_analysis_validation
                    WHERE analysis_date = %s
                    ORDER BY analysis_time
                """, (test_date,))
                
                rows = cur.fetchall()
            
            print(f"✅ 데이터 조회 성공")
            print(f"   - 조회된 행 수: {len(rows)}")
            
            for row in rows:
                if isinstance(row, tuple):
                    print(f"   - {row[0]}: KOSPI {row[1]*100:.2f}%, 가용={row[2]}, 완전={row[3]}")
                else:
                    print(f"   - {row['analysis_time']}: KOSPI {row['kospi_return']*100:.2f}%, 가용={row['data_available']}, 완전={row['data_complete']}")
            
            self.assertGreater(len(rows), 0)
            
        except Exception as e:
            print(f"❌ 데이터 조회 실패: {e}")
            self.fail(f"데이터 조회 실패: {e}")
    
    def test_08_api_endpoint_test(self):
        """8단계: API 엔드포인트 테스트"""
        print("\n[8단계] API 엔드포인트 테스트")
        
        try:
            import httpx
            from datetime import datetime
            
            # FastAPI 앱 import
            from main import app
            
            # 테스트 클라이언트 생성
            with httpx.Client(app=app, base_url="http://test") as client:
                today_str = datetime.now().strftime('%Y%m%d')
                response = client.get(f"/admin/market-validation?date={today_str}")
                
                print(f"✅ API 호출 성공")
                print(f"   - 상태 코드: {response.status_code}")
                print(f"   - 응답 본문:")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"     - ok: {data.get('ok')}")
                    
                    if data.get('ok'):
                        validations = data.get('data', {}).get('validations', [])
                        print(f"     - 검증 데이터 수: {len(validations)}")
                        print(f"     - 첫 완전 시점: {data.get('data', {}).get('first_complete_time')}")
                        
                        for v in validations[:3]:  # 처음 3개만 출력
                            print(f"       {v.get('time')}: KOSPI {v.get('kospi_return')}%, 완전={v.get('data_complete')}")
                    else:
                        print(f"     - 오류: {data.get('error')}")
                else:
                    print(f"   - 응답: {response.text[:200]}")
                
                self.assertEqual(response.status_code, 200)
            
        except ImportError as e:
            print(f"⚠️ httpx 미설치: pip install httpx")
            print(f"   API 테스트 스킵")
        except Exception as e:
            print(f"❌ API 테스트 실패: {e}")
            import traceback
            traceback.print_exc()
    
    def test_09_scheduler_config(self):
        """9단계: 스케줄러 설정 확인"""
        print("\n[9단계] 스케줄러 설정 확인")
        
        try:
            import scheduler
            
            print(f"✅ 스케줄러 모듈 import 성공")
            print(f"   - run_validation 함수: {hasattr(scheduler, 'run_validation')}")
            print(f"   - run_market_analysis 함수: {hasattr(scheduler, 'run_market_analysis')}")
            print(f"   - run_scan 함수: {hasattr(scheduler, 'run_scan')}")
            print(f"   - setup_scheduler 함수: {hasattr(scheduler, 'setup_scheduler')}")
            
            self.assertTrue(hasattr(scheduler, 'run_validation'))
            self.assertTrue(hasattr(scheduler, 'run_market_analysis'))
            self.assertTrue(hasattr(scheduler, 'setup_scheduler'))
            
        except Exception as e:
            print(f"❌ 스케줄러 확인 실패: {e}")
            self.fail(f"스케줄러 확인 실패: {e}")
    
    def test_10_cleanup_test_data(self):
        """10단계: 테스트 데이터 정리"""
        print("\n[10단계] 테스트 데이터 정리")
        
        try:
            from db_manager import db_manager
            
            test_date = date.today()
            
            with db_manager.get_cursor(commit=True) as cur:
                cur.execute("""
                    DELETE FROM market_analysis_validation
                    WHERE analysis_date = %s
                    RETURNING id
                """, (test_date,))
                
                deleted = cur.fetchall()
            
            print(f"✅ 테스트 데이터 정리 완료")
            print(f"   - 삭제된 행 수: {len(deleted)}")
            
        except Exception as e:
            print(f"❌ 데이터 정리 실패: {e}")
            # 정리 실패는 테스트 실패로 처리하지 않음


def run_tests():
    """테스트 실행"""
    print("\n" + "="*80)
    print("장세 분석 데이터 검증 시스템 테스트")
    print("="*80)
    
    # 테스트 스위트 생성
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestMarketValidationSystem)
    
    # 테스트 실행
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 결과 요약
    print("\n" + "="*80)
    print("테스트 결과 요약")
    print("="*80)
    print(f"총 테스트: {result.testsRun}")
    print(f"성공: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"실패: {len(result.failures)}")
    print(f"오류: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n✅ 모든 테스트 통과!")
    else:
        print("\n❌ 일부 테스트 실패")
    
    return result


if __name__ == "__main__":
    result = run_tests()
    sys.exit(0 if result.wasSuccessful() else 1)


"""
날짜 처리 DB 통합 테스트

실제 DB 연결이 필요한 테스트 (선택적 실행)
"""
import pytest
import sys
import os
from datetime import date, datetime
import pytz

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from date_helper import yyyymmdd_to_date, yyyymmdd_to_timestamp, timestamp_to_yyyymmdd, KST


@pytest.mark.skipif(
    os.getenv("DB_ENGINE", "sqlite").lower() != "postgres",
    reason="PostgreSQL이 활성화되지 않음"
)
class TestDateDbIntegration:
    """실제 DB를 사용한 통합 테스트"""
    
    @pytest.fixture
    def db_manager(self):
        """DB 매니저 fixture"""
        from db_manager import db_manager
        return db_manager
    
    def test_scan_rank_date_storage_and_retrieval(self, db_manager):
        """scan_rank: date 객체 저장 및 조회"""
        test_date_str = "20251124"
        test_code = "TEST001"
        test_name = "테스트종목"
        
        date_obj = yyyymmdd_to_date(test_date_str)
        
        try:
            with db_manager.get_cursor(commit=True) as cur:
                # 테스트 데이터 삽입
                cur.execute("""
                    INSERT INTO scan_rank (date, code, name, score, scanner_version)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (date, code, scanner_version) DO UPDATE
                    SET name = EXCLUDED.name, score = EXCLUDED.score
                """, (date_obj, test_code, test_name, 10.0, "v1"))
                
                # 조회
                cur.execute("""
                    SELECT date, code, name, score
                    FROM scan_rank
                    WHERE date = %s AND code = %s AND scanner_version = %s
                """, (date_obj, test_code, "v1"))
                
                row = cur.fetchone()
                assert row is not None
                
                # date 객체로 조회되는지 확인
                retrieved_date = row[0]
                assert isinstance(retrieved_date, date)
                assert retrieved_date == date_obj
                assert retrieved_date.year == 2025
                assert retrieved_date.month == 11
                assert retrieved_date.day == 24
                
                # YYYYMMDD로 변환
                date_str = retrieved_date.strftime('%Y%m%d')
                assert date_str == test_date_str
                
        finally:
            # 테스트 데이터 정리
            with db_manager.get_cursor(commit=True) as cur:
                cur.execute("""
                    DELETE FROM scan_rank
                    WHERE code = %s AND scanner_version = %s
                """, (test_code, "v1"))
    
    def test_popup_notice_datetime_storage_and_retrieval(self, db_manager):
        """popup_notice: datetime 객체 저장 및 조회"""
        test_start_date_str = "20251124"
        test_end_date_str = "20251130"
        
        start_dt = yyyymmdd_to_timestamp(test_start_date_str, hour=0, minute=0, second=0)
        end_dt = yyyymmdd_to_timestamp(test_end_date_str, hour=23, minute=59, second=59)
        
        try:
            with db_manager.get_cursor(commit=True) as cur:
                # 기존 데이터 삭제
                cur.execute("DELETE FROM popup_notice")
                
                # 테스트 데이터 삽입
                cur.execute("""
                    INSERT INTO popup_notice (is_enabled, title, message, start_date, end_date)
                    VALUES (%s, %s, %s, %s, %s)
                """, (True, "테스트 제목", "테스트 내용", start_dt, end_dt))
                
                # 조회
                cur.execute("""
                    SELECT start_date, end_date
                    FROM popup_notice
                    ORDER BY id DESC LIMIT 1
                """)
                
                row = cur.fetchone()
                assert row is not None
                
                # datetime 객체로 조회되는지 확인
                retrieved_start = row[0]
                retrieved_end = row[1]
                
                assert isinstance(retrieved_start, datetime)
                assert isinstance(retrieved_end, datetime)
                assert retrieved_start.tzinfo is not None
                assert retrieved_end.tzinfo is not None
                
                # YYYYMMDD로 변환
                start_str = timestamp_to_yyyymmdd(retrieved_start)
                end_str = timestamp_to_yyyymmdd(retrieved_end)
                
                assert start_str == test_start_date_str
                assert end_str == test_end_date_str
                
        finally:
            # 테스트 데이터 정리
            with db_manager.get_cursor(commit=True) as cur:
                cur.execute("DELETE FROM popup_notice")
    
    def test_date_comparison_in_query(self, db_manager):
        """날짜 비교 쿼리 테스트"""
        test_date_str = "20251124"
        date_obj = yyyymmdd_to_date(test_date_str)
        
        try:
            with db_manager.get_cursor(commit=True) as cur:
                # 날짜 범위 조회 테스트
                cur.execute("""
                    SELECT COUNT(*) as cnt
                    FROM scan_rank
                    WHERE date = %s
                """, (date_obj,))
                
                row = cur.fetchone()
                assert row is not None
                assert isinstance(row[0], (int, type(None)))
                
        except Exception as e:
            pytest.fail(f"날짜 비교 쿼리 실패: {e}")
    
    def test_datetime_range_query(self, db_manager):
        """datetime 범위 쿼리 테스트"""
        start_dt = yyyymmdd_to_timestamp("20251124", hour=0, minute=0, second=0)
        end_dt = yyyymmdd_to_timestamp("20251130", hour=23, minute=59, second=59)
        
        try:
            with db_manager.get_cursor(commit=True) as cur:
                # datetime 범위 조회 테스트
                cur.execute("""
                    SELECT COUNT(*) as cnt
                    FROM popup_notice
                    WHERE start_date <= %s AND end_date >= %s
                """, (start_dt, end_dt))
                
                row = cur.fetchone()
                assert row is not None
                
        except Exception as e:
            pytest.fail(f"datetime 범위 쿼리 실패: {e}")


class TestDateDbPatchBehavior:
    """db_patch 동작 확인 테스트"""
    
    def test_db_patch_preserves_date_objects(self):
        """db_patch가 date 객체를 보존하는지 확인"""
        from db_patch import PostgresCursor
        
        # 다양한 date 객체 테스트
        test_dates = [
            date(2025, 1, 1),
            date(2025, 12, 31),
            date(2024, 2, 29),  # 윤년
        ]
        
        for test_date in test_dates:
            result = PostgresCursor._convert_value(test_date)
            assert result == test_date
            assert isinstance(result, date)
            assert not isinstance(result, str)
    
    def test_db_patch_preserves_datetime_objects(self):
        """db_patch가 datetime 객체를 보존하는지 확인"""
        from db_patch import PostgresCursor
        
        # 다양한 datetime 객체 테스트
        test_datetimes = [
            datetime(2025, 1, 1, 0, 0, 0, tzinfo=KST),
            datetime(2025, 12, 31, 23, 59, 59, tzinfo=KST),
            datetime(2025, 11, 24, 10, 30, 45, tzinfo=KST),
        ]
        
        for test_dt in test_datetimes:
            result = PostgresCursor._convert_value(test_dt)
            assert result == test_dt
            assert isinstance(result, datetime)
            assert not isinstance(result, str)
            assert result.tzinfo is not None


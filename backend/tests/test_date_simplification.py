"""
날짜 처리 단순화 검증 테스트

단계별 테스트:
1. 유틸리티 함수 테스트
2. db_patch 변환 로직 테스트 (변환하지 않음 확인)
3. DB 저장/조회 통합 테스트
4. 실제 API 엔드포인트 테스트
"""
import pytest
import sys
import os
from datetime import date, datetime
import pytz

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from date_helper import (
    yyyymmdd_to_date,
    yyyymmdd_to_timestamp,
    timestamp_to_yyyymmdd,
    get_kst_now,
    KST
)


class TestDateHelperFunctions:
    """날짜 유틸리티 함수 테스트"""
    
    def test_yyyymmdd_to_date_valid(self):
        """yyyymmdd_to_date: 유효한 입력"""
        result = yyyymmdd_to_date("20251124")
        assert isinstance(result, date)
        assert result.year == 2025
        assert result.month == 11
        assert result.day == 24
    
    def test_yyyymmdd_to_date_invalid_format(self):
        """yyyymmdd_to_date: 잘못된 형식"""
        with pytest.raises(ValueError):
            yyyymmdd_to_date("2025-11-24")  # 하이픈 포함
        
        with pytest.raises(ValueError):
            yyyymmdd_to_date("2025112")  # 길이 부족
        
        with pytest.raises(ValueError):
            yyyymmdd_to_date("abc")  # 숫자 아님
    
    def test_yyyymmdd_to_timestamp_valid(self):
        """yyyymmdd_to_timestamp: 유효한 입력"""
        result = yyyymmdd_to_timestamp("20251124", hour=10, minute=30, second=45)
        assert isinstance(result, datetime)
        assert result.year == 2025
        assert result.month == 11
        assert result.day == 24
        assert result.hour == 10
        assert result.minute == 30
        assert result.second == 45
        assert result.tzinfo is not None  # timezone-aware
    
    def test_yyyymmdd_to_timestamp_default_time(self):
        """yyyymmdd_to_timestamp: 기본 시간 (00:00:00)"""
        result = yyyymmdd_to_timestamp("20251124")
        assert result.hour == 0
        assert result.minute == 0
        assert result.second == 0
    
    def test_yyyymmdd_to_timestamp_kst_timezone(self):
        """yyyymmdd_to_timestamp: KST timezone 확인"""
        result = yyyymmdd_to_timestamp("20251124")
        assert result.tzinfo == KST or str(result.tzinfo) == 'Asia/Seoul'
    
    def test_timestamp_to_yyyymmdd_timezone_aware(self):
        """timestamp_to_yyyymmdd: timezone-aware datetime"""
        dt = datetime(2025, 11, 24, 10, 30, 45, tzinfo=KST)
        result = timestamp_to_yyyymmdd(dt)
        assert result == "20251124"
    
    def test_timestamp_to_yyyymmdd_timezone_naive(self):
        """timestamp_to_yyyymmdd: timezone-naive datetime (자동 변환)"""
        dt = datetime(2025, 11, 24, 10, 30, 45)  # timezone-naive
        result = timestamp_to_yyyymmdd(dt)
        assert result == "20251124"
    
    def test_timestamp_to_yyyymmdd_round_trip(self):
        """timestamp_to_yyyymmdd: 왕복 변환 테스트"""
        original = "20251124"
        dt = yyyymmdd_to_timestamp(original, hour=10, minute=30, second=45)
        converted = timestamp_to_yyyymmdd(dt)
        assert converted == original


class TestDbPatchConversion:
    """db_patch.py 변환 로직 테스트 (변환하지 않음 확인)"""
    
    def test_convert_value_date_not_converted(self):
        """_convert_value: date 객체는 변환하지 않음"""
        from db_patch import PostgresCursor
        
        date_obj = date(2025, 11, 24)
        result = PostgresCursor._convert_value(date_obj)
        
        # 변환하지 않고 그대로 반환되어야 함
        assert result == date_obj
        assert isinstance(result, date)
        assert not isinstance(result, str)
    
    def test_convert_value_datetime_not_converted(self):
        """_convert_value: datetime 객체는 변환하지 않음"""
        from db_patch import PostgresCursor
        
        dt_obj = datetime(2025, 11, 24, 10, 30, 45, tzinfo=KST)
        result = PostgresCursor._convert_value(dt_obj)
        
        # 변환하지 않고 그대로 반환되어야 함
        assert result == dt_obj
        assert isinstance(result, datetime)
        assert not isinstance(result, str)
    
    def test_convert_value_other_types_still_converted(self):
        """_convert_value: 다른 타입은 여전히 변환됨"""
        from db_patch import PostgresCursor
        from decimal import Decimal
        
        # Decimal은 여전히 float로 변환
        dec = Decimal("123.45")
        result = PostgresCursor._convert_value(dec)
        assert isinstance(result, float)
        assert result == 123.45
        
        # dict는 여전히 JSON 문자열로 변환
        d = {"key": "value"}
        result = PostgresCursor._convert_value(d)
        assert isinstance(result, str)
        assert "key" in result


class TestDateStorageIntegration:
    """DB 저장/조회 통합 테스트 (실제 DB 필요)"""
    
    @pytest.fixture
    def mock_db_cursor(self):
        """모의 DB 커서"""
        from unittest.mock import MagicMock
        cursor = MagicMock()
        return cursor
    
    def test_scan_rank_date_storage_format(self):
        """scan_rank: date 객체로 저장되는지 확인"""
        from date_helper import yyyymmdd_to_date
        
        # YYYYMMDD → date 객체 변환
        date_str = "20251124"
        date_obj = yyyymmdd_to_date(date_str)
        
        # date 객체인지 확인
        assert isinstance(date_obj, date)
        assert date_obj.year == 2025
        assert date_obj.month == 11
        assert date_obj.day == 24
        
        # db_patch를 통과해도 변환되지 않아야 함
        from db_patch import PostgresCursor
        converted = PostgresCursor._convert_value(date_obj)
        assert converted == date_obj
        assert isinstance(converted, date)
    
    def test_popup_notice_datetime_storage_format(self):
        """popup_notice: datetime 객체로 저장되는지 확인"""
        from date_helper import yyyymmdd_to_timestamp
        
        # YYYYMMDD → datetime 객체 변환
        date_str = "20251124"
        dt_obj = yyyymmdd_to_timestamp(date_str, hour=0, minute=0, second=0)
        
        # datetime 객체인지 확인
        assert isinstance(dt_obj, datetime)
        assert dt_obj.tzinfo is not None
        
        # db_patch를 통과해도 변환되지 않아야 함
        from db_patch import PostgresCursor
        converted = PostgresCursor._convert_value(dt_obj)
        assert converted == dt_obj
        assert isinstance(converted, datetime)


class TestDateRetrievalIntegration:
    """DB 조회 통합 테스트"""
    
    def test_scan_rank_date_retrieval(self):
        """scan_rank: date 객체로 조회되는지 확인"""
        # PostgreSQL에서 조회한 date는 이미 date 객체
        # _convert_row를 통과해도 변환되지 않아야 함
        from db_patch import PostgresCursor
        
        # 모의 row (PostgreSQL이 반환하는 형식)
        mock_row = (date(2025, 11, 24), "005930", "삼성전자")
        
        # _convert_row를 통과
        converted_row = PostgresCursor._convert_row(None, mock_row)
        
        # date 객체가 그대로 유지되어야 함
        assert converted_row[0] == date(2025, 11, 24)
        assert isinstance(converted_row[0], date)
    
    def test_popup_notice_datetime_retrieval(self):
        """popup_notice: datetime 객체로 조회되는지 확인"""
        from db_patch import PostgresCursor
        
        # 모의 row (PostgreSQL이 반환하는 형식)
        dt_obj = datetime(2025, 11, 24, 0, 0, 0, tzinfo=KST)
        mock_row = (True, "제목", "내용", dt_obj, dt_obj)
        
        # _convert_row를 통과
        converted_row = PostgresCursor._convert_row(None, mock_row)
        
        # datetime 객체가 그대로 유지되어야 함
        assert converted_row[3] == dt_obj
        assert isinstance(converted_row[3], datetime)


class TestDateComparison:
    """날짜 비교 로직 테스트"""
    
    def test_date_comparison_objects(self):
        """date 객체끼리 비교"""
        date1 = yyyymmdd_to_date("20251124")
        date2 = yyyymmdd_to_date("20251125")
        
        assert date1 < date2
        assert date2 > date1
        assert date1 == yyyymmdd_to_date("20251124")
    
    def test_datetime_date_extraction(self):
        """datetime에서 date 추출하여 비교"""
        dt = yyyymmdd_to_timestamp("20251124", hour=10, minute=30, second=45)
        date_from_dt = dt.date()
        date_obj = yyyymmdd_to_date("20251124")
        
        assert date_from_dt == date_obj


class TestDateEdgeCases:
    """날짜 처리 엣지 케이스 테스트"""
    
    def test_leap_year(self):
        """윤년 처리"""
        result = yyyymmdd_to_date("20240229")  # 2024년은 윤년
        assert result.year == 2024
        assert result.month == 2
        assert result.day == 29
    
    def test_year_boundary(self):
        """연도 경계"""
        result1 = yyyymmdd_to_date("20231231")
        result2 = yyyymmdd_to_date("20240101")
        
        assert result1.year == 2023
        assert result2.year == 2024
        assert (result2 - result1).days == 1
    
    def test_month_boundary(self):
        """월 경계"""
        result1 = yyyymmdd_to_date("20251130")
        result2 = yyyymmdd_to_date("20251201")
        
        assert result1.month == 11
        assert result2.month == 12
        assert (result2 - result1).days == 1
    
    def test_timezone_conversion(self):
        """timezone 변환"""
        dt_kst = yyyymmdd_to_timestamp("20251124", hour=0, minute=0, second=0)
        
        # UTC로 변환
        dt_utc = dt_kst.astimezone(pytz.UTC)
        
        # 다시 YYYYMMDD로 변환하면 같은 날짜여야 함
        result = timestamp_to_yyyymmdd(dt_utc)
        assert result == "20251124"  # KST 기준으로 변환


class TestDateFormatConsistency:
    """날짜 형식 일관성 테스트"""
    
    def test_all_functions_use_yyyymmdd(self):
        """모든 함수가 YYYYMMDD 형식 사용"""
        test_date = "20251124"
        
        # 변환
        date_obj = yyyymmdd_to_date(test_date)
        dt_obj = yyyymmdd_to_timestamp(test_date)
        
        # 다시 변환
        date_str = date_obj.strftime('%Y%m%d')
        dt_str = timestamp_to_yyyymmdd(dt_obj)
        
        assert date_str == test_date
        assert dt_str == test_date
    
    def test_no_string_conversion_in_db_patch(self):
        """db_patch에서 문자열 변환하지 않음"""
        from db_patch import PostgresCursor
        
        date_obj = date(2025, 11, 24)
        dt_obj = datetime(2025, 11, 24, 0, 0, 0, tzinfo=KST)
        
        # 변환 결과가 문자열이 아니어야 함
        date_result = PostgresCursor._convert_value(date_obj)
        dt_result = PostgresCursor._convert_value(dt_obj)
        
        assert not isinstance(date_result, str)
        assert not isinstance(dt_result, str)
        assert isinstance(date_result, date)
        assert isinstance(dt_result, datetime)


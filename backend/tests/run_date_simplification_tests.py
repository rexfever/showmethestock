#!/usr/bin/env python3
"""
날짜 처리 단순화 검증 테스트 실행 스크립트

단계별 테스트 실행:
1. 유틸리티 함수 테스트
2. db_patch 변환 로직 테스트
3. 통합 테스트 (선택적)
"""
import sys
import os
from datetime import date, datetime
import traceback

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from date_helper import (
    yyyymmdd_to_date,
    yyyymmdd_to_timestamp,
    timestamp_to_yyyymmdd,
    get_kst_now,
    KST
)


class TestRunner:
    """테스트 실행기"""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def run_test(self, test_name, test_func):
        """단일 테스트 실행"""
        try:
            test_func()
            self.passed += 1
            print(f"✅ {test_name}")
            return True
        except Exception as e:
            self.failed += 1
            error_msg = f"❌ {test_name}: {str(e)}"
            self.errors.append(error_msg)
            print(error_msg)
            traceback.print_exc()
            return False
    
    def print_summary(self):
        """테스트 결과 요약"""
        total = self.passed + self.failed
        print("\n" + "="*60)
        print(f"테스트 결과: {self.passed}/{total} 통과")
        if self.failed > 0:
            print(f"실패: {self.failed}")
            print("\n실패한 테스트:")
            for error in self.errors:
                print(f"  {error}")
        print("="*60)


runner = TestRunner()


# ==================== Step 1: 유틸리티 함수 테스트 ====================

def test_yyyymmdd_to_date_valid():
    """yyyymmdd_to_date: 유효한 입력"""
    result = yyyymmdd_to_date("20251124")
    assert isinstance(result, date), f"date 객체가 아님: {type(result)}"
    assert result.year == 2025, f"연도 불일치: {result.year}"
    assert result.month == 11, f"월 불일치: {result.month}"
    assert result.day == 24, f"일 불일치: {result.day}"


def test_yyyymmdd_to_date_invalid():
    """yyyymmdd_to_date: 잘못된 형식"""
    try:
        yyyymmdd_to_date("2025-11-24")
        assert False, "ValueError가 발생해야 함"
    except ValueError:
        pass
    
    try:
        yyyymmdd_to_date("2025112")
        assert False, "ValueError가 발생해야 함"
    except ValueError:
        pass


def test_yyyymmdd_to_timestamp_valid():
    """yyyymmdd_to_timestamp: 유효한 입력"""
    result = yyyymmdd_to_timestamp("20251124", hour=10, minute=30, second=45)
    assert isinstance(result, datetime), f"datetime 객체가 아님: {type(result)}"
    assert result.year == 2025
    assert result.month == 11
    assert result.day == 24
    assert result.hour == 10
    assert result.minute == 30
    assert result.second == 45
    assert result.tzinfo is not None, "timezone-aware가 아님"


def test_yyyymmdd_to_timestamp_default_time():
    """yyyymmdd_to_timestamp: 기본 시간"""
    result = yyyymmdd_to_timestamp("20251124")
    assert result.hour == 0
    assert result.minute == 0
    assert result.second == 0


def test_timestamp_to_yyyymmdd():
    """timestamp_to_yyyymmdd: 변환 테스트"""
    dt = datetime(2025, 11, 24, 10, 30, 45, tzinfo=KST)
    result = timestamp_to_yyyymmdd(dt)
    assert result == "20251124", f"변환 결과 불일치: {result}"


def test_round_trip_conversion():
    """왕복 변환 테스트"""
    original = "20251124"
    dt = yyyymmdd_to_timestamp(original, hour=10, minute=30, second=45)
    converted = timestamp_to_yyyymmdd(dt)
    assert converted == original, f"왕복 변환 실패: {original} → {converted}"


# ==================== Step 2: db_patch 변환 로직 테스트 ====================

def test_db_patch_date_not_converted():
    """db_patch: date 객체는 변환하지 않음"""
    import db_patch
    
    # USE_POSTGRES가 True일 때만 PostgresCursor 사용 가능
    if not hasattr(db_patch, 'USE_POSTGRES') or not db_patch.USE_POSTGRES:
        # SQLite 모드에서는 테스트 스킵
        return
    
    PostgresCursor = db_patch.PostgresCursor
    
    date_obj = date(2025, 11, 24)
    result = PostgresCursor._convert_value(date_obj)
    
    assert result == date_obj, "date 객체가 변경됨"
    assert isinstance(result, date), f"date 객체가 아님: {type(result)}"
    assert not isinstance(result, str), "문자열로 변환됨 (불필요한 변환)"


def test_db_patch_datetime_not_converted():
    """db_patch: datetime 객체는 변환하지 않음"""
    import db_patch
    
    if not hasattr(db_patch, 'USE_POSTGRES') or not db_patch.USE_POSTGRES:
        return
    
    PostgresCursor = db_patch.PostgresCursor
    
    dt_obj = datetime(2025, 11, 24, 10, 30, 45, tzinfo=KST)
    result = PostgresCursor._convert_value(dt_obj)
    
    assert result == dt_obj, "datetime 객체가 변경됨"
    assert isinstance(result, datetime), f"datetime 객체가 아님: {type(result)}"
    assert not isinstance(result, str), "문자열로 변환됨 (불필요한 변환)"


def test_db_patch_other_types_still_converted():
    """db_patch: 다른 타입은 여전히 변환됨"""
    import db_patch
    from decimal import Decimal
    
    if not hasattr(db_patch, 'USE_POSTGRES') or not db_patch.USE_POSTGRES:
        return
    
    PostgresCursor = db_patch.PostgresCursor
    
    # Decimal은 여전히 float로 변환
    dec = Decimal("123.45")
    result = PostgresCursor._convert_value(dec)
    assert isinstance(result, float), f"float로 변환되지 않음: {type(result)}"
    assert result == 123.45


# ==================== Step 3: 저장/조회 로직 테스트 ====================

def test_scan_rank_date_storage_format():
    """scan_rank: date 객체로 저장되는지 확인"""
    from date_helper import yyyymmdd_to_date
    import db_patch
    
    if not hasattr(db_patch, 'USE_POSTGRES') or not db_patch.USE_POSTGRES:
        return
    
    PostgresCursor = db_patch.PostgresCursor
    
    date_str = "20251124"
    date_obj = yyyymmdd_to_date(date_str)
    
    # date 객체인지 확인
    assert isinstance(date_obj, date)
    
    # db_patch를 통과해도 변환되지 않아야 함
    converted = PostgresCursor._convert_value(date_obj)
    assert converted == date_obj
    assert isinstance(converted, date)
    assert not isinstance(converted, str)


def test_popup_notice_datetime_storage_format():
    """popup_notice: datetime 객체로 저장되는지 확인"""
    from date_helper import yyyymmdd_to_timestamp
    import db_patch
    
    if not hasattr(db_patch, 'USE_POSTGRES') or not db_patch.USE_POSTGRES:
        return
    
    PostgresCursor = db_patch.PostgresCursor
    
    date_str = "20251124"
    dt_obj = yyyymmdd_to_timestamp(date_str, hour=0, minute=0, second=0)
    
    # datetime 객체인지 확인
    assert isinstance(dt_obj, datetime)
    assert dt_obj.tzinfo is not None
    
    # db_patch를 통과해도 변환되지 않아야 함
    converted = PostgresCursor._convert_value(dt_obj)
    assert converted == dt_obj
    assert isinstance(converted, datetime)
    assert not isinstance(converted, str)


# ==================== Step 4: 날짜 비교 테스트 ====================

def test_date_comparison():
    """날짜 비교 테스트"""
    date1 = yyyymmdd_to_date("20251124")
    date2 = yyyymmdd_to_date("20251125")
    
    assert date1 < date2
    assert date2 > date1
    assert date1 == yyyymmdd_to_date("20251124")


def test_datetime_date_extraction():
    """datetime에서 date 추출"""
    dt = yyyymmdd_to_timestamp("20251124", hour=10, minute=30, second=45)
    date_from_dt = dt.date()
    date_obj = yyyymmdd_to_date("20251124")
    
    assert date_from_dt == date_obj


# ==================== Step 5: 엣지 케이스 테스트 ====================

def test_leap_year():
    """윤년 처리"""
    result = yyyymmdd_to_date("20240229")  # 2024년은 윤년
    assert result.year == 2024
    assert result.month == 2
    assert result.day == 29


def test_year_boundary():
    """연도 경계"""
    result1 = yyyymmdd_to_date("20231231")
    result2 = yyyymmdd_to_date("20240101")
    
    assert result1.year == 2023
    assert result2.year == 2024
    assert (result2 - result1).days == 1


def test_timezone_conversion():
    """timezone 변환"""
    dt_kst = yyyymmdd_to_timestamp("20251124", hour=0, minute=0, second=0)
    
    # UTC로 변환
    import pytz
    dt_utc = dt_kst.astimezone(pytz.UTC)
    
    # 다시 YYYYMMDD로 변환하면 같은 날짜여야 함
    result = timestamp_to_yyyymmdd(dt_utc)
    assert result == "20251124"


# ==================== Step 6: 형식 일관성 테스트 ====================

def test_format_consistency():
    """날짜 형식 일관성"""
    test_date = "20251124"
    
    # 변환
    date_obj = yyyymmdd_to_date(test_date)
    dt_obj = yyyymmdd_to_timestamp(test_date)
    
    # 다시 변환
    date_str = date_obj.strftime('%Y%m%d')
    dt_str = timestamp_to_yyyymmdd(dt_obj)
    
    assert date_str == test_date
    assert dt_str == test_date


def test_no_string_conversion_in_db_patch():
    """db_patch에서 문자열 변환하지 않음"""
    import db_patch
    
    if not hasattr(db_patch, 'USE_POSTGRES') or not db_patch.USE_POSTGRES:
        return
    
    PostgresCursor = db_patch.PostgresCursor
    
    date_obj = date(2025, 11, 24)
    dt_obj = datetime(2025, 11, 24, 0, 0, 0, tzinfo=KST)
    
    # 변환 결과가 문자열이 아니어야 함
    date_result = PostgresCursor._convert_value(date_obj)
    dt_result = PostgresCursor._convert_value(dt_obj)
    
    assert not isinstance(date_result, str), "date가 문자열로 변환됨"
    assert not isinstance(dt_result, str), "datetime이 문자열로 변환됨"
    assert isinstance(date_result, date), "date 객체가 아님"
    assert isinstance(dt_result, datetime), "datetime 객체가 아님"


# ==================== 메인 실행 ====================

def main():
    """모든 테스트 실행"""
    print("="*60)
    print("날짜 처리 단순화 검증 테스트")
    print("="*60)
    print()
    
    print("Step 1: 유틸리티 함수 테스트")
    print("-" * 60)
    runner.run_test("yyyymmdd_to_date (유효한 입력)", test_yyyymmdd_to_date_valid)
    runner.run_test("yyyymmdd_to_date (잘못된 형식)", test_yyyymmdd_to_date_invalid)
    runner.run_test("yyyymmdd_to_timestamp (유효한 입력)", test_yyyymmdd_to_timestamp_valid)
    runner.run_test("yyyymmdd_to_timestamp (기본 시간)", test_yyyymmdd_to_timestamp_default_time)
    runner.run_test("timestamp_to_yyyymmdd", test_timestamp_to_yyyymmdd)
    runner.run_test("왕복 변환", test_round_trip_conversion)
    print()
    
    print("Step 2: db_patch 변환 로직 테스트")
    print("-" * 60)
    runner.run_test("db_patch: date 객체 변환하지 않음", test_db_patch_date_not_converted)
    runner.run_test("db_patch: datetime 객체 변환하지 않음", test_db_patch_datetime_not_converted)
    runner.run_test("db_patch: 다른 타입은 여전히 변환", test_db_patch_other_types_still_converted)
    print()
    
    print("Step 3: 저장/조회 로직 테스트")
    print("-" * 60)
    import db_patch
    if hasattr(db_patch, 'USE_POSTGRES') and db_patch.USE_POSTGRES:
        runner.run_test("scan_rank: date 객체 저장 형식", test_scan_rank_date_storage_format)
        runner.run_test("popup_notice: datetime 객체 저장 형식", test_popup_notice_datetime_storage_format)
    else:
        print("⚠️  PostgreSQL이 활성화되지 않아 저장/조회 테스트 스킵")
    print()
    
    print("Step 4: 날짜 비교 테스트")
    print("-" * 60)
    runner.run_test("날짜 객체 비교", test_date_comparison)
    runner.run_test("datetime에서 date 추출", test_datetime_date_extraction)
    print()
    
    print("Step 5: 엣지 케이스 테스트")
    print("-" * 60)
    runner.run_test("윤년 처리", test_leap_year)
    runner.run_test("연도 경계", test_year_boundary)
    runner.run_test("timezone 변환", test_timezone_conversion)
    print()
    
    print("Step 6: 형식 일관성 테스트")
    print("-" * 60)
    runner.run_test("날짜 형식 일관성", test_format_consistency)
    import db_patch
    if hasattr(db_patch, 'USE_POSTGRES') and db_patch.USE_POSTGRES:
        runner.run_test("db_patch에서 문자열 변환하지 않음", test_no_string_conversion_in_db_patch)
    else:
        print("⚠️  PostgreSQL이 활성화되지 않아 db_patch 테스트 스킵")
    print()
    
    runner.print_summary()
    
    return runner.failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)


"""
접속 기록 서비스 테스트
"""
import unittest
from datetime import datetime, date
from unittest.mock import patch, MagicMock
import sys
import os

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.access_log_service import (
    get_daily_visitor_stats,
    get_daily_visitor_stats_by_path,
    get_cumulative_visitor_stats
)


class TestAccessLogService(unittest.TestCase):
    """접속 기록 서비스 테스트"""
    
    def setUp(self):
        """테스트 전 설정"""
        pass
    
    def tearDown(self):
        """테스트 후 정리"""
        pass
    
    @patch('services.access_log_service.db_manager')
    def test_get_daily_visitor_stats_no_params(self, mock_db_manager):
        """일별 방문자 수 조회 - 파라미터 없음"""
        # Mock 설정
        mock_cursor = MagicMock()
        mock_db_manager.get_cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []
        
        # 테스트 실행
        result = get_daily_visitor_stats()
        
        # 검증
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)
        mock_cursor.execute.assert_called_once()
    
    @patch('services.access_log_service.db_manager')
    def test_get_daily_visitor_stats_with_dates(self, mock_db_manager):
        """일별 방문자 수 조회 - 날짜 파라미터 있음"""
        # Mock 설정
        mock_cursor = MagicMock()
        mock_db_manager.get_cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            (date(2025, 12, 4), 10, 25)
        ]
        
        # 테스트 실행
        result = get_daily_visitor_stats(
            start_date=datetime(2025, 12, 4),
            end_date=datetime(2025, 12, 4)
        )
        
        # 검증
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['date'], '2025-12-04')
        self.assertEqual(result[0]['unique_visitors'], 10)
        self.assertEqual(result[0]['total_visits'], 25)
    
    @patch('services.access_log_service.db_manager')
    def test_get_daily_visitor_stats_by_path_no_params(self, mock_db_manager):
        """화면별 일 방문자 수 조회 - 파라미터 없음"""
        # Mock 설정
        mock_cursor = MagicMock()
        mock_db_manager.get_cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []
        
        # 테스트 실행
        result = get_daily_visitor_stats_by_path()
        
        # 검증
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)
        mock_cursor.execute.assert_called_once()
    
    @patch('services.access_log_service.db_manager')
    def test_get_daily_visitor_stats_by_path_with_dates(self, mock_db_manager):
        """화면별 일 방문자 수 조회 - 날짜 파라미터 있음"""
        # Mock 설정
        mock_cursor = MagicMock()
        mock_db_manager.get_cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            (date(2025, 12, 4), '/v2/scanner-v2', 5, 15),
            (date(2025, 12, 4), '/more', 3, 8)
        ]
        
        # 테스트 실행
        result = get_daily_visitor_stats_by_path(
            start_date=datetime(2025, 12, 4),
            end_date=datetime(2025, 12, 4)
        )
        
        # 검증
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['date'], '2025-12-04')
        self.assertEqual(result[0]['path'], '/v2/scanner-v2')
        self.assertEqual(result[0]['unique_visitors'], 5)
        self.assertEqual(result[0]['total_visits'], 15)
        self.assertEqual(result[1]['path'], '/more')
    
    @patch('services.access_log_service.db_manager')
    def test_get_daily_visitor_stats_by_path_result_structure(self, mock_db_manager):
        """화면별 일 방문자 수 조회 - 결과 구조 검증"""
        # Mock 설정
        mock_cursor = MagicMock()
        mock_db_manager.get_cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            (date(2025, 12, 4), '/v2/scanner-v2', 5, 15)
        ]
        
        # 테스트 실행
        result = get_daily_visitor_stats_by_path(
            start_date=datetime(2025, 12, 4),
            end_date=datetime(2025, 12, 4)
        )
        
        # 검증
        self.assertGreater(len(result), 0)
        first_result = result[0]
        required_keys = ['date', 'path', 'unique_visitors', 'total_visits']
        for key in required_keys:
            self.assertIn(key, first_result, f"결과에 '{key}' 키가 없습니다")
    
    @patch('services.access_log_service.db_manager')
    def test_get_daily_visitor_stats_by_path_sql_params(self, mock_db_manager):
        """화면별 일 방문자 수 조회 - SQL 파라미터 검증"""
        # Mock 설정
        mock_cursor = MagicMock()
        mock_db_manager.get_cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []
        
        # 테스트 실행
        get_daily_visitor_stats_by_path(
            start_date=datetime(2025, 12, 4),
            end_date=datetime(2025, 12, 4)
        )
        
        # SQL 쿼리와 파라미터 검증
        call_args = mock_cursor.execute.call_args
        self.assertIsNotNone(call_args)
        
        sql_query = call_args[0][0]
        params = call_args[0][1]
        
        # SQL에 IN 절이 포함되어 있는지 확인
        self.assertIn('IN (', sql_query)
        
        # 파라미터 개수 확인 (날짜 2개 + 경로 7개 + 제외 경로 5개 = 14개)
        self.assertGreaterEqual(len(params), 14)
    
    @patch('services.access_log_service.db_manager')
    def test_get_daily_visitor_stats_by_path_error_handling(self, mock_db_manager):
        """화면별 일 방문자 수 조회 - 에러 처리"""
        # Mock 설정 - DB 에러 발생
        mock_cursor = MagicMock()
        mock_db_manager.get_cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception("DB 연결 오류")
        
        # 테스트 실행
        result = get_daily_visitor_stats_by_path()
        
        # 검증 - 에러 발생 시 빈 리스트 반환
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)
    
    @patch('services.access_log_service.db_manager')
    def test_get_cumulative_visitor_stats(self, mock_db_manager):
        """누적 방문자 수 조회"""
        # Mock 설정
        mock_cursor = MagicMock()
        mock_db_manager.get_cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (
            date(2025, 12, 1),
            date(2025, 12, 4),
            50,
            200
        )
        
        # 테스트 실행
        result = get_cumulative_visitor_stats(
            start_date=datetime(2025, 12, 1),
            end_date=datetime(2025, 12, 4)
        )
        
        # 검증
        self.assertIsInstance(result, dict)
        self.assertIn('total_unique_visitors', result)
        self.assertIn('total_visits', result)


if __name__ == '__main__':
    unittest.main()


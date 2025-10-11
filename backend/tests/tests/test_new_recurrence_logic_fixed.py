import unittest
import sqlite3
import os
import sys
import json
from unittest.mock import patch, MagicMock

# 상위 디렉토리의 모듈 import
sys.path.append('..')
from main import get_recurring_stocks, _db_path

class TestNewRecurrenceLogic(unittest.TestCase):
    """새로운 재등장 로직 테스트 (수정된 버전)"""
    
    def setUp(self):
        """테스트 설정"""
        self.test_db_path = "test_snapshots.db"
        self.test_data = [
            ("2025-10-10", "042700", "한미반도체", 12.0, "강한 매수", 100600.0),
            ("2025-10-08", "042700", "한미반도체", 12.0, "강한 매수", 100600.0),
            ("2025-10-10", "379810", "KODEX 미국나스닥100", 12.0, "강한 매수", 23215.0),
            ("2025-10-08", "379810", "KODEX 미국나스닥100", 12.0, "강한 매수", 23215.0),
            ("2025-10-10", "007660", "이수페타시스", 11.0, "강한 매수", 76800.0),
            ("2025-10-02", "035420", "네이버", 6.0, "매수 후보", 253000.0),
            ("2025-10-01", "035420", "네이버", 8.0, "강한 매수", 253000.0),
        ]
        
        # 테스트 DB 생성
        self.create_test_db()
    
    def create_test_db(self):
        """테스트 DB 생성"""
        conn = sqlite3.connect(self.test_db_path)
        cur = conn.cursor()
        
        # 테스트 테이블 생성
        cur.execute("""
            CREATE TABLE IF NOT EXISTS scan_rank(
                date TEXT, code TEXT, name TEXT, score REAL, 
                score_label TEXT, close_price REAL,
                PRIMARY KEY(date, code)
            )
        """)
        
        # 기존 데이터 삭제
        cur.execute("DELETE FROM scan_rank")
        
        # 테스트 데이터 삽입
        cur.executemany("""
            INSERT INTO scan_rank(date, code, name, score, score_label, close_price)
            VALUES (?, ?, ?, ?, ?, ?)
        """, self.test_data)
        
        conn.commit()
        conn.close()
    
    def tearDown(self):
        """테스트 정리"""
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
    
    @patch('main._db_path')
    def test_get_recurring_stocks_basic(self, mock_db_path):
        """기본 재등장 종목 조회 테스트"""
        mock_db_path.return_value = self.test_db_path
        
        # 테스트 실행
        result = get_recurring_stocks(days=30, min_appearances=2)
        
        # 검증
        self.assertIsInstance(result, dict)
        self.assertGreater(len(result), 0, "재등장 종목이 있어야 함")
        
        # 한미반도체가 2회 등장했는지 확인
        self.assertIn("042700", result, "한미반도체가 재등장 종목에 있어야 함")
        self.assertEqual(result["042700"]["appear_count"], 2, "한미반도체는 2회 등장해야 함")
        self.assertEqual(result["042700"]["name"], "한미반도체", "종목명이 일치해야 함")
    
    @patch('main._db_path')
    def test_get_recurring_stocks_min_appearances(self, mock_db_path):
        """최소 등장 횟수 테스트"""
        mock_db_path.return_value = self.test_db_path
        
        # min_appearances=3으로 설정 (아무것도 반환되지 않아야 함)
        result = get_recurring_stocks(days=30, min_appearances=3)
        
        # 검증
        self.assertEqual(len(result), 0, "3회 이상 등장한 종목은 없어야 함")
    
    @patch('main._db_path')
    def test_get_recurring_stocks_days_filter(self, mock_db_path):
        """날짜 필터 테스트"""
        mock_db_path.return_value = self.test_db_path
        
        # days=1로 설정 (최근 1일만)
        result = get_recurring_stocks(days=1, min_appearances=1)
        
        # 검증 (최근 1일에는 2025-10-10 데이터만 있음)
        self.assertGreater(len(result), 0, "최근 1일 데이터가 있어야 함")
        for code, data in result.items():
            for appearance in data["appearances"]:
                self.assertEqual(appearance["date"], "2025-10-10", f"날짜가 2025-10-10이어야 함: {appearance}")
    
    @patch('main._db_path')
    def test_get_recurring_stocks_data_structure(self, mock_db_path):
        """데이터 구조 테스트"""
        mock_db_path.return_value = self.test_db_path
        
        result = get_recurring_stocks(days=30, min_appearances=2)
        
        # 데이터 구조 검증
        for code, data in result.items():
            self.assertIn("name", data, f"name 필드가 있어야 함: {code}")
            self.assertIn("appear_count", data, f"appear_count 필드가 있어야 함: {code}")
            self.assertIn("appearances", data, f"appearances 필드가 있어야 함: {code}")
            self.assertIn("latest_score", data, f"latest_score 필드가 있어야 함: {code}")
            self.assertIn("latest_date", data, f"latest_date 필드가 있어야 함: {code}")
            
            # appear_count가 실제 appearances 길이와 일치하는지 확인
            self.assertEqual(data["appear_count"], len(data["appearances"]), 
                           f"appear_count와 appearances 길이가 일치해야 함: {code}")
            
            # appearances가 날짜순으로 정렬되어 있는지 확인
            dates = [app["date"] for app in data["appearances"]]
            self.assertEqual(dates, sorted(dates, reverse=True), 
                           f"appearances가 날짜 내림차순으로 정렬되어야 함: {code}")

if __name__ == '__main__':
    unittest.main()

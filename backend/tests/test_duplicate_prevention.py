"""
중복 데이터 방지 테스트
"""
import unittest
from unittest.mock import Mock, patch
import sqlite3
import tempfile
import os

# main.py에서 함수들 import
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import create_scan_rank_table, _save_snapshot_db
from models import ScanItem, IndicatorPayload, TrendPayload, ScoreFlags


class TestDuplicatePrevention(unittest.TestCase):
    """중복 데이터 방지 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        # 임시 데이터베이스 생성
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.temp_db.close()
        
        # Mock ScanItem 생성
        self.mock_item = Mock()
        self.mock_item.ticker = "005930"
        self.mock_item.name = "삼성전자"
        self.mock_item.score = 8.5
        self.mock_item.score_label = "매우 좋음"
        self.mock_item.strategy = "momentum"
        self.mock_item.market = "KOSPI"
        
        # Mock indicators
        self.mock_indicators = Mock()
        self.mock_indicators.close = 75000.0
        self.mock_indicators.VOL = 1000000
        self.mock_indicators.change_rate = 2.5
        self.mock_item.indicators = self.mock_indicators
        
        # Mock trend
        self.mock_trend = Mock()
        self.mock_trend.__dict__ = {"trend": "up"}
        self.mock_item.trend = self.mock_trend
        
        # Mock flags
        self.mock_flags = Mock()
        self.mock_flags.__dict__ = {"cross": True}
        self.mock_item.flags = self.mock_flags
    
    def tearDown(self):
        """테스트 정리"""
        os.unlink(self.temp_db.name)
    
    def test_table_creation_with_primary_key(self):
        """테이블 생성 시 PRIMARY KEY 설정 테스트"""
        conn = sqlite3.connect(self.temp_db.name)
        cur = conn.cursor()
        
        create_scan_rank_table(cur)
        
        # 테이블 구조 확인
        cur.execute("PRAGMA table_info(scan_rank)")
        columns = cur.fetchall()
        
        # PRIMARY KEY 컬럼 찾기
        pk_columns = [col[1] for col in columns if col[5]]  # col[5]는 pk 여부
        self.assertIn("date", pk_columns)
        self.assertIn("code", pk_columns)
        self.assertEqual(len(pk_columns), 2)  # date, code만 PK여야 함
        
        conn.close()
    
    def test_insert_or_replace_prevents_duplicates(self):
        """INSERT OR REPLACE로 중복 방지 테스트"""
        conn = sqlite3.connect(self.temp_db.name)
        cur = conn.cursor()
        
        create_scan_rank_table(cur)
        
        # 첫 번째 데이터 삽입
        cur.execute("""
            INSERT OR REPLACE INTO scan_rank(
                date, code, name, score, score_label, current_price, volume, change_rate, 
                market, strategy, indicators, trend, flags, details, returns, recurrence
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            "2025-10-24", "005930", "삼성전자", 8.5, "매우 좋음", 
            75000.0, 1000000, 2.5, "KOSPI", "momentum",
            "{}", "{}", "{}", "{}", "{}", "{}"
        ))
        
        # 같은 날짜, 같은 종목으로 두 번째 데이터 삽입 (다른 점수)
        cur.execute("""
            INSERT OR REPLACE INTO scan_rank(
                date, code, name, score, score_label, current_price, volume, change_rate, 
                market, strategy, indicators, trend, flags, details, returns, recurrence
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            "2025-10-24", "005930", "삼성전자", 9.0, "최고", 
            76000.0, 1100000, 3.0, "KOSPI", "momentum",
            "{}", "{}", "{}", "{}", "{}", "{}"
        ))
        
        # 데이터 개수 확인 (중복이 없어야 함)
        cur.execute("SELECT COUNT(*) FROM scan_rank WHERE date = ? AND code = ?", 
                   ("2025-10-24", "005930"))
        count = cur.fetchone()[0]
        self.assertEqual(count, 1)  # 중복이 없어야 함
        
        # 최신 데이터가 저장되었는지 확인
        cur.execute("SELECT score FROM scan_rank WHERE date = ? AND code = ?", 
                   ("2025-10-24", "005930"))
        score = cur.fetchone()[0]
        self.assertEqual(score, 9.0)  # 두 번째 데이터가 저장되어야 함
        
        conn.close()
    
    def test_multiple_items_same_date(self):
        """같은 날짜에 여러 종목 저장 테스트"""
        conn = sqlite3.connect(self.temp_db.name)
        cur = conn.cursor()
        
        create_scan_rank_table(cur)
        
        # 여러 종목 데이터 삽입
        items_data = [
            ("2025-10-24", "005930", "삼성전자", 8.5),
            ("2025-10-24", "000660", "SK하이닉스", 7.8),
            ("2025-10-24", "035420", "NAVER", 9.2),
        ]
        
        for date, code, name, score in items_data:
            cur.execute("""
                INSERT OR REPLACE INTO scan_rank(
                    date, code, name, score, score_label, current_price, volume, change_rate, 
                    market, strategy, indicators, trend, flags, details, returns, recurrence
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                date, code, name, score, "좋음", 
                50000.0, 500000, 1.0, "KOSPI", "momentum",
                "{}", "{}", "{}", "{}", "{}", "{}"
            ))
        
        # 전체 데이터 개수 확인
        cur.execute("SELECT COUNT(*) FROM scan_rank WHERE date = ?", ("2025-10-24",))
        total_count = cur.fetchone()[0]
        self.assertEqual(total_count, 3)  # 3개 종목이 모두 저장되어야 함
        
        # 각 종목별 개수 확인
        for _, code, _, _ in items_data:
            cur.execute("SELECT COUNT(*) FROM scan_rank WHERE date = ? AND code = ?", 
                       ("2025-10-24", code))
            count = cur.fetchone()[0]
            self.assertEqual(count, 1)  # 각 종목당 1개씩만 있어야 함
        
        conn.close()
    
    def test_primary_key_constraint_violation(self):
        """PRIMARY KEY 제약 조건 위반 테스트"""
        conn = sqlite3.connect(self.temp_db.name)
        cur = conn.cursor()
        
        create_scan_rank_table(cur)
        
        # 첫 번째 데이터 삽입
        cur.execute("""
            INSERT INTO scan_rank(
                date, code, name, score, score_label, current_price, volume, change_rate, 
                market, strategy, indicators, trend, flags, details, returns, recurrence
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            "2025-10-24", "005930", "삼성전자", 8.5, "매우 좋음", 
            75000.0, 1000000, 2.5, "KOSPI", "momentum",
            "{}", "{}", "{}", "{}", "{}", "{}"
        ))
        
        # 같은 PRIMARY KEY로 INSERT 시도 (INSERT OR REPLACE 없이)
        with self.assertRaises(sqlite3.IntegrityError):
            cur.execute("""
                INSERT INTO scan_rank(
                    date, code, name, score, score_label, current_price, volume, change_rate, 
                    market, strategy, indicators, trend, flags, details, returns, recurrence
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                "2025-10-24", "005930", "삼성전자", 9.0, "최고", 
                76000.0, 1100000, 3.0, "KOSPI", "momentum",
                "{}", "{}", "{}", "{}", "{}", "{}"
            ))
        
        conn.close()


if __name__ == '__main__':
    unittest.main()




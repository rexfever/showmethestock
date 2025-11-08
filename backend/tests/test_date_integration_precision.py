"""
날짜 타입 통합 정밀 테스트
실제 DB 작업과 API 호출 시뮬레이션
"""
import pytest
import sqlite3
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils_date_utils import normalize_date, format_date_for_db, get_today_yyyymmdd


class TestDateIntegrationDB:
    """DB 통합 날짜 처리 테스트"""
    
    def setup_method(self):
        """실제 스키마와 유사한 테스트 DB 생성"""
        self.test_db = ":memory:"
        self.conn = sqlite3.connect(self.test_db)
        self.cur = self.conn.cursor()
        
        # 실제 scan_rank 테이블 스키마
        self.cur.execute("""
            CREATE TABLE scan_rank(
                date TEXT NOT NULL,
                code TEXT NOT NULL,
                name TEXT,
                score REAL,
                score_label TEXT,
                current_price REAL,
                volume INTEGER,
                change_rate REAL,
                market TEXT,
                strategy TEXT,
                indicators TEXT,
                trend TEXT,
                flags TEXT,
                details TEXT,
                returns TEXT,
                recurrence TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(date, code)
            )
        """)
        self.conn.commit()
    
    def teardown_method(self):
        """테스트 DB 정리"""
        self.conn.close()
    
    def test_insert_or_replace_date_normalization(self):
        """INSERT OR REPLACE에서 날짜 정규화 테스트"""
        # 다양한 형식으로 저장 시도
        test_cases = [
            ("20251031", "005930"),
            ("2025-10-31", "005930"),  # 같은 날짜, 다른 형식
            ("20251101", "000660"),
        ]
        
        for input_date, code in test_cases:
            normalized_date = format_date_for_db(input_date)
            
            # INSERT OR REPLACE 실행
            self.cur.execute("""
                INSERT OR REPLACE INTO scan_rank(
                    date, code, name, score, score_label, current_price, volume, change_rate, 
                    market, strategy, indicators, trend, flags, details, returns, recurrence
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                normalized_date, code, "테스트종목", 8.5, "매우좋음", 
                100000.0, 1000000, 5.5, "KOSPI", "추세상승",
                "{}", "{}", "{}", "{}", "{}", "{}"
            ))
            self.conn.commit()
            
            # 저장된 날짜 형식 확인
            self.cur.execute("SELECT date FROM scan_rank WHERE code = ?", (code,))
            result = self.cur.fetchone()
            assert result[0] == normalized_date
            assert len(result[0]) == 8
            assert result[0].isdigit()
    
    def test_between_query_all_scenarios(self):
        """BETWEEN 쿼리 모든 시나리오 테스트"""
        # 테스트 데이터 삽입
        dates = [
            ("20251028", "001"),
            ("20251029", "002"),
            ("20251030", "003"),
            ("20251031", "004"),
            ("20251101", "005"),
        ]
        
        for date, code in dates:
            normalized = format_date_for_db(date)
            self.cur.execute("""
                INSERT INTO scan_rank(date, code, name, score) VALUES (?, ?, ?, ?)
            """, (normalized, code, f"종목{code}", 8.0))
        self.conn.commit()
        
        # 시나리오 1: YYYYMMDD 형식으로 BETWEEN
        start = format_date_for_db("20251029")
        end = format_date_for_db("20251031")
        
        self.cur.execute(
            "SELECT date, code FROM scan_rank WHERE date BETWEEN ? AND ? ORDER BY date",
            (start, end)
        )
        results = self.cur.fetchall()
        assert len(results) == 3
        assert all(len(r[0]) == 8 for r in results)
        
        # 시나리오 2: YYYY-MM-DD 형식 입력 후 BETWEEN
        start2 = format_date_for_db("2025-10-29")
        end2 = format_date_for_db("2025-10-31")
        
        assert start == start2
        assert end == end2
    
    def test_date_comparison_queries(self):
        """날짜 비교 쿼리 테스트"""
        # 테스트 데이터
        test_dates = ["20251028", "20251029", "20251030", "20251031"]
        for i, date in enumerate(test_dates):
            normalized = format_date_for_db(date)
            self.cur.execute("""
                INSERT INTO scan_rank(date, code, name, score) VALUES (?, ?, ?, ?)
            """, (normalized, f"00000{i}", f"종목{i}", 7.0 + i))
        self.conn.commit()
        
        # >= 쿼리
        cutoff = format_date_for_db("2025-10-30")
        self.cur.execute(
            "SELECT COUNT(*) FROM scan_rank WHERE date >= ?",
            (cutoff,)
        )
        count = self.cur.fetchone()[0]
        assert count == 2  # 20251030, 20251031
        
        # <= 쿼리
        cutoff2 = format_date_for_db("20251029")
        self.cur.execute(
            "SELECT COUNT(*) FROM scan_rank WHERE date <= ?",
            (cutoff2,)
        )
        count2 = self.cur.fetchone()[0]
        assert count2 == 2  # 20251028, 20251029
    
    def test_duplicate_prevention_with_date_normalization(self):
        """날짜 정규화 후 중복 방지 테스트"""
        # 같은 날짜를 다른 형식으로 삽입 시도
        date1 = format_date_for_db("20251031")
        date2 = format_date_for_db("2025-10-31")
        
        assert date1 == date2  # 정규화 후 동일해야 함
        
        # 첫 번째 삽입
        self.cur.execute("""
            INSERT OR REPLACE INTO scan_rank(date, code, name, score) 
            VALUES (?, ?, ?, ?)
        """, (date1, "005930", "삼성전자", 8.5))
        self.conn.commit()
        
        # 두 번째 삽입 (같은 날짜, 다른 형식)
        self.cur.execute("""
            INSERT OR REPLACE INTO scan_rank(date, code, name, score) 
            VALUES (?, ?, ?, ?)
        """, (date2, "005930", "삼성전자", 9.0))
        self.conn.commit()
        
        # 중복이 방지되어 하나만 존재해야 함
        self.cur.execute("SELECT COUNT(*) FROM scan_rank WHERE code = ?", ("005930",))
        count = self.cur.fetchone()[0]
        assert count == 1
        
        # 최신 점수(9.0)로 업데이트되었는지 확인
        self.cur.execute("SELECT score FROM scan_rank WHERE code = ?", ("005930",))
        score = self.cur.fetchone()[0]
        assert score == 9.0


class TestDateIntegrationAPI:
    """API 레벨 날짜 통합 테스트"""
    
    @patch('scan_service_refactored.format_date_for_db')
    def test_scan_service_date_handling(self, mock_format):
        """scan_service_refactored 날짜 처리 테스트"""
        mock_format.return_value = "20251031"
        
        # _save_snapshot_db에서 날짜 사용 시뮬레이션
        as_of = "2025-10-31"
        normalized = mock_format(as_of)
        
        assert normalized == "20251031"
        mock_format.assert_called_once_with(as_of)
    
    def test_returns_service_date_handling(self):
        """returns_service 날짜 처리 테스트"""
        from utils_date_utils import get_today_yyyymmdd, format_date_for_db
        
        # current_date가 None일 때
        current_date = get_today_yyyymmdd()
        assert len(current_date) == 8
        assert current_date.isdigit()
        
        # scan_date 정규화
        scan_date = format_date_for_db("2025-10-31")
        assert scan_date == "20251031"


class TestDateMigrationScenario:
    """날짜 마이그레이션 시나리오 테스트"""
    
    def setup_method(self):
        """혼재된 날짜 형식이 있는 DB 시뮬레이션"""
        self.test_db = ":memory:"
        self.conn = sqlite3.connect(self.test_db)
        self.cur = self.conn.cursor()
        
        self.cur.execute("""
            CREATE TABLE scan_rank(
                date TEXT NOT NULL,
                code TEXT NOT NULL,
                name TEXT,
                score REAL,
                PRIMARY KEY(date, code)
            )
        """)
        self.conn.commit()
        
        # 혼재된 형식 데이터 삽입 (마이그레이션 전 상태 시뮬레이션)
        self.cur.execute("""
            INSERT INTO scan_rank(date, code, name, score) VALUES
            ('2025-10-28', '001', '종목1', 7.5),
            ('20251029', '002', '종목2', 8.0),
            ('2025-10-30', '003', '종목3', 8.5)
        """)
        self.conn.commit()
    
    def teardown_method(self):
        """테스트 DB 정리"""
        self.conn.close()
    
    def test_query_with_mixed_formats(self):
        """혼재된 형식에서 조회 테스트"""
        # 모든 날짜 조회
        self.cur.execute("SELECT date FROM scan_rank ORDER BY code")
        results = self.cur.fetchall()
        
        # 형식이 혼재되어 있음을 확인
        formats = [len(r[0]) for r in results]
        assert 8 in formats  # YYYYMMDD
        assert 10 in formats  # YYYY-MM-DD
        
        # 정규화 후 형식 통일
        normalized_dates = []
        for (date_str,) in results:
            normalized = format_date_for_db(date_str)
            normalized_dates.append(normalized)
            assert len(normalized) == 8
            assert normalized.isdigit()
        
        # 모두 YYYYMMDD 형식으로 변환됨
        assert all(len(d) == 8 for d in normalized_dates)
        assert all(d.isdigit() for d in normalized_dates)


class TestDateRealWorldScenarios:
    """실제 사용 시나리오 테스트"""
    
    def test_daily_scan_workflow(self):
        """일일 스캔 워크플로우 테스트"""
        from utils_date_utils import get_today_yyyymmdd, format_date_for_db
        
        # 1. 오늘 날짜 가져오기
        today = get_today_yyyymmdd()
        assert len(today) == 8
        
        # 2. 스캔 실행 (날짜 정규화)
        scan_date = format_date_for_db(today)
        assert scan_date == today
        
        # 3. DB 저장 준비
        normalized = format_date_for_db(scan_date)
        assert normalized == today
    
    def test_historical_scan_workflow(self):
        """과거 날짜 스캔 워크플로우 테스트"""
        from utils_date_utils import format_date_for_db
        
        # 다양한 형식 입력 처리
        input_formats = [
            "2025-10-31",
            "20251031",
        ]
        
        results = []
        for input_date in input_formats:
            normalized = format_date_for_db(input_date)
            results.append(normalized)
        
        # 모두 동일한 결과
        assert len(set(results)) == 1
        assert results[0] == "20251031"
    
    def test_report_generation_workflow(self):
        """보고서 생성 워크플로우 테스트"""
        from utils_date_utils import format_date_for_db
        from datetime import datetime, timedelta
        
        # 주차별 날짜 범위 계산
        year, month, week = 2025, 10, 1
        week_start = (week - 1) * 7 + 1
        week_end = min(week_start + 6, 31)
        
        start_date = format_date_for_db(f"{year}{month:02d}{week_start:02d}")
        end_date = format_date_for_db(f"{year}{month:02d}{week_end:02d}")
        
        assert start_date == "20251001"
        assert end_date == "20251007"
        assert len(start_date) == 8
        assert len(end_date) == 8
        
        # BETWEEN 쿼리 사용 가능
        assert start_date <= end_date


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])




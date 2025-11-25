"""
customer-scanner 페이지 통합 테스트
- SSR 데이터가 없을 때 클라이언트 API 자동 호출 기능 테스트
- 다른 페이지에서 돌아왔을 때 동작 테스트
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


@pytest.fixture
def client():
    """TestClient 인스턴스 생성"""
    from main import app
    return TestClient(app)


class TestCustomerScannerIntegration:
    """customer-scanner 통합 테스트"""

    def test_latest_scan_api_returns_data(self, client):
        """최신 스캔 API가 데이터를 반환하는지 테스트"""
        with patch('main.sqlite3') as mock_sqlite:
            # Mock DB 연결
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_sqlite.connect.return_value.__enter__.return_value = mock_conn

            # Mock scan_rank 테이블 데이터
            mock_cursor.execute.return_value = None
            mock_cursor.fetchone.return_value = ('2025-10-24',)
            mock_cursor.fetchall.return_value = [
                ('2025-10-24', '005930', '삼성전자', 8.5, '매우 좋음', 75000, 1000000, 2.5, 'KOSPI', 'momentum', '{}', '{}', '{}', '{}', '{}', '{}'),
            ]
            mock_cursor.description = [
                ('date',), ('code',), ('name',), ('score',), ('score_label',), 
                ('current_price',), ('volume',), ('change_rate',), ('market',), 
                ('strategy',), ('indicators',), ('trend',), ('flags',), 
                ('details',), ('returns',), ('recurrence',)
            ]

            response = client.get('/latest-scan')

            assert response.status_code == 200
            data = response.json()
            assert data['ok'] is True
            assert 'data' in data
            assert 'items' in data['data'] or 'rank' in data['data']

    def test_latest_scan_api_with_no_data(self, client):
        """최신 스캔 API가 데이터가 없을 때 빈 배열을 반환하는지 테스트"""
        with patch('main.sqlite3') as mock_sqlite:
            # Mock DB 연결
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_sqlite.connect.return_value.__enter__.return_value = mock_conn

            # Mock scan_rank 테이블 데이터 (빈 결과)
            mock_cursor.execute.return_value = None
            mock_cursor.fetchone.return_value = None  # 날짜가 없음
            mock_cursor.fetchall.return_value = []

            response = client.get('/latest-scan')

            assert response.status_code == 200
            data = response.json()
            assert data['ok'] is True
            assert 'data' in data
            items = data['data'].get('items', data['data'].get('rank', []))
            assert len(items) == 0

    def test_recurring_stocks_api_returns_data(self, client):
        """재등장 종목 API가 데이터를 반환하는지 테스트"""
        with patch('main.sqlite3') as mock_sqlite:
            # Mock DB 연결
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_sqlite.connect.return_value.__enter__.return_value = mock_conn

            # Mock recurring_stocks 데이터
            mock_cursor.fetchall.return_value = [
                ('005930', '삼성전자', 3, '2025-10-20,2025-10-21,2025-10-22'),
            ]
            mock_cursor.description = [('code',), ('name',), ('count',), ('dates',)]

            response = client.get('/recurring-stocks?days=14&min_appearances=2')

            assert response.status_code == 200
            data = response.json()
            assert data['ok'] is True
            assert 'data' in data
            assert 'recurring_stocks' in data['data']

    def test_maintenance_status_api(self, client):
        """메인트넌스 상태 API 테스트"""
        with patch('main.sqlite3') as mock_sqlite:
            # Mock DB 연결
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_sqlite.connect.return_value.__enter__.return_value = mock_conn

            # Mock maintenance_settings 테이블 데이터
            mock_cursor.fetchone.return_value = (False, None, '서비스 점검 중입니다.')
            mock_cursor.description = [('is_enabled',), ('end_date',), ('message',)]

            response = client.get('/maintenance/status')

            assert response.status_code == 200
            data = response.json()
            assert 'is_enabled' in data
            assert data['is_enabled'] is False

    def test_maintenance_status_api_when_enabled(self, client):
        """메인트넌스가 활성화되었을 때 API 테스트"""
        with patch('main.sqlite3') as mock_sqlite:
            # Mock DB 연결
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_sqlite.connect.return_value.__enter__.return_value = mock_conn

            # Mock maintenance_settings 테이블 데이터 (활성화됨)
            mock_cursor.fetchone.return_value = (True, '2025-12-31', '시스템 점검 중입니다.')
            mock_cursor.description = [('is_enabled',), ('end_date',), ('message',)]

            response = client.get('/maintenance/status')

            assert response.status_code == 200
            data = response.json()
            assert 'is_enabled' in data
            assert data['is_enabled'] is True
            assert data['end_date'] == '2025-12-31'
            assert data['message'] == '시스템 점검 중입니다.'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])





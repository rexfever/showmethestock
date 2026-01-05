"""
v3 홈 화면 상태 불변성 테스트

목적: 동일한 추천 인스턴스에 대해 홈 API를 연속 호출했을 때
      status가 변하지 않음을 확인
"""

import unittest
import time
import requests
import os
from typing import Dict, List, Optional

class TestV3StatusImmutability(unittest.TestCase):
    """v3 홈 화면 상태 불변성 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.base_url = os.getenv('BACKEND_URL', 'http://localhost:8010')
        self.scanner_version = 'v3'
        
    def get_latest_scan(self, token: Optional[str] = None) -> Dict:
        """최신 스캔 결과 조회"""
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        if token:
            headers['Authorization'] = f'Bearer {token}'
        
        response = requests.get(
            f'{self.base_url}/latest-scan?scanner_version={self.scanner_version}',
            headers=headers,
            timeout=10
        )
        self.assertEqual(response.status_code, 200)
        return response.json()
    
    def extract_item_by_ticker(self, data: Dict, ticker: str) -> Optional[Dict]:
        """특정 ticker의 아이템 추출"""
        if not data.get('ok') or not data.get('data'):
            return None
        
        items = data.get('data', {}).get('items', [])
        for item in items:
            if item.get('ticker') == ticker:
                return item
        return None
    
    def test_status_immutability_same_request(self):
        """동일 요청에서 상태가 동일한지 확인"""
        # 첫 번째 호출
        data1 = self.get_latest_scan()
        self.assertTrue(data1.get('ok'), '첫 번째 호출 실패')
        
        # 두 번째 호출 (즉시)
        data2 = self.get_latest_scan()
        self.assertTrue(data2.get('ok'), '두 번째 호출 실패')
        
        items1 = data1.get('data', {}).get('items', [])
        items2 = data2.get('data', {}).get('items', [])
        
        # 아이템 개수 비교
        self.assertEqual(len(items1), len(items2), '아이템 개수가 다름')
        
        # 각 아이템의 status 비교
        for item1, item2 in zip(items1, items2):
            ticker = item1.get('ticker')
            if ticker == 'NORESULT':
                continue
            
            status1 = item1.get('status')
            status2 = item2.get('status')
            
            self.assertEqual(
                status1, status2,
                f'ticker={ticker}의 status가 다름: {status1} vs {status2}'
            )
            
            # current_return도 비교 (v3 홈에서는 재계산 금지)
            return1 = item1.get('current_return')
            return2 = item2.get('current_return')
            
            if return1 is not None and return2 is not None:
                self.assertEqual(
                    return1, return2,
                    f'ticker={ticker}의 current_return이 다름: {return1} vs {return2}'
                )
    
    def test_status_immutability_time_interval(self):
        """시간 간격을 두고 호출해도 상태가 동일한지 확인"""
        # 첫 번째 호출
        data1 = self.get_latest_scan()
        self.assertTrue(data1.get('ok'), '첫 번째 호출 실패')
        
        # 5초 대기
        time.sleep(5)
        
        # 두 번째 호출
        data2 = self.get_latest_scan()
        self.assertTrue(data2.get('ok'), '두 번째 호출 실패')
        
        items1 = data1.get('data', {}).get('items', [])
        items2 = data2.get('data', {}).get('items', [])
        
        # 각 아이템의 status 비교
        ticker_to_status1 = {
            item.get('ticker'): item.get('status')
            for item in items1
            if item.get('ticker') != 'NORESULT'
        }
        
        ticker_to_status2 = {
            item.get('ticker'): item.get('status')
            for item in items2
            if item.get('ticker') != 'NORESULT'
        }
        
        # 공통 ticker에 대해 status 비교
        common_tickers = set(ticker_to_status1.keys()) & set(ticker_to_status2.keys())
        
        for ticker in common_tickers:
            status1 = ticker_to_status1[ticker]
            status2 = ticker_to_status2[ticker]
            
            self.assertEqual(
                status1, status2,
                f'ticker={ticker}의 status가 시간 경과 후 변경됨: {status1} → {status2}'
            )
    
    def test_status_field_required(self):
        """status 필드가 모든 아이템에 있는지 확인"""
        data = self.get_latest_scan()
        self.assertTrue(data.get('ok'), 'API 호출 실패')
        
        items = data.get('data', {}).get('items', [])
        
        missing_status_items = []
        for item in items:
            if item.get('ticker') == 'NORESULT':
                continue
            
            if not item.get('status'):
                missing_status_items.append(item.get('ticker'))
        
        self.assertEqual(
            len(missing_status_items), 0,
            f'status 필드가 없는 아이템: {missing_status_items}'
        )
    
    def test_no_calculate_returns_in_v3_home(self):
        """v3 홈에서 calculate_returns가 호출되지 않았는지 확인"""
        # 이 테스트는 로그 파일을 확인하거나 메트릭을 확인해야 함
        # 실제 구현은 로깅/메트릭 시스템에 따라 다름
        
        # 최소한 API 호출이 성공하는지 확인
        data = self.get_latest_scan()
        self.assertTrue(data.get('ok'), 'API 호출 실패')
        
        # TODO: 백엔드 로그에서 [V3_HOME_GUARD] 경고 확인
        # TODO: 메트릭에서 v3_home_recalc_attempt 증가 확인


if __name__ == '__main__':
    unittest.main()



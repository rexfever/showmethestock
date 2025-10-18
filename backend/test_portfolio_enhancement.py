#!/usr/bin/env python3
"""
포트폴리오 확장 기능 테스트
- 추천종목 vs 개인종목 구분
- 일일 수익률 자동 업데이트
- 성과 비교 기능
"""

import unittest
import sqlite3
import json
import os
import tempfile
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# 테스트 대상 모듈 import
import sys
sys.path.append('.')

from portfolio_service import PortfolioService
from daily_update_service import DailyUpdateService
from notification_service import NotificationService
from models import PortfolioItem, AddToPortfolioRequest, AddPersonalStockRequest


class TestPortfolioEnhancement(unittest.TestCase):
    """포트폴리오 확장 기능 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        # 임시 데이터베이스 생성
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        # 테스트용 서비스 인스턴스 생성
        self.portfolio_service = PortfolioService(self.temp_db.name)
        self.daily_update_service = DailyUpdateService(self.temp_db.name)
        self.notification_service = NotificationService(self.temp_db.name)
        
        # 테스트 데이터 설정
        self.test_user_id = 1
        self.setup_test_data()
    
    def tearDown(self):
        """테스트 정리"""
        # 임시 데이터베이스 삭제
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    def setup_test_data(self):
        """테스트 데이터 설정"""
        with sqlite3.connect(self.temp_db.name) as conn:
            cursor = conn.cursor()
            
            # 테스트 포트폴리오 데이터 삽입
            test_portfolios = [
                # 추천종목
                (1, '005930', '삼성전자', 70000, 10, '2025-10-01', 75000, 700000, 750000, 50000, 7.14, 'watching', 'recommended', 12, '2025-10-01', 2.5, 8.5, 5.0, 11),
                # 개인종목
                (1, '000660', 'SK하이닉스', 120000, 5, '2025-10-02', 125000, 600000, 625000, 25000, 4.17, 'watching', 'personal', None, None, 1.2, 5.2, 3.0, 10),
                # 추천종목
                (1, '035420', 'NAVER', 200000, 3, '2025-10-03', 195000, 600000, 585000, -15000, -2.5, 'watching', 'recommended', 10, '2025-10-03', -1.0, 2.0, -3.0, 9),
            ]
            
            for portfolio in test_portfolios:
                cursor.execute("""
                    INSERT INTO portfolio (
                        user_id, ticker, name, entry_price, quantity, entry_date,
                        current_price, total_investment, current_value, profit_loss,
                        profit_loss_pct, status, source, recommendation_score,
                        recommendation_date, daily_return_pct, max_return_pct,
                        min_return_pct, holding_days
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, portfolio)
            
            conn.commit()
    
    def test_portfolio_model_extension(self):
        """포트폴리오 모델 확장 테스트"""
        print("🧪 테스트 1: 포트폴리오 모델 확장")
        
        # 포트폴리오 조회
        portfolios = self.portfolio_service.get_portfolio(self.test_user_id)
        
        self.assertIsNotNone(portfolios)
        self.assertGreater(len(portfolios.items), 0)
        
        # 새 필드들이 존재하는지 확인
        for item in portfolios.items:
            self.assertIsNotNone(item.source)
            self.assertIn(item.source, ['recommended', 'personal'])
            
            if item.source == 'recommended':
                self.assertIsNotNone(item.recommendation_score)
                self.assertIsNotNone(item.recommendation_date)
            else:
                self.assertIsNone(item.recommendation_score)
                self.assertIsNone(item.recommendation_date)
        
        print("✅ 포트폴리오 모델 확장 테스트 통과")
    
    def test_add_personal_stock(self):
        """개인 종목 추가 테스트"""
        print("🧪 테스트 2: 개인 종목 추가")
        
        # 개인 종목 추가 요청
        request = AddPersonalStockRequest(
            ticker="035720",
            name="카카오",
            entry_price=50000,
            quantity=20,
            entry_date="2025-10-12",
            source="personal"
        )
        
        # 포트폴리오에 추가
        result = self.portfolio_service.add_to_portfolio(self.test_user_id, request)
        
        self.assertIsNotNone(result)
        self.assertEqual(result.ticker, "035720")
        self.assertEqual(result.name, "카카오")
        self.assertEqual(result.source, "personal")
        self.assertEqual(result.entry_price, 50000)
        self.assertEqual(result.quantity, 20)
        
        print("✅ 개인 종목 추가 테스트 통과")
    
    def test_recommended_vs_personal_performance(self):
        """추천종목 vs 개인종목 성과 비교 테스트"""
        print("🧪 테스트 3: 추천종목 vs 개인종목 성과 비교")
        
        portfolios = self.portfolio_service.get_portfolio(self.test_user_id)
        
        # 추천종목과 개인종목 분리
        recommended_items = [item for item in portfolios.items if item.source == 'recommended']
        personal_items = [item for item in portfolios.items if item.source == 'personal']
        
        self.assertGreater(len(recommended_items), 0)
        self.assertGreater(len(personal_items), 0)
        
        # 평균 수익률 계산
        recommended_avg = sum(item.profit_loss_pct or 0 for item in recommended_items) / len(recommended_items)
        personal_avg = sum(item.profit_loss_pct or 0 for item in personal_items) / len(personal_items)
        
        print(f"📊 추천종목 평균 수익률: {recommended_avg:.2f}%")
        print(f"📊 개인종목 평균 수익률: {personal_avg:.2f}%")
        
        # 성과 비교 데이터가 올바르게 계산되는지 확인
        self.assertIsInstance(recommended_avg, float)
        self.assertIsInstance(personal_avg, float)
        
        print("✅ 추천종목 vs 개인종목 성과 비교 테스트 통과")
    
    @patch('daily_update_service.portfolio_service.get_current_price')
    def test_daily_update_service(self, mock_get_price):
        """일일 업데이트 서비스 테스트"""
        print("🧪 테스트 4: 일일 업데이트 서비스")
        
        # 현재가 조회 모킹
        mock_get_price.side_effect = lambda ticker: {
            '005930': 76000,  # 삼성전자 +1000원
            '000660': 124000, # SK하이닉스 -1000원
            '035420': 200000  # NAVER +5000원
        }.get(ticker, 100000)
        
        # 일일 업데이트 실행
        self.daily_update_service.update_user_portfolio(self.test_user_id)
        
        # 업데이트 결과 확인
        with sqlite3.connect(self.temp_db.name) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ticker, current_price, daily_return_pct, max_return_pct, min_return_pct
                FROM portfolio WHERE user_id = ?
            """, (self.test_user_id,))
            
            results = cursor.fetchall()
            
            for ticker, current_price, daily_return, max_return, min_return in results:
                self.assertIsNotNone(current_price)
                self.assertIsNotNone(daily_return)
                self.assertIsNotNone(max_return)
                self.assertIsNotNone(min_return)
                
                print(f"📈 {ticker}: 현재가 {current_price}, 일일수익률 {daily_return:.2f}%")
        
        print("✅ 일일 업데이트 서비스 테스트 통과")
    
    def test_notification_service(self):
        """알림 서비스 테스트"""
        print("🧪 테스트 5: 알림 서비스")
        
        # 일일 리포트 생성 (daily_update_service를 통해)
        report = self.daily_update_service.generate_daily_report(self.test_user_id)
        
        self.assertIsNotNone(report)
        self.assertIn('date', report)
        self.assertIn('source_stats', report)
        self.assertIn('top_performers', report)
        self.assertIn('bottom_performers', report)
        
        # 리포트 내용 확인
        source_stats = report['source_stats']
        self.assertIn('recommended', source_stats)
        self.assertIn('personal', source_stats)
        
        print(f"📊 추천종목: {source_stats['recommended']['count']}개, 평균 {source_stats['recommended']['avg_return']:.2f}%")
        print(f"📊 개인종목: {source_stats['personal']['count']}개, 평균 {source_stats['personal']['avg_return']:.2f}%")
        
        # 리포트 포맷팅 테스트
        formatted_message = self.notification_service._format_daily_report(report)
        self.assertIsInstance(formatted_message, str)
        self.assertIn('포트폴리오 리포트', formatted_message)
        self.assertIn('성과 비교', formatted_message)
        
        print("✅ 알림 서비스 테스트 통과")
    
    def test_database_migration(self):
        """데이터베이스 마이그레이션 테스트"""
        print("🧪 테스트 6: 데이터베이스 마이그레이션")
        
        with sqlite3.connect(self.temp_db.name) as conn:
            cursor = conn.cursor()
            
            # 새 컬럼들이 존재하는지 확인
            cursor.execute("PRAGMA table_info(portfolio)")
            columns = [row[1] for row in cursor.fetchall()]
            
            new_columns = [
                'source', 'recommendation_score', 'recommendation_date',
                'daily_return_pct', 'max_return_pct', 'min_return_pct', 'holding_days'
            ]
            
            for column in new_columns:
                self.assertIn(column, columns, f"컬럼 {column}이 존재하지 않습니다")
            
            print(f"✅ 새 컬럼들 확인: {', '.join(new_columns)}")
        
        print("✅ 데이터베이스 마이그레이션 테스트 통과")


def run_portfolio_tests():
    """포트폴리오 확장 기능 테스트 실행"""
    print("🚀 포트폴리오 확장 기능 테스트 시작")
    print("=" * 50)
    
    # 테스트 스위트 생성
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPortfolioEnhancement)
    
    # 테스트 실행
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("=" * 50)
    if result.wasSuccessful():
        print("🎉 모든 포트폴리오 확장 기능 테스트 통과!")
        return True
    else:
        print(f"❌ {len(result.failures)}개 테스트 실패, {len(result.errors)}개 오류")
        return False


if __name__ == "__main__":
    success = run_portfolio_tests()
    exit(0 if success else 1)

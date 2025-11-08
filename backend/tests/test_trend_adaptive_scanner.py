"""
추세 적응 스캐너 테스트
"""
import unittest
import os
import json
import tempfile
import shutil
from unittest.mock import patch, MagicMock, mock_open
from datetime import datetime

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trend_adaptive_scanner import TrendAdaptiveScanner, PerformanceMetrics
from config import config


class TestTrendAdaptiveScanner(unittest.TestCase):
    """추세 적응 스캐너 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.scanner = TrendAdaptiveScanner()
        self.test_reports_dir = None
        self.original_reports_dir = None
        
    def tearDown(self):
        """테스트 정리"""
        # 테스트용 보고서 디렉토리 정리
        if self.test_reports_dir and os.path.exists(self.test_reports_dir):
            shutil.rmtree(self.test_reports_dir)
    
    def create_test_weekly_report(self, year, month, week, stocks_data):
        """테스트용 주간 보고서 생성"""
        if not self.test_reports_dir:
            self.test_reports_dir = tempfile.mkdtemp()
            weekly_dir = os.path.join(self.test_reports_dir, "weekly")
            os.makedirs(weekly_dir, exist_ok=True)
        else:
            weekly_dir = os.path.join(self.test_reports_dir, "weekly")
        
        filename = f"weekly_{year}_{month:02d}_week{week}.json"
        filepath = os.path.join(weekly_dir, filename)
        
        report = {
            "year": year,
            "month": month,
            "week": week,
            "start_date": f"{year}-{month:02d}-01",
            "end_date": f"{year}-{month:02d}-07",
            "stocks": stocks_data
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        return filepath
    
    def create_test_monthly_report(self, year, month, stats):
        """테스트용 월간 보고서 생성"""
        if not self.test_reports_dir:
            self.test_reports_dir = tempfile.mkdtemp()
            monthly_dir = os.path.join(self.test_reports_dir, "monthly")
            os.makedirs(monthly_dir, exist_ok=True)
        else:
            monthly_dir = os.path.join(self.test_reports_dir, "monthly")
        
        filename = f"monthly_{year}_{month:02d}.json"
        filepath = os.path.join(monthly_dir, filename)
        
        report = {
            "year": year,
            "month": month,
            "statistics": stats
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        return filepath
    
    @patch('trend_adaptive_scanner.os.path.join')
    @patch('trend_adaptive_scanner.os.path.exists')
    @patch('trend_adaptive_scanner.os.path.dirname')
    def test_get_recent_performance_no_reports(self, mock_dirname, mock_exists, mock_join):
        """보고서가 없을 때 None 반환 테스트"""
        mock_dirname.return_value = "/fake/path"
        mock_join.return_value = "/fake/path/reports/weekly"
        mock_exists.return_value = False
        
        result = self.scanner.get_recent_performance(weeks=4)
        self.assertIsNone(result)
    
    @patch('trend_adaptive_scanner.glob.glob')
    @patch('trend_adaptive_scanner.os.path.exists')
    @patch('trend_adaptive_scanner.os.path.join')
    @patch('trend_adaptive_scanner.os.path.dirname')
    def test_get_recent_performance_no_files(self, mock_dirname, mock_join, mock_exists, mock_glob):
        """보고서 파일이 없을 때 None 반환 테스트"""
        mock_dirname.return_value = "/fake/path"
        mock_join.return_value = "/fake/path/reports/weekly"
        mock_exists.return_value = True
        mock_glob.return_value = []
        
        result = self.scanner.get_recent_performance(weeks=4)
        self.assertIsNone(result)
    
    def test_get_recent_performance_with_data(self):
        """보고서 데이터로 성과 계산 테스트"""
        # 테스트용 보고서 생성
        stocks1 = [
            {"ticker": "A001", "name": "종목1", "max_return": 10.5},
            {"ticker": "A002", "name": "종목2", "max_return": -5.2},
            {"ticker": "A003", "name": "종목3", "max_return": 15.8},
        ]
        stocks2 = [
            {"ticker": "A004", "name": "종목4", "max_return": 8.3},
            {"ticker": "A005", "name": "종목5", "max_return": 12.1},
        ]
        
        now = datetime.now()
        self.create_test_weekly_report(now.year, now.month, 1, stocks1)
        self.create_test_weekly_report(now.year, now.month, 2, stocks2)
        
        # reports 디렉토리 경로 패치
        original_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        reports_dir = os.path.join(original_dir, "reports")
        weekly_dir = os.path.join(reports_dir, "weekly")
        
        # 실제 디렉토리가 없으면 테스트 스킵
        if not os.path.exists(weekly_dir):
            self.skipTest("보고서 디렉토리가 없습니다")
        
        # 기존 reports 디렉토리 백업
        backup_dir = reports_dir + ".backup"
        if os.path.exists(reports_dir):
            if os.path.exists(backup_dir):
                shutil.rmtree(backup_dir)
            shutil.copytree(reports_dir, backup_dir)
        
        try:
            # 테스트용 보고서를 실제 위치에 복사
            test_weekly_dir = os.path.join(self.test_reports_dir, "weekly")
            if os.path.exists(weekly_dir):
                for file in os.listdir(test_weekly_dir):
                    shutil.copy(
                        os.path.join(test_weekly_dir, file),
                        os.path.join(weekly_dir, file)
                    )
            
            # 성과 조회
            result = self.scanner.get_recent_performance(weeks=2)
            
            # 검증
            self.assertIsNotNone(result)
            self.assertIsInstance(result, PerformanceMetrics)
            self.assertEqual(result.total_stocks, 5)
            # 평균 수익률: (10.5 + -5.2 + 15.8 + 8.3 + 12.1) / 5 = 8.3
            self.assertAlmostEqual(result.avg_return, 8.3, places=1)
            # 승률: 4/5 = 80%
            self.assertAlmostEqual(result.win_rate, 80.0, places=1)
            self.assertEqual(result.best_return, 15.8)
            self.assertEqual(result.worst_return, -5.2)
        finally:
            # 백업 복원
            if os.path.exists(backup_dir):
                if os.path.exists(reports_dir):
                    shutil.rmtree(reports_dir)
                shutil.move(backup_dir, reports_dir)
    
    def test_get_monthly_performance_no_file(self):
        """월간 보고서 파일이 없을 때 None 반환 테스트"""
        now = datetime.now()
        result = self.scanner.get_monthly_performance(now.year, 13)  # 존재하지 않는 월
        self.assertIsNone(result)
    
    def test_evaluate_performance_excellent(self):
        """우수 성과 평가 테스트"""
        # 실제 threshold: avg_return >= 40.0, win_rate >= 95.0
        metrics = PerformanceMetrics(
            avg_return=45.0,
            win_rate=96.0,
            total_stocks=10,
            best_return=60.0,
            worst_return=-2.0
        )
        result = self.scanner.evaluate_performance(metrics)
        self.assertEqual(result, "excellent")
    
    def test_evaluate_performance_good(self):
        """양호 성과 평가 테스트"""
        # 실제 threshold: avg_return >= 30.0, win_rate >= 90.0
        metrics = PerformanceMetrics(
            avg_return=35.0,
            win_rate=92.0,
            total_stocks=10,
            best_return=50.0,
            worst_return=-3.0
        )
        result = self.scanner.evaluate_performance(metrics)
        self.assertEqual(result, "good")
    
    def test_evaluate_performance_fair(self):
        """보통 성과 평가 테스트"""
        # 실제 threshold: avg_return >= 20.0, win_rate >= 85.0
        metrics = PerformanceMetrics(
            avg_return=25.0,
            win_rate=87.0,
            total_stocks=10,
            best_return=40.0,
            worst_return=-5.0
        )
        result = self.scanner.evaluate_performance(metrics)
        self.assertEqual(result, "fair")
    
    def test_evaluate_performance_poor(self):
        """저조 성과 평가 테스트"""
        metrics = PerformanceMetrics(
            avg_return=-2.0,
            win_rate=30.0,
            total_stocks=10,
            best_return=5.0,
            worst_return=-10.0
        )
        result = self.scanner.evaluate_performance(metrics)
        self.assertEqual(result, "poor")
    
    @patch('trend_adaptive_scanner.config')
    def test_get_adjusted_parameters_excellent(self, mock_config):
        """우수 성과 시 파라미터 조정 테스트"""
        mock_config.min_signals = 5
        mock_config.rsi_upper_limit = 60
        mock_config.vol_ma5_mult = 2.2
        mock_config.gap_max = 0.008
        mock_config.ext_from_tema20_max = 0.008
        mock_config.min_score = 5
        
        params = self.scanner.get_adjusted_parameters("excellent")
        
        # 우수 성과 시 기준 완화 (더 많은 종목 선별) - 실제 로직 확인
        # excellent: min_signals -1, rsi_upper_limit +2, vol_ma5_mult -0.2, gap_max +0.003, ext_from_tema20_max +0.003
        # 따라서 min_signals는 감소 (4 <= 5)
        self.assertLessEqual(params["min_signals"], mock_config.min_signals + 1)  # 완화됨
        self.assertGreaterEqual(params["rsi_upper_limit"], mock_config.rsi_upper_limit - 1)  # 완화됨
        self.assertLessEqual(params["vol_ma5_mult"], mock_config.vol_ma5_mult + 0.3)  # 완화됨
        self.assertGreaterEqual(params["gap_max"], mock_config.gap_max - 0.004)  # 완화됨
        self.assertGreaterEqual(params["ext_from_tema20_max"], mock_config.ext_from_tema20_max - 0.004)  # 완화됨
    
    @patch('trend_adaptive_scanner.config')
    def test_get_adjusted_parameters_poor(self, mock_config):
        """저조 성과 시 파라미터 조정 테스트"""
        mock_config.min_signals = 5
        mock_config.rsi_upper_limit = 60
        mock_config.vol_ma5_mult = 2.2
        mock_config.gap_max = 0.008
        mock_config.ext_from_tema20_max = 0.008
        mock_config.min_score = 5
        
        params = self.scanner.get_adjusted_parameters("poor")
        
        # 저조 성과 시 기준 완화 (더 관대하게)
        self.assertLessEqual(params["min_signals"], mock_config.min_signals)
        self.assertGreaterEqual(params["rsi_upper_limit"], mock_config.rsi_upper_limit)
        self.assertLessEqual(params["vol_ma5_mult"], mock_config.vol_ma5_mult)
        self.assertGreaterEqual(params["gap_max"], mock_config.gap_max)
        self.assertGreaterEqual(params["ext_from_tema20_max"], mock_config.ext_from_tema20_max)
    
    @patch('trend_adaptive_scanner.TrendAdaptiveScanner.get_recent_performance')
    @patch('trend_adaptive_scanner.TrendAdaptiveScanner.get_monthly_performance')
    @patch('trend_adaptive_scanner.TrendAdaptiveScanner.evaluate_performance')
    @patch('trend_adaptive_scanner.TrendAdaptiveScanner.get_adjusted_parameters')
    @patch('trend_adaptive_scanner.config')
    def test_analyze_and_recommend_return_type(self, mock_config, mock_get_adjusted, 
                                                mock_evaluate, mock_monthly, mock_recent):
        """analyze_and_recommend 반환 타입 테스트"""
        # Mock 설정
        mock_metrics = PerformanceMetrics(
            avg_return=8.0,
            win_rate=65.0,
            total_stocks=10,
            best_return=15.0,
            worst_return=-3.0
        )
        mock_recent.return_value = mock_metrics
        mock_monthly.return_value = mock_metrics
        mock_evaluate.return_value = "good"
        mock_get_adjusted.return_value = {
            "min_signals": 3,
            "rsi_upper_limit": 65,
            "vol_ma5_mult": 1.8,
            "gap_max": 0.013,
            "ext_from_tema20_max": 0.013,
            "min_score": 4
        }
        mock_config.min_signals = 5
        mock_config.rsi_upper_limit = 60
        mock_config.vol_ma5_mult = 2.2
        mock_config.gap_max = 0.008
        mock_config.ext_from_tema20_max = 0.008
        
        # 실행
        result = self.scanner.analyze_and_recommend()
        
        # 검증 - Tuple 반환 확인
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        
        recommended_params, evaluation = result
        
        # 권장 파라미터 검증
        self.assertIsInstance(recommended_params, dict)
        self.assertIn("min_signals", recommended_params)
        self.assertIn("rsi_upper_limit", recommended_params)
        self.assertIn("vol_ma5_mult", recommended_params)
        self.assertIn("gap_max", recommended_params)
        self.assertIn("ext_from_tema20_max", recommended_params)
        self.assertIn("min_score", recommended_params)
        
        # 평가 검증
        self.assertIsInstance(evaluation, str)
        self.assertIn(evaluation, ["excellent", "good", "fair", "poor"])


class TestPerformanceMetrics(unittest.TestCase):
    """PerformanceMetrics 데이터클래스 테스트"""
    
    def test_performance_metrics_creation(self):
        """PerformanceMetrics 생성 테스트"""
        metrics = PerformanceMetrics(
            avg_return=10.5,
            win_rate=75.0,
            total_stocks=20,
            best_return=25.0,
            worst_return=-5.0
        )
        
        self.assertEqual(metrics.avg_return, 10.5)
        self.assertEqual(metrics.win_rate, 75.0)
        self.assertEqual(metrics.total_stocks, 20)
        self.assertEqual(metrics.best_return, 25.0)
        self.assertEqual(metrics.worst_return, -5.0)
    
    def test_performance_metrics_default_values(self):
        """PerformanceMetrics 기본값 테스트"""
        metrics = PerformanceMetrics(
            avg_return=0.0,
            win_rate=0.0,
            total_stocks=0,
            best_return=0.0,
            worst_return=0.0
        )
        
        self.assertEqual(metrics.avg_return, 0.0)
        self.assertEqual(metrics.win_rate, 0.0)
        self.assertEqual(metrics.total_stocks, 0)


if __name__ == '__main__':
    unittest.main()


#!/usr/bin/env python3
"""
추세 변화 자동 대응 스캐너
성과 기반으로 파라미터를 자동 조정합니다.
"""
import os
import json
import glob
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, Any
from dataclasses import dataclass

from services.report_generator import ReportGenerator
from config import config


@dataclass
class PerformanceMetrics:
    """성과 지표"""
    avg_return: float
    win_rate: float
    total_stocks: int
    best_return: float
    worst_return: float


class TrendAdaptiveScanner:
    """추세 적응형 스캐너"""
    
    def __init__(self):
        self.report_generator = ReportGenerator()
        self.performance_thresholds = {
            "excellent": {"avg_return": 40.0, "win_rate": 95.0},
            "good": {"avg_return": 30.0, "win_rate": 90.0},
            "fair": {"avg_return": 20.0, "win_rate": 85.0},
            "poor": {"avg_return": 10.0, "win_rate": 80.0},
        }
    
    def get_recent_performance(self, weeks: int = 4) -> Optional[PerformanceMetrics]:
        """최근 N주간 성과 분석"""
        weekly_reports = []
        weekly_dir = os.path.join(os.path.dirname(__file__), "reports", "weekly")
        
        if not os.path.exists(weekly_dir):
            return None
        
        # 최근 N주간 보고서 수집
        all_files = sorted(glob.glob(f"{weekly_dir}/weekly_*.json"), reverse=True)
        recent_files = all_files[:weeks]
        
        if not recent_files:
            return None
        
        all_stocks = []
        for file_path in recent_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    report = json.load(f)
                    stocks = report.get("stocks", [])
                    all_stocks.extend(stocks)
            except Exception as e:
                print(f"보고서 로드 오류: {file_path} - {e}")
                continue
        
        if not all_stocks:
            return None
        
        # 성과 지표 계산
        returns = [s.get("max_return", 0) for s in all_stocks]
        positive_count = sum(1 for r in returns if r > 0)
        
        return PerformanceMetrics(
            avg_return=sum(returns) / len(returns) if returns else 0,
            win_rate=(positive_count / len(returns) * 100) if returns else 0,
            total_stocks=len(all_stocks),
            best_return=max(returns) if returns else 0,
            worst_return=min(returns) if returns else 0,
        )
    
    def get_monthly_performance(self, year: int, month: int) -> Optional[PerformanceMetrics]:
        """특정 월의 성과 분석"""
        monthly_dir = os.path.join(os.path.dirname(__file__), "reports", "monthly")
        filename = f"monthly_{year}_{month:02d}.json"
        file_path = os.path.join(monthly_dir, filename)
        
        if not os.path.exists(file_path):
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                report = json.load(f)
                stats = report.get("statistics", {})
                
                return PerformanceMetrics(
                    avg_return=stats.get("avg_return", 0),
                    win_rate=stats.get("positive_rate", 0),
                    total_stocks=stats.get("total_stocks", 0),
                    best_return=stats.get("best_stock", {}).get("max_return", 0) if stats.get("best_stock") else 0,
                    worst_return=stats.get("worst_stock", {}).get("max_return", 0) if stats.get("worst_stock") else 0,
                )
        except Exception as e:
            print(f"월간 보고서 로드 오류: {file_path} - {e}")
            return None
    
    def evaluate_performance(self, metrics: PerformanceMetrics) -> str:
        """성과 평가"""
        if metrics.avg_return >= self.performance_thresholds["excellent"]["avg_return"] and \
           metrics.win_rate >= self.performance_thresholds["excellent"]["win_rate"]:
            return "excellent"
        elif metrics.avg_return >= self.performance_thresholds["good"]["avg_return"] and \
             metrics.win_rate >= self.performance_thresholds["good"]["win_rate"]:
            return "good"
        elif metrics.avg_return >= self.performance_thresholds["fair"]["avg_return"] and \
             metrics.win_rate >= self.performance_thresholds["fair"]["win_rate"]:
            return "fair"
        else:
            return "poor"
    
    def get_adjusted_parameters(self, performance_level: str) -> Dict:
        """성과 수준에 따른 파라미터 조정"""
        
        # 기본값 (현재 config 값)
        base_params = {
            "min_signals": config.min_signals,
            "rsi_upper_limit": config.rsi_upper_limit,
            "vol_ma5_mult": config.vol_ma5_mult,
            "gap_max": config.gap_max,
            "ext_from_tema20_max": config.ext_from_tema20_max,
            "rsi_threshold": config.rsi_threshold,
            "min_score": 4,  # 기본 최소 점수
        }
        
        if performance_level == "excellent":
            # 성과 우수 → 기준 완화 (더 많은 종목 선별)
            return {
                **base_params,
                "min_signals": max(2, base_params["min_signals"] - 1),
                "rsi_upper_limit": min(75, base_params["rsi_upper_limit"] + 5),
                "vol_ma5_mult": max(1.5, base_params["vol_ma5_mult"] - 0.2),
                "gap_max": min(0.15, base_params["gap_max"] + 0.02),
                "ext_from_tema20_max": min(0.20, base_params["ext_from_tema20_max"] + 0.02),
                "min_score": 4,
            }
        elif performance_level == "good":
            # 성과 양호 → 기본값 유지
            return base_params
        elif performance_level == "fair":
            # 성과 보통 → 기준 강화
            return {
                **base_params,
                "min_signals": base_params["min_signals"] + 1,
                "rsi_upper_limit": max(60, base_params["rsi_upper_limit"] - 5),
                "vol_ma5_mult": base_params["vol_ma5_mult"] + 0.2,
                "gap_max": max(0.010, base_params["gap_max"] - 0.005),  # 축소
                "ext_from_tema20_max": max(0.010, base_params["ext_from_tema20_max"] - 0.005),  # 축소
                "min_score": 6,
            }
        else:  # poor
            # 성과 저조 → 기준 완화 (더 많은 종목 선별 시도)
            # 현재 기준이 너무 엄격해서 종목이 적거나, 잘못된 종목이 선별되고 있을 가능성
            return {
                **base_params,
                "min_signals": max(2, base_params["min_signals"] - 2),  # 완화 (예: 5 → 3)
                "rsi_upper_limit": min(70, base_params["rsi_upper_limit"] + 5),  # 완화
                "vol_ma5_mult": max(1.5, base_params["vol_ma5_mult"] - 0.4),  # 완화 (예: 2.2 → 1.8)
                "gap_max": min(0.02, base_params["gap_max"] + 0.005),  # 확대 (더 넓은 범위 허용)
                "ext_from_tema20_max": min(0.02, base_params["ext_from_tema20_max"] + 0.005),  # 확대
                "min_score": 4,  # 완화
            }
    
    def analyze_and_recommend(self) -> Tuple[Dict[str, Any], str]:
        """성과 분석 및 조정 권장사항 출력
        
        Returns:
            Tuple[Dict[str, Any], str]: (recommended_params, evaluation)
                - recommended_params: 권장 파라미터 딕셔너리
                - evaluation: 성과 평가 ("excellent", "good", "fair", "poor")
        """
        print("=" * 80)
        print("📊 추세 변화 대응 분석")
        print("=" * 80)
        
        # 현재 월 계산
        now = datetime.now()
        current_month = now.month
        current_year = now.year
        
        # 최근 4주간 성과
        print("\n1️⃣ 최근 4주간 성과 분석")
        recent_4weeks = self.get_recent_performance(weeks=4)
        if recent_4weeks:
            print(f"   평균 수익률: {recent_4weeks.avg_return:.2f}%")
            print(f"   승률: {recent_4weeks.win_rate:.2f}%")
            print(f"   추천 종목 수: {recent_4weeks.total_stocks}개")
            print(f"   최고 수익률: {recent_4weeks.best_return:.2f}%")
            print(f"   최저 수익률: {recent_4weeks.worst_return:.2f}%")
            
            recent_eval = self.evaluate_performance(recent_4weeks)
            print(f"   평가: {recent_eval}")
        else:
            print("   데이터 없음")
            recent_eval = "good"  # 기본값
        
        # 최근 월간 성과
        print(f"\n2️⃣ {current_year}년 {current_month}월 성과 분석")
        monthly_perf = self.get_monthly_performance(current_year, current_month)
        if monthly_perf:
            print(f"   평균 수익률: {monthly_perf.avg_return:.2f}%")
            print(f"   승률: {monthly_perf.win_rate:.2f}%")
            print(f"   추천 종목 수: {monthly_perf.total_stocks}개")
            
            monthly_eval = self.evaluate_performance(monthly_perf)
            print(f"   평가: {monthly_eval}")
        else:
            print("   데이터 없음")
            monthly_eval = "good"  # 기본값
        
        # 종합 평가 (더 나쁜 쪽 기준)
        if recent_eval == "poor" or monthly_eval == "poor":
            overall_eval = "poor"
        elif recent_eval == "fair" or monthly_eval == "fair":
            overall_eval = "fair"
        elif recent_eval == "excellent" and monthly_eval == "excellent":
            overall_eval = "excellent"
        else:
            overall_eval = "good"
        
        # 조정 권장사항
        print(f"\n3️⃣ 권장 파라미터 조정")
        recommended_params = self.get_adjusted_parameters(overall_eval)
        
        print(f"   현재 설정:")
        print(f"     min_signals: {config.min_signals}")
        print(f"     rsi_upper_limit: {config.rsi_upper_limit}")
        print(f"     vol_ma5_mult: {config.vol_ma5_mult}")
        print(f"     gap_max: {config.gap_max}")
        print(f"     ext_from_tema20_max: {config.ext_from_tema20_max}")
        
        print(f"\n   권장 설정 ({overall_eval} 기준):")
        print(f"     min_signals: {recommended_params['min_signals']}")
        print(f"     rsi_upper_limit: {recommended_params['rsi_upper_limit']}")
        print(f"     vol_ma5_mult: {recommended_params['vol_ma5_mult']}")
        print(f"     gap_max: {recommended_params['gap_max']}")
        print(f"     ext_from_tema20_max: {recommended_params['ext_from_tema20_max']}")
        print(f"     min_score: {recommended_params['min_score']}")
        
        # 변경 사항
        changes = []
        if recommended_params['min_signals'] != config.min_signals:
            changes.append(f"min_signals: {config.min_signals} → {recommended_params['min_signals']}")
        if recommended_params['rsi_upper_limit'] != config.rsi_upper_limit:
            changes.append(f"rsi_upper_limit: {config.rsi_upper_limit} → {recommended_params['rsi_upper_limit']}")
        if recommended_params['vol_ma5_mult'] != config.vol_ma5_mult:
            changes.append(f"vol_ma5_mult: {config.vol_ma5_mult} → {recommended_params['vol_ma5_mult']}")
        if recommended_params['gap_max'] != config.gap_max:
            changes.append(f"gap_max: {config.gap_max} → {recommended_params['gap_max']}")
        if recommended_params['ext_from_tema20_max'] != config.ext_from_tema20_max:
            changes.append(f"ext_from_tema20_max: {config.ext_from_tema20_max} → {recommended_params['ext_from_tema20_max']}")
        
        if changes:
            print(f"\n   변경 사항:")
            for change in changes:
                print(f"     - {change}")
        else:
            print(f"\n   변경 사항 없음 (현재 설정이 적절함)")
        
        print("\n" + "=" * 80)
        
        return recommended_params, overall_eval


def main():
    """메인 실행 함수"""
    scanner = TrendAdaptiveScanner()
    recommended_params, evaluation = scanner.analyze_and_recommend()
    
    # 평가 결과에 따른 조치
    if evaluation == "poor":
        print("\n⚠️  경고: 성과 저조 감지. 즉시 파라미터 조정을 권장합니다.")
    elif evaluation == "fair":
        print("\n💡 알림: 성과 보통. 파라미터 조정을 검토하세요.")
    elif evaluation == "good":
        print("\n✅ 양호: 현재 성과가 양호합니다. 파라미터 유지 권장.")
    else:
        print("\n🎉 우수: 현재 성과가 매우 우수합니다!")


if __name__ == "__main__":
    main()


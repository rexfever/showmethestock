"""
향상된 성과 보고서 생성 서비스
"""
import numpy as np
from typing import Dict, List
from datetime import datetime, timedelta
import sqlite3
import logging

logger = logging.getLogger(__name__)

class EnhancedReportGenerator:
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def calculate_enhanced_metrics(self, stocks: List[Dict]) -> Dict:
        """향상된 성과 지표 계산"""
        if not stocks:
            return {}
        
        returns = [stock['current_return'] for stock in stocks]
        max_returns = [stock['max_return'] for stock in stocks]
        
        # 기본 통계
        avg_return = np.mean(returns)
        median_return = np.median(returns)
        std_return = np.std(returns)
        
        # 샤프 비율 (무위험 수익률 3% 가정)
        risk_free_rate = 3.0
        sharpe_ratio = (avg_return - risk_free_rate) / std_return if std_return > 0 else 0
        
        # 최대 낙폭 (Maximum Drawdown)
        max_drawdown = min([stock['min_return'] for stock in stocks])
        
        # 승률 및 손익비
        winners = [r for r in returns if r > 0]
        losers = [r for r in returns if r < 0]
        
        win_rate = len(winners) / len(returns) * 100 if returns else 0
        avg_win = np.mean(winners) if winners else 0
        avg_loss = abs(np.mean(losers)) if losers else 0
        profit_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0
        
        # 변동성 조정 수익률
        volatility_adjusted_return = avg_return / std_return if std_return > 0 else 0
        
        return {
            'basic_stats': {
                'avg_return': round(avg_return, 2),
                'median_return': round(median_return, 2),
                'std_return': round(std_return, 2),
                'total_stocks': len(stocks)
            },
            'risk_metrics': {
                'sharpe_ratio': round(sharpe_ratio, 3),
                'max_drawdown': round(max_drawdown, 2),
                'volatility_adjusted_return': round(volatility_adjusted_return, 3)
            },
            'performance_metrics': {
                'win_rate': round(win_rate, 2),
                'avg_win': round(avg_win, 2),
                'avg_loss': round(avg_loss, 2),
                'profit_loss_ratio': round(profit_loss_ratio, 2)
            }
        }
    
    def analyze_sector_performance(self, stocks: List[Dict]) -> Dict:
        """섹터별 성과 분석"""
        sector_data = {}
        
        for stock in stocks:
            market = stock.get('market', '기타')
            if market not in sector_data:
                sector_data[market] = []
            sector_data[market].append(stock['current_return'])
        
        sector_analysis = {}
        for sector, returns in sector_data.items():
            sector_analysis[sector] = {
                'count': len(returns),
                'avg_return': round(np.mean(returns), 2),
                'win_rate': round(len([r for r in returns if r > 0]) / len(returns) * 100, 2)
            }
        
        return sector_analysis
    
    def generate_insights(self, metrics: Dict, sector_analysis: Dict) -> List[str]:
        """AI 기반 인사이트 생성"""
        insights = []
        
        # 수익률 평가
        avg_return = metrics['basic_stats']['avg_return']
        if avg_return > 10:
            insights.append("🎯 평균 수익률이 10%를 초과하여 우수한 성과를 보이고 있습니다.")
        elif avg_return > 5:
            insights.append("📈 평균 수익률이 양호한 수준입니다.")
        else:
            insights.append("⚠️ 평균 수익률이 기대치를 하회하고 있어 전략 점검이 필요합니다.")
        
        # 승률 평가
        win_rate = metrics['performance_metrics']['win_rate']
        if win_rate > 70:
            insights.append("✅ 높은 승률로 안정적인 수익 창출이 가능합니다.")
        elif win_rate < 50:
            insights.append("🔍 승률이 50% 미만으로 종목 선별 기준 강화가 필요합니다.")
        
        # 리스크 평가
        sharpe_ratio = metrics['risk_metrics']['sharpe_ratio']
        if sharpe_ratio > 1.0:
            insights.append("💎 샤프 비율이 1.0을 초과하여 위험 대비 수익이 우수합니다.")
        elif sharpe_ratio < 0.5:
            insights.append("⚡ 변동성 대비 수익률이 낮아 리스크 관리가 필요합니다.")
        
        return insights
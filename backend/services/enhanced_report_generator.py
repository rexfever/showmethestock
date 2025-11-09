"""
향상된 성과 보고서 생성 서비스
"""
import os
import json
import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import calendar
from collections import Counter, defaultdict
from services.returns_service import calculate_returns
import concurrent.futures

logger = logging.getLogger(__name__)

class EnhancedReportGenerator:
    def __init__(self):
        # 절대 경로 사용 - 프로젝트 루트 찾기
        current_file = os.path.abspath(__file__)
        current = current_file
        while current != os.path.dirname(current):
            if os.path.basename(current) == "backend":
                project_root = os.path.dirname(current)
                break
            current = os.path.dirname(current)
        else:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
        
        self.reports_dir = os.path.join(project_root, "backend", "reports")
    
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
            # 종목명에서 섹터 추정 또는 기본 분류 사용
            sector = self._get_sector_from_stock(stock)
            
            if sector not in sector_data:
                sector_data[sector] = []
            sector_data[sector].append(stock['current_return'])
        
        sector_analysis = {}
        for sector, returns in sector_data.items():
            sector_analysis[sector] = {
                'count': len(returns),
                'avg_return': round(np.mean(returns), 2),
                'win_rate': round(len([r for r in returns if r > 0]) / len(returns) * 100, 2)
            }
        
        return sector_analysis
    
    def _get_sector_from_stock(self, stock: Dict) -> str:
        """종목에서 섹터 정보 추출"""
        name = stock.get('name', '')
        ticker = stock.get('ticker', '')
        
        # 종목명 기반 섹터 분류
        if any(keyword in name for keyword in ['바이오', '제약', '의료', '헬스']):
            return '바이오/제약'
        elif any(keyword in name for keyword in ['반도체', '전자', '디스플레이', 'IT']):
            return 'IT/전자'
        elif any(keyword in name for keyword in ['화학', '케미칼', '소재']):
            return '화학/소재'
        elif any(keyword in name for keyword in ['자동차', '모터', '부품']):
            return '자동차'
        elif any(keyword in name for keyword in ['건설', '건축', '토목']):
            return '건설'
        elif any(keyword in name for keyword in ['금융', '은행', '증권', '보험']):
            return '금융'
        elif any(keyword in name for keyword in ['통신', '네트워크', '인터넷']):
            return '통신/인터넷'
        elif any(keyword in name for keyword in ['에너지', '전력', '가스']):
            return '에너지'
        elif any(keyword in name for keyword in ['식품', '음료', '농업']):
            return '식품/농업'
        elif any(keyword in name for keyword in ['유통', '백화점', '마트']):
            return '유통/소비재'
        else:
            return '기타'
    
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
    
    def _load_report(self, report_type: str, filename: str) -> Optional[Dict]:
        """보고서 파일 로드"""
        try:
            filepath = os.path.join(self.reports_dir, report_type, filename)
            if not os.path.exists(filepath):
                return None
            
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"보고서 로드 오류 ({filename}): {e}")
            return None
    
    def generate_enhanced_report(self, report_type: str, year: int, month: int = None, week: int = None, quarter: int = None) -> Dict:
        """향상된 보고서 생성"""
        try:
            # 기존 보고서 데이터 로드
            if report_type == "weekly" and month and week:
                filename = f"weekly_{year}_{month:02d}_week{week}.json"
            elif report_type == "monthly" and month:
                filename = f"monthly_{year}_{month:02d}.json"
            elif report_type == "quarterly" and quarter:
                filename = f"quarterly_{year}_Q{quarter}.json"
            elif report_type == "yearly":
                filename = f"yearly_{year}.json"
            else:
                return {"error": "잘못된 보고서 유형입니다"}
            
            base_report = self._load_report(report_type, filename)
            if not base_report:
                return {"error": "보고서를 찾을 수 없습니다"}
            
            stocks = base_report.get('stocks', [])
            if not stocks:
                return base_report
            
            # 향상된 지표 계산
            enhanced_metrics = self.calculate_enhanced_metrics(stocks)
            sector_analysis = self.analyze_sector_performance(stocks)
            insights = self.generate_insights(enhanced_metrics, sector_analysis)
            
            # 기존 보고서에 향상된 데이터 추가
            enhanced_report = base_report.copy()
            enhanced_report['enhanced_metrics'] = enhanced_metrics
            enhanced_report['sector_analysis'] = sector_analysis
            enhanced_report['ai_insights'] = insights
            enhanced_report['report_version'] = '2.0'
            enhanced_report['enhanced_at'] = datetime.now().isoformat()
            
            # 보고서 파일에 저장
            try:
                filepath = os.path.join(self.reports_dir, report_type, filename)
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(enhanced_report, f, ensure_ascii=False, indent=2)
                logger.info(f"향상된 보고서 저장 완료: {filename}")
            except Exception as save_error:
                logger.warning(f"보고서 저장 실패: {save_error}")
            
            return enhanced_report
            
        except Exception as e:
            logger.error(f"향상된 보고서 생성 오류: {e}")
            return {"error": str(e)}
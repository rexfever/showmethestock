"""
향상된 성과 보고서 API 엔드포인트
"""
from flask import Blueprint, jsonify, request
from services.enhanced_report_generator import EnhancedReportGenerator
from services.report_generator import report_generator
import logging

logger = logging.getLogger(__name__)

enhanced_report_bp = Blueprint('enhanced_report', __name__)

@enhanced_report_bp.route('/reports/enhanced/<report_type>/<int:year>/<int:month>', methods=['GET'])
def get_enhanced_monthly_report(report_type, year, month):
    """향상된 월간 보고서 조회"""
    try:
        # 기본 보고서 데이터 조회
        filename = f"monthly_{year}_{month:02d}.json"
        basic_report = report_generator._load_report("monthly", filename)
        
        if not basic_report:
            return jsonify({"ok": False, "error": "보고서를 찾을 수 없습니다."})
        
        # 향상된 분석 추가
        enhanced_generator = EnhancedReportGenerator(report_generator.db_path)
        
        # 향상된 지표 계산
        enhanced_metrics = enhanced_generator.calculate_enhanced_metrics(basic_report['stocks'])
        
        # 섹터별 분석
        sector_analysis = enhanced_generator.analyze_sector_performance(basic_report['stocks'])
        
        # AI 인사이트 생성
        insights = enhanced_generator.generate_insights(enhanced_metrics, sector_analysis)
        
        # 보고서 데이터 확장
        enhanced_report = {
            **basic_report,
            'enhanced_metrics': enhanced_metrics,
            'sector_analysis': sector_analysis,
            'ai_insights': insights,
            'report_version': '2.0'
        }
        
        return jsonify({"ok": True, "data": enhanced_report})
        
    except Exception as e:
        logger.error(f"향상된 보고서 조회 오류: {e}", exc_info=True)
        return jsonify({"ok": False, "error": "서버 오류가 발생했습니다."})

@enhanced_report_bp.route('/reports/summary/<int:year>/<int:month>', methods=['GET'])
def get_report_summary(year, month):
    """보고서 요약 정보 조회"""
    try:
        filename = f"monthly_{year}_{month:02d}.json"
        report_data = report_generator._load_report("monthly", filename)
        
        if not report_data:
            return jsonify({"ok": False, "error": "보고서를 찾을 수 없습니다."})
        
        # 요약 정보 생성
        summary = {
            'period': f"{year}년 {month}월",
            'total_stocks': len(report_data['stocks']),
            'avg_return': report_data['statistics']['avg_return'],
            'win_rate': report_data['statistics']['positive_rate'],
            'best_performer': report_data['statistics']['best_stock']['name'] if report_data['statistics']['best_stock'] else None,
            'best_return': report_data['statistics']['best_stock']['max_return'] if report_data['statistics']['best_stock'] else 0,
            'analysis_days': len(report_data['dates'])
        }
        
        return jsonify({"ok": True, "data": summary})
        
    except Exception as e:
        logger.error(f"보고서 요약 조회 오류: {e}", exc_info=True)
        return jsonify({"ok": False, "error": "서버 오류가 발생했습니다."})
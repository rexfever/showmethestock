#!/usr/bin/env python3
"""
임시 파일 및 스크립트 정리 도구
"""
import os
import shutil
from pathlib import Path

def cleanup_temp_files():
    """임시 파일들을 정리합니다."""
    
    # 루트 디렉토리의 임시 파일들
    root_temp_files = [
        # 테스트 스크립트들
        "test_november_regime_v4.py",
        "test_november_regime_v4_fast.py", 
        "test_real_data_v4.py",
        "test_regime_analysis_nov2024.py",
        "test_regime_simple.py",
        "test_regime_v4.py",
        "test_regime_v4_comparison.py",
        "test_v2_november.py",
        "test_yahoo_direct.py",
        "simple_v2_test.py",
        
        # 분석 스크립트들
        "analyze_november_market.py",
        "analyze_november_regime.py",
        "bulk_regime_2025.py",
        "bulk_regime_2025_real.py",
        "bulk_regime_cached.py",
        "bulk_regime_korea_only.py",
        "bulk_regime_yahoo_csv.py",
        "create_november_regime_direct.py",
        "query_november_regime.py",
        "query_november_regime_fixed.py",
        "update_november_regime.py",
        "update_november_regime_fast.py",
        "update_november_with_api.py",
        "generate_regime_v4_demo.py",
        
        # 임시 결과 파일들
        "november_market_analysis.json",
        "november_regime_analysis.json",
        "bulk_regime_cached_20251101_20251123.json",
        "v1_v2_comparison_nov.json",
        "weekly_report_2025_10_week5.json",
        
        # 팝업 수정 스크립트들
        "popup_fix.py",
        "popup_fix_v2.py", 
        "popup_fix_final.py",
        
        # 기타 임시 파일들
        "filter_engine_v2.py",
        "scanner_v2_server.py",
        "scorer_v2.py",
        "generate_july_reports.py",
        "generate_october_reports.py",
        "generate_weekly_report.py",
        "generate_weekly_report_simple.py",
        "mock_dependencies.py",
        "start_mock_server.py",
        "run_all_tests.py",
        
        # 로그 파일들
        "backend.log",
        "frontend.log",
        "backend.pid",
        
        # 배포 관련 임시 파일들
        "deploy-backend.json",
        "deploy-summary.json",
        "parameter-store-policy.json",
        "trust-policy.json",
        
        # 임시 문서들
        "BACKTEST_ENGINE_WORK_IN_PROGRESS_20251109.md",
        "CODE_REVIEW_2025-11-24.md",
        "CODE_REVIEW_ISSUES.md",
        "DB_MANAGEMENT.md",
        "DEPLOYMENT_SUMMARY.md",
        "PHASE1_COMPLETION_REPORT.md",
        "PHASE1_TEST_ANALYSIS.md",
        "PHASE2_COMPLETION_REPORT.md", 
        "PHASE2_TEST_ANALYSIS.md",
        "PHASE3_COMPLETION_REPORT.md",
        "PHASE3_FINAL_COMPLETION_REPORT.md",
        "TEST_REPORT_CLEANUP_20251109.md",
        "TREND_ADAPTATION_GUIDE.md",
        "WORK_REPORT_20251117.md"
    ]
    
    # 백엔드 임시 파일들
    backend_temp_files = [
        "backend/.env.temp",
        "backend/temp_latest_scan_api.py",
        "backend/test_3line_system.py",
        "backend/test_admin_rescan.py",
        "backend/test_api_endpoints.py",
        "backend/test_date_format.py",
        "backend/test_date_helper.py",
        "backend/test_db_storage_validation.py",
        "backend/test_final_date_format.py",
        "backend/test_final_validation.py",
        "backend/test_integration_admin.py",
        "backend/test_integration_validation.py",
        "backend/test_kakao_comprehensive.py",
        "backend/test_kakao_integration.py",
        "backend/test_kakao_provider_id.py",
        "backend/test_main_functions.py",
        "backend/test_market_guide.py",
        "backend/test_market_guide_mock.py",
        "backend/test_models.py",
        "backend/test_path_traversal_fix.py",
        "backend/test_portfolio_enhancement.py",
        "backend/test_refactored_scan_service.py",
        "backend/test_regime_cache.py",
        "backend/test_security.py",
        "backend/test_simple.py",
        "backend/test_strategy_variations.py",
        "backend/test_trading_day.py"
    ]
    
    # 임시 디렉토리들
    temp_dirs = [
        "backend/test_3line_system_results",
        "backend/test_cache"
    ]
    
    root_path = Path("/Users/rexsmac/workspace/stock-finder")
    moved_count = 0
    
    # archive/temp 디렉토리 생성
    temp_archive = root_path / "archive" / "temp_cleanup_20251123"
    temp_archive.mkdir(parents=True, exist_ok=True)
    
    print(f"임시 파일 정리 시작...")
    print(f"이동 대상: {temp_archive}")
    
    # 루트 파일들 이동
    for file_name in root_temp_files:
        file_path = root_path / file_name
        if file_path.exists():
            dest_path = temp_archive / file_name
            shutil.move(str(file_path), str(dest_path))
            print(f"이동: {file_name}")
            moved_count += 1
    
    # 백엔드 파일들 이동
    for file_path in backend_temp_files:
        full_path = root_path / file_path
        if full_path.exists():
            dest_path = temp_archive / file_path
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(full_path), str(dest_path))
            print(f"이동: {file_path}")
            moved_count += 1
    
    # 임시 디렉토리들 이동
    for dir_path in temp_dirs:
        full_path = root_path / dir_path
        if full_path.exists():
            dest_path = temp_archive / dir_path
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(full_path), str(dest_path))
            print(f"이동: {dir_path}/")
            moved_count += 1
    
    print(f"\n정리 완료: {moved_count}개 파일/디렉토리 이동")
    print(f"이동된 위치: {temp_archive}")
    
    return moved_count

if __name__ == "__main__":
    cleanup_temp_files()
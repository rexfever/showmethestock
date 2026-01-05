#!/usr/bin/env python3
"""
문서 통합 스크립트

흩어져 있는 문서들을 /docs 아래로 통합 관리
"""
import os
import shutil
from pathlib import Path

# 작업 디렉토리
workspace_root = Path(__file__).parent.parent
docs_root = workspace_root / 'docs'

# 디렉토리 생성
directories = [
    docs_root / 'v3' / 'implementation',
    docs_root / 'v3' / 'migration',
    docs_root / 'v3' / 'verification',
    docs_root / 'v3' / 'ux',
    docs_root / 'backend' / 'scanner',
    docs_root / 'backend' / 'backtest',
    docs_root / 'backend' / 'analysis',
    docs_root / 'frontend' / 'v3',
    docs_root / 'migrations',
]

for dir_path in directories:
    dir_path.mkdir(parents=True, exist_ok=True)
    print(f"✅ 디렉토리 생성: {dir_path}")

# 파일 이동 매핑
file_moves = [
    # V3 구현 문서
    (workspace_root / 'docs' / 'V3_ARCHIVED_SNAPSHOT_IMPLEMENTATION_REPORT.md',
     docs_root / 'v3' / 'implementation' / 'V3_ARCHIVED_SNAPSHOT_IMPLEMENTATION_REPORT.md'),
    (workspace_root / 'docs' / 'v3' / 'V3_IMPLEMENTATION_REPORT.md',
     docs_root / 'v3' / 'implementation' / 'V3_IMPLEMENTATION_REPORT.md'),
    (workspace_root / 'backend' / 'docs' / 'V3_RECOMMENDATIONS_REFACTORING_REPORT.md',
     docs_root / 'v3' / 'implementation' / 'V3_RECOMMENDATIONS_REFACTORING_REPORT.md'),
    (workspace_root / 'backend' / 'docs' / 'V3_IMPLEMENTATION_SUMMARY.md',
     docs_root / 'v3' / 'implementation' / 'V3_IMPLEMENTATION_SUMMARY.md'),
    
    # V3 마이그레이션 문서
    (workspace_root / 'backend' / 'docs' / 'V3_MIGRATION_EXECUTION_GUIDE.md',
     docs_root / 'v3' / 'migration' / 'V3_MIGRATION_EXECUTION_GUIDE.md'),
    (workspace_root / 'backend' / 'docs' / 'V3_MIGRATION_EXECUTION_RESULTS.md',
     docs_root / 'v3' / 'migration' / 'V3_MIGRATION_EXECUTION_RESULTS.md'),
    (workspace_root / 'backend' / 'docs' / 'V3_BACKFILL_EXECUTION_RESULTS.md',
     docs_root / 'v3' / 'migration' / 'V3_BACKFILL_EXECUTION_RESULTS.md'),
    
    # V3 검증 문서
    (workspace_root / 'backend' / 'docs' / 'V3_VERIFICATION_REPORT.md',
     docs_root / 'v3' / 'verification' / 'V3_VERIFICATION_REPORT.md'),
    (workspace_root / 'backend' / 'docs' / 'V3_VERIFICATION_FINAL_REPORT.md',
     docs_root / 'v3' / 'verification' / 'V3_VERIFICATION_FINAL_REPORT.md'),
    (workspace_root / 'backend' / 'docs' / 'V3_VERIFICATION_EXECUTION_RESULTS.md',
     docs_root / 'v3' / 'verification' / 'V3_VERIFICATION_EXECUTION_RESULTS.md'),
    (workspace_root / 'backend' / 'docs' / 'V3_VERIFICATION_EXECUTION_GUIDE.md',
     docs_root / 'v3' / 'verification' / 'V3_VERIFICATION_EXECUTION_GUIDE.md'),
    (workspace_root / 'backend' / 'docs' / 'V3_VERIFICATION_COMPLETE.md',
     docs_root / 'v3' / 'verification' / 'V3_VERIFICATION_COMPLETE.md'),
    (workspace_root / 'backend' / 'docs' / 'V3_VERIFICATION_LOCATIONS.md',
     docs_root / 'v3' / 'verification' / 'V3_VERIFICATION_LOCATIONS.md'),
    (workspace_root / 'backend' / 'docs' / 'V3_FINAL_VERIFICATION_SUMMARY.md',
     docs_root / 'v3' / 'verification' / 'V3_FINAL_VERIFICATION_SUMMARY.md'),
    
    # V3 UX 문서
    (workspace_root / 'frontend' / 'docs' / 'V3_UX_IMPLEMENTATION_REPORT.md',
     docs_root / 'v3' / 'ux' / 'V3_UX_IMPLEMENTATION_REPORT.md'),
    (workspace_root / 'frontend' / 'docs' / 'V3_UX_IMPLEMENTATION_SUMMARY.md',
     docs_root / 'v3' / 'ux' / 'V3_UX_IMPLEMENTATION_SUMMARY.md'),
    (workspace_root / 'frontend' / 'docs' / 'V3_UX_IMPLEMENTATION.md',
     docs_root / 'v3' / 'ux' / 'V3_UX_IMPLEMENTATION.md'),
    
    # 프론트엔드 V3 문서
    (workspace_root / 'frontend' / 'pages' / 'v3' / 'ACK_IMPLEMENTATION.md',
     docs_root / 'frontend' / 'v3' / 'ACK_IMPLEMENTATION.md'),
    (workspace_root / 'frontend' / 'pages' / 'v3' / 'COLLAPSE_EXPAND_IMPLEMENTATION.md',
     docs_root / 'frontend' / 'v3' / 'COLLAPSE_EXPAND_IMPLEMENTATION.md'),
    (workspace_root / 'frontend' / 'pages' / 'v3' / 'STATUS_BASED_REFACTOR.md',
     docs_root / 'frontend' / 'v3' / 'STATUS_BASED_REFACTOR.md'),
    (workspace_root / 'frontend' / 'pages' / 'v3' / 'CARD_IMPLEMENTATION.md',
     docs_root / 'frontend' / 'v3' / 'CARD_IMPLEMENTATION.md'),
    (workspace_root / 'frontend' / 'pages' / 'v3' / 'V3_IMPLEMENTATION_SUMMARY.md',
     docs_root / 'frontend' / 'v3' / 'V3_IMPLEMENTATION_SUMMARY.md'),
    (workspace_root / 'frontend' / 'pages' / 'v3' / 'DETAIL_IMPLEMENTATION.md',
     docs_root / 'frontend' / 'v3' / 'DETAIL_IMPLEMENTATION.md'),
    (workspace_root / 'frontend' / 'pages' / 'v3' / 'QA_REGRESSION_TEST.md',
     docs_root / 'frontend' / 'v3' / 'QA_REGRESSION_TEST.md'),
    (workspace_root / 'frontend' / 'pages' / 'v3' / 'REGRESSION_GUARDS.md',
     docs_root / 'frontend' / 'v3' / 'REGRESSION_GUARDS.md'),
    (workspace_root / 'frontend' / 'components' / 'v3' / 'HOLIDAY_UX_FIX.md',
     docs_root / 'frontend' / 'v3' / 'HOLIDAY_UX_FIX.md'),
    (workspace_root / 'frontend' / 'components' / 'v3' / 'STATUS_MIGRATION.md',
     docs_root / 'frontend' / 'v3' / 'STATUS_MIGRATION.md'),
    (workspace_root / 'frontend' / 'components' / 'v3' / 'HOLIDAY_MESSAGE_FIX.md',
     docs_root / 'frontend' / 'v3' / 'HOLIDAY_MESSAGE_FIX.md'),
    
    # 마이그레이션 README
    (workspace_root / 'backend' / 'migrations' / 'README_V2_SCHEMA.md',
     docs_root / 'migrations' / 'README_V2_SCHEMA.md'),
    (workspace_root / 'backend' / 'migrations' / 'README_V2_TRANSACTION_SQL.md',
     docs_root / 'migrations' / 'README_V2_TRANSACTION_SQL.md'),
    (workspace_root / 'backend' / 'migrations' / 'README_ANCHOR_CLOSE.md',
     docs_root / 'migrations' / 'README_ANCHOR_CLOSE.md'),
]

# 파일 이동 실행
moved_count = 0
skipped_count = 0
error_count = 0

for src, dst in file_moves:
    if src.exists():
        try:
            # 대상 디렉토리 생성
            dst.parent.mkdir(parents=True, exist_ok=True)
            
            # 파일 이동 (이미 있으면 건너뛰기)
            if not dst.exists():
                shutil.move(str(src), str(dst))
                print(f"✅ 이동: {src.name} → {dst.relative_to(workspace_root)}")
                moved_count += 1
            else:
                print(f"⚠️  건너뜀 (이미 존재): {dst.relative_to(workspace_root)}")
                skipped_count += 1
        except Exception as e:
            print(f"❌ 오류 ({src.name}): {e}")
            error_count += 1
    else:
        print(f"⚠️  파일 없음: {src}")

print(f"\n{'='*60}")
print(f"✅ 이동 완료: {moved_count}개")
print(f"⚠️  건너뜀: {skipped_count}개")
print(f"❌ 오류: {error_count}개")
print(f"{'='*60}")



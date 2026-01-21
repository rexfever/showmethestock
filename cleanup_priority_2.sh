#!/bin/bash
# Priority 2: Archive or remove one-time analysis scripts
# Moves analysis scripts to archive for historical reference

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

echo "🧹 Starting Priority 2 Cleanup..."
echo "=================================="

echo ""
echo "📦 Creating archive directories..."
mkdir -p backend/archive/analysis_scripts_2025
mkdir -p backend/scripts/one_time_scripts

echo ""
echo "📦 Moving analysis scripts to archive..."
[ -f backend/analyze_v2_winrate.py ] && mv -v backend/analyze_v2_winrate.py backend/archive/analysis_scripts_2025/
[ -f backend/analyze_v2_winrate_by_horizon.py ] && mv -v backend/analyze_v2_winrate_by_horizon.py backend/archive/analysis_scripts_2025/
[ -f backend/analyze_november_regime_cached.py ] && mv -v backend/analyze_november_regime_cached.py backend/archive/analysis_scripts_2025/
[ -f backend/analyze_november_regime_with_csv.py ] && mv -v backend/analyze_november_regime_with_csv.py backend/archive/analysis_scripts_2025/
[ -f backend/analyze_optimal_conditions.py ] && mv -v backend/analyze_optimal_conditions.py backend/archive/analysis_scripts_2025/
[ -f backend/analyze_regime_v4_july_nov.py ] && mv -v backend/analyze_regime_v4_july_nov.py backend/archive/analysis_scripts_2025/

echo ""
echo "📦 Moving one-time utility scripts..."
[ -f backend/check_aws_v2_data.py ] && mv -v backend/check_aws_v2_data.py backend/scripts/one_time_scripts/
[ -f backend/check_v2_scan_data.py ] && mv -v backend/check_v2_scan_data.py backend/scripts/one_time_scripts/
[ -f backend/create_admin_user.py ] && mv -v backend/create_admin_user.py backend/scripts/one_time_scripts/
[ -f backend/create_cache_data.py ] && mv -v backend/create_cache_data.py backend/scripts/one_time_scripts/
[ -f backend/create_regime_table_sqlite.py ] && mv -v backend/create_regime_table_sqlite.py backend/scripts/one_time_scripts/

echo ""
echo "📝 Creating README for archived scripts..."
cat > backend/archive/analysis_scripts_2025/README.md << 'EOF'
# Analysis Scripts Archive (2025)

This directory contains one-time analysis scripts that were used for historical analysis and debugging.

## Scripts
- `analyze_v2_winrate.py` - Scanner V2 win rate analysis
- `analyze_v2_winrate_by_horizon.py` - Win rate by holding horizon
- `analyze_november_regime_cached.py` - November 2024 regime analysis (cached)
- `analyze_november_regime_with_csv.py` - November 2024 regime analysis (CSV)
- `analyze_optimal_conditions.py` - Optimal condition parameter analysis
- `analyze_regime_v4_july_nov.py` - Regime V4 July-November analysis

## Note
These scripts are no longer used in production but are kept for historical reference.
Moved from `backend/` on 2025-01-21.
EOF

cat > backend/scripts/one_time_scripts/README.md << 'EOF'
# One-Time Utility Scripts

This directory contains utility scripts that are meant to be run once or occasionally for setup/debugging.

## Scripts
- `check_aws_v2_data.py` - Check AWS V2 scanner data
- `check_v2_scan_data.py` - Verify V2 scan data integrity
- `create_admin_user.py` - Create admin user (run once during setup)
- `create_cache_data.py` - Initialize cache data (run once during setup)
- `create_regime_table_sqlite.py` - Create regime table in SQLite (deprecated, PostgreSQL used)

## Usage
These scripts should only be run when needed, not as part of regular operations.
Moved from `backend/` on 2025-01-21.
EOF

echo ""
echo "=================================="
echo "✅ Priority 2 cleanup completed!"
echo ""
echo "Next steps:"
echo "1. Run: git status"
echo "2. Verify no imports are broken: cd backend && python -m pytest tests/"
echo "3. Run: bash cleanup_priority_3.sh"

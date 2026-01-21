#!/bin/bash
# Priority 1: Remove backup, security, log files
# Safe to run - removes only temporary/backup/security files

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

echo "🧹 Starting Priority 1 Cleanup..."
echo "=================================="

# Count files before cleanup
FILES_BEFORE=$(find . -type f | wc -l)

echo ""
echo "🗑️  Removing backup files..."
rm -vf backend/.env.backup
rm -vf backend/.env.backup.20251023_004613
rm -vf backend/.env.example.backup

echo ""
echo "🗑️  Removing security risk files..."
rm -vf aws_console_copy_paste.txt
rm -vf notification_recipients.txt

echo ""
echo "🗑️  Removing log files..."
rm -vf update_regime_v4.log
rm -vf backend/backend.log
rm -vf backend/update_regime_v4.log
rm -vf backend/optimal_conditions.log
rm -vf backend/optimal_conditions_full.log
rm -vf backend/optimal_conditions_full_v2.log
rm -vf backend/optimal_conditions_jul_sep.log
rm -vf backend/rescan_november_full.log
rm -vf backend/server_scan_validation.log
rm -vf backend/server_scan_validation_oct27.log
rm -vf frontend/frontend.log

echo ""
echo "🗑️  Removing coverage files..."
rm -vf backend/.coverage

# Count files after cleanup
FILES_AFTER=$(find . -type f | wc -l)
FILES_REMOVED=$((FILES_BEFORE - FILES_AFTER))

echo ""
echo "=================================="
echo "✅ Priority 1 cleanup completed!"
echo "📊 Files removed: $FILES_REMOVED"
echo ""
echo "Next steps:"
echo "1. Run: git status"
echo "2. Update .gitignore (see CLEANUP_PLAN.md)"
echo "3. Run: bash cleanup_priority_2.sh"

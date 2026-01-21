#!/bin/bash
# Complete cleanup execution script
# Runs all three priority cleanups with verification

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║         showmethestock 정리 스크립트 (전체 실행)              ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if git is clean
echo "🔍 Checking git status..."
if [ -n "$(git status --porcelain)" ]; then
    echo -e "${YELLOW}⚠️  Warning: You have uncommitted changes.${NC}"
    echo ""
    echo "It's recommended to commit or stash your changes before running cleanup."
    echo ""
    read -p "Do you want to continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 1
    fi
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 Cleanup Plan Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Priority 1: Remove logs, backups, security files (~320KB)"
echo "Priority 2: Archive analysis scripts (~70KB)"
echo "Priority 3: Consolidate archives and configs (~5MB)"
echo ""
echo "Total cleanup: ~5.7MB, ~50 files/folders"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

read -p "Do you want to proceed with the cleanup? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                   Priority 1: Logs & Backups                  ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

if [ -f "./cleanup_priority_1.sh" ]; then
    bash cleanup_priority_1.sh
    PRIORITY1_EXIT=$?
    
    if [ $PRIORITY1_EXIT -eq 0 ]; then
        echo -e "${GREEN}✅ Priority 1 completed successfully${NC}"
    else
        echo -e "${RED}❌ Priority 1 failed with exit code: $PRIORITY1_EXIT${NC}"
        exit $PRIORITY1_EXIT
    fi
else
    echo -e "${RED}❌ Error: cleanup_priority_1.sh not found${NC}"
    exit 1
fi

echo ""
read -p "Continue to Priority 2? (Y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Nn]$ ]]; then
    echo "Stopped after Priority 1."
    exit 0
fi

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║              Priority 2: Analysis Scripts                     ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

if [ -f "./cleanup_priority_2.sh" ]; then
    bash cleanup_priority_2.sh
    PRIORITY2_EXIT=$?
    
    if [ $PRIORITY2_EXIT -eq 0 ]; then
        echo -e "${GREEN}✅ Priority 2 completed successfully${NC}"
    else
        echo -e "${RED}❌ Priority 2 failed with exit code: $PRIORITY2_EXIT${NC}"
        exit $PRIORITY2_EXIT
    fi
else
    echo -e "${RED}❌ Error: cleanup_priority_2.sh not found${NC}"
    exit 1
fi

echo ""
read -p "Continue to Priority 3? (Y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Nn]$ ]]; then
    echo "Stopped after Priority 2."
    exit 0
fi

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║           Priority 3: Archive Consolidation                   ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

if [ -f "./cleanup_priority_3.sh" ]; then
    bash cleanup_priority_3.sh
    PRIORITY3_EXIT=$?
    
    if [ $PRIORITY3_EXIT -eq 0 ]; then
        echo -e "${GREEN}✅ Priority 3 completed successfully${NC}"
    else
        echo -e "${RED}❌ Priority 3 failed with exit code: $PRIORITY3_EXIT${NC}"
        exit $PRIORITY3_EXIT
    fi
else
    echo -e "${RED}❌ Error: cleanup_priority_3.sh not found${NC}"
    exit 1
fi

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                  Cleanup Completed! 🎉                        ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "Next steps:"
echo ""
echo "1. Review changes:"
echo "   git status"
echo "   git diff"
echo ""
echo "2. Run tests:"
echo "   cd backend && pytest"
echo ""
echo "3. Test local server:"
echo "   bash local.sh"
echo ""
echo "4. If everything looks good, commit:"
echo "   git add -A"
echo "   git commit -m 'chore: cleanup unnecessary files and update .gitignore'"
echo ""
echo "5. If there are issues, rollback:"
echo "   git reset --hard HEAD"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Optionally run tests
echo ""
read -p "Do you want to run tests now? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "🧪 Running tests..."
    cd backend
    if pytest; then
        echo -e "${GREEN}✅ All tests passed!${NC}"
    else
        echo -e "${RED}❌ Some tests failed. Please review.${NC}"
        echo "You may want to rollback: git reset --hard HEAD"
    fi
    cd ..
fi

echo ""
echo "✅ Cleanup script finished!"

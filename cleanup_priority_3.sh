#!/bin/bash
# Priority 3: Archive consolidation and config cleanup
# Consolidates old archives and config files

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

echo "🧹 Starting Priority 3 Cleanup..."
echo "=================================="

echo ""
echo "📦 Consolidating archive folders..."
mkdir -p archive/old_archives_consolidated

# Move old sqlite files (no longer needed - PostgreSQL in use)
if [ -d "archive/old_sqlite_backups" ]; then
    echo "  Moving old_sqlite_backups..."
    mv -v archive/old_sqlite_backups archive/old_archives_consolidated/
fi

if [ -d "archive/old_sqlite_dbs" ]; then
    echo "  Moving old_sqlite_dbs..."
    mv -v archive/old_sqlite_dbs archive/old_archives_consolidated/
fi

if [ -d "archive/old_sqlite_exports" ]; then
    echo "  Moving old_sqlite_exports..."
    mv -v archive/old_sqlite_exports archive/old_archives_consolidated/
fi

# Remove temporary cleanup folder from previous cleanup
if [ -d "archive/temp_cleanup_20251123" ]; then
    echo "  Removing temp_cleanup_20251123..."
    rm -rfv archive/temp_cleanup_20251123/
fi

echo ""
echo "📦 Consolidating nginx configs..."
mkdir -p archive/old_nginx_configs

if [ -f "nginx_config" ]; then
    mv -v nginx_config archive/old_nginx_configs/
fi

if [ -f "nginx_config_fixed" ]; then
    mv -v nginx_config_fixed archive/old_nginx_configs/
fi

if [ -f "nginx_config_simple" ]; then
    mv -v nginx_config_simple archive/old_nginx_configs/
fi

if [ -f "nginx_config_updated" ]; then
    mv -v nginx_config_updated archive/old_nginx_configs/
fi

if [ -f "nginx_https_config" ]; then
    mv -v nginx_https_config archive/old_nginx_configs/
fi

# Create README for nginx configs
cat > archive/old_nginx_configs/README.md << 'EOF'
# Old Nginx Configurations

This directory contains various historical nginx configuration files.

## Files
- `nginx_config` - Original config
- `nginx_config_fixed` - Fixed version
- `nginx_config_simple` - Simplified version
- `nginx_config_updated` - Updated version
- `nginx_https_config` - HTTPS configuration

## Note
The actual nginx configuration in use on the server is managed by the deployment scripts.
These files are kept for historical reference.

To get the current production configuration:
```bash
ssh your-server
cat /etc/nginx/sites-available/showmethestock
```

Moved from project root on 2025-01-21.
EOF

echo ""
echo "🗑️  Removing unnecessary admin_scanner (static HTML only)..."
if [ -d "backend/admin_scanner" ]; then
    rm -rfv backend/admin_scanner/
fi

echo ""
echo "🗑️  Removing docs.zip (docs/ folder exists with latest documentation)..."
if [ -f "docs.zip" ]; then
    rm -vf docs.zip
fi

echo ""
echo "📝 Creating consolidated archive README..."
cat > archive/old_archives_consolidated/README.md << 'EOF'
# Consolidated Old Archives

This directory contains historical archives that are no longer needed for active development.

## Contents
- `old_sqlite_backups/` - SQLite database backups (PostgreSQL now in use)
- `old_sqlite_dbs/` - SQLite database files (PostgreSQL now in use)
- `old_sqlite_exports/` - SQLite export files (PostgreSQL now in use)

## Database Migration
The project migrated from SQLite to PostgreSQL. These files are kept for historical reference
but are not used in production.

## Deletion Consideration
These files can be safely deleted if:
1. PostgreSQL migration is confirmed stable (✅ Confirmed)
2. No need to reference old SQLite data
3. Git history is sufficient for audit trail

Consolidated on 2025-01-21.
EOF

echo ""
echo "=================================="
echo "✅ Priority 3 cleanup completed!"
echo ""
echo "📊 Cleanup Summary:"
echo "  - SQLite archives: Consolidated"
echo "  - Nginx configs: Moved to archive"
echo "  - admin_scanner: Removed"
echo "  - docs.zip: Removed"
echo ""
echo "Next steps:"
echo "1. Run: git status"
echo "2. Review changes: git diff"
echo "3. Test: bash local.sh"
echo "4. Commit: git add -A && git commit -m 'chore: cleanup unnecessary files'"

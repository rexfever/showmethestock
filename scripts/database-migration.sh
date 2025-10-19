#!/bin/bash

# 데이터베이스 마이그레이션 스크립트
# 배포 시 DB 스키마 변경사항을 안전하게 적용

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0;m'

# 로그 함수
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 설정
DB_DIR="/home/ubuntu/showmethestock/backend"
BACKUP_DIR="/home/ubuntu/backups/db"
MIGRATION_DIR="/home/ubuntu/showmethestock/backend/migrations"

# 백업 디렉토리 생성
mkdir -p "$BACKUP_DIR"

# DB 백업 함수
backup_database() {
    local db_file=$1
    local backup_file="$BACKUP_DIR/${db_file}.backup.$(date +%Y%m%d_%H%M%S)"
    
    log_info "DB 백업 중: $db_file"
    
    if [ -f "$DB_DIR/$db_file" ]; then
        cp "$DB_DIR/$db_file" "$backup_file"
        log_success "백업 완료: $backup_file"
        return 0
    else
        log_warning "DB 파일이 존재하지 않음: $db_file"
        return 1
    fi
}

# DB 복원 함수
restore_database() {
    local db_file=$1
    local backup_file=$2
    
    log_info "DB 복원 중: $db_file"
    
    if [ -f "$backup_file" ]; then
        cp "$backup_file" "$DB_DIR/$db_file"
        log_success "복원 완료: $db_file"
        return 0
    else
        log_error "백업 파일이 존재하지 않음: $backup_file"
        return 1
    fi
}

# 마이그레이션 실행 함수
run_migration() {
    local migration_file=$1
    
    log_info "마이그레이션 실행: $migration_file"
    
    if [ -f "$migration_file" ]; then
        # Python으로 마이그레이션 실행
        if python3 "$migration_file"; then
            log_success "마이그레이션 성공: $migration_file"
            return 0
        else
            log_error "마이그레이션 실패: $migration_file"
            return 1
        fi
    else
        log_warning "마이그레이션 파일이 존재하지 않음: $migration_file"
        return 1
    fi
}

# 스키마 검증 함수
validate_schema() {
    local db_file=$1
    
    log_info "스키마 검증 중: $db_file"
    
    # Python으로 스키마 검증
    if python3 -c "
import sqlite3
import sys

try:
    conn = sqlite3.connect('$DB_DIR/$db_file')
    cursor = conn.cursor()
    
    # 테이블 목록 조회
    cursor.execute(\"SELECT name FROM sqlite_master WHERE type='table'\")
    tables = cursor.fetchall()
    
    print(f'✅ DB 연결 성공: {len(tables)}개 테이블')
    
    # 각 테이블의 레코드 수 확인
    for table in tables:
        table_name = table[0]
        cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
        count = cursor.fetchone()[0]
        print(f'  - {table_name}: {count}개 레코드')
    
    conn.close()
    print('✅ 스키마 검증 완료')
    
except Exception as e:
    print(f'❌ 스키마 검증 실패: {e}')
    sys.exit(1)
" 2>/dev/null; then
        log_success "스키마 검증 통과: $db_file"
        return 0
    else
        log_error "스키마 검증 실패: $db_file"
        return 1
    fi
}

# 메인 마이그레이션 함수
main() {
    local action=${1:-migrate}
    
    case $action in
        "migrate")
            migrate_databases
            ;;
        "rollback")
            rollback_databases
            ;;
        "validate")
            validate_databases
            ;;
        "backup")
            backup_all_databases
            ;;
        *)
            echo "사용법: $0 [migrate|rollback|validate|backup]"
            exit 1
            ;;
    esac
}

# 데이터베이스 마이그레이션
migrate_databases() {
    log_info "🚀 데이터베이스 마이그레이션 시작"
    
    # 마이그레이션 디렉토리 생성
    mkdir -p "$MIGRATION_DIR"
    
    # 모든 DB 파일 백업
    local db_files=("snapshots.db" "portfolio.db" "email_verifications.db" "news_data.db")
    
    for db_file in "${db_files[@]}"; do
        backup_database "$db_file"
    done
    
    # 마이그레이션 파일 실행
    if [ -d "$MIGRATION_DIR" ]; then
        for migration_file in "$MIGRATION_DIR"/*.py; do
            if [ -f "$migration_file" ]; then
                if ! run_migration "$migration_file"; then
                    log_error "마이그레이션 실패. 롤백을 실행합니다."
                    rollback_databases
                    exit 1
                fi
            fi
        done
    else
        log_info "마이그레이션 파일이 없습니다. 스키마 검증만 수행합니다."
    fi
    
    # 스키마 검증
    for db_file in "${db_files[@]}"; do
        if [ -f "$DB_DIR/$db_file" ]; then
            if ! validate_schema "$db_file"; then
                log_error "스키마 검증 실패. 롤백을 실행합니다."
                rollback_databases
                exit 1
            fi
        fi
    done
    
    log_success "🎉 데이터베이스 마이그레이션 완료"
}

# 데이터베이스 롤백
rollback_databases() {
    log_info "🔄 데이터베이스 롤백 시작"
    
    local db_files=("snapshots.db" "portfolio.db" "email_verifications.db" "news_data.db")
    
    # 가장 최근 백업 파일 찾기
    for db_file in "${db_files[@]}"; do
        local latest_backup=$(ls -t "$BACKUP_DIR/${db_file}.backup."* 2>/dev/null | head -1)
        
        if [ -n "$latest_backup" ]; then
            if restore_database "$db_file" "$latest_backup"; then
                log_success "롤백 완료: $db_file"
            else
                log_error "롤백 실패: $db_file"
            fi
        else
            log_warning "백업 파일이 없음: $db_file"
        fi
    done
    
    log_success "🎉 데이터베이스 롤백 완료"
}

# 데이터베이스 검증
validate_databases() {
    log_info "🔍 데이터베이스 검증 시작"
    
    local db_files=("snapshots.db" "portfolio.db" "email_verifications.db" "news_data.db")
    local all_valid=true
    
    for db_file in "${db_files[@]}"; do
        if [ -f "$DB_DIR/$db_file" ]; then
            if ! validate_schema "$db_file"; then
                all_valid=false
            fi
        else
            log_warning "DB 파일이 존재하지 않음: $db_file"
        fi
    done
    
    if [ "$all_valid" = true ]; then
        log_success "🎉 모든 데이터베이스 검증 통과"
        exit 0
    else
        log_error "❌ 일부 데이터베이스 검증 실패"
        exit 1
    fi
}

# 모든 데이터베이스 백업
backup_all_databases() {
    log_info "💾 데이터베이스 백업 시작"
    
    local db_files=("snapshots.db" "portfolio.db" "email_verifications.db" "news_data.db")
    
    for db_file in "${db_files[@]}"; do
        backup_database "$db_file"
    done
    
    log_success "🎉 모든 데이터베이스 백업 완료"
}

# 스크립트 실행
if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
    main "$@"
fi

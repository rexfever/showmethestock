#!/usr/bin/env python3
"""
서버 DB 데이터를 로컬 DB로 동기화하는 스크립트

사용법:
    python3 sync_server_data.py

환경 변수:
    SERVER_DATABASE_URL: 서버 DB 연결 문자열 (예: postgresql://user:pass@server:5432/dbname)
    DATABASE_URL: 로컬 DB 연결 문자열 (기본값: .env 파일에서 읽음)
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()
backend_env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(backend_env_path):
    load_dotenv(dotenv_path=backend_env_path, override=True)

from db_manager import db_manager
from psycopg_pool import ConnectionPool
from psycopg import sql
from psycopg.types.json import Json
import psycopg


def get_server_db_url():
    """서버 DB 연결 URL 반환"""
    server_db_url = os.getenv("SERVER_DATABASE_URL")
    if not server_db_url:
        raise ValueError(
            "SERVER_DATABASE_URL 환경 변수가 설정되지 않았습니다.\n"
            "예: export SERVER_DATABASE_URL=postgresql://user:pass@server:5432/dbname\n"
            "또는 SSH 터널링 사용: export SERVER_DATABASE_URL=postgresql://user:pass@localhost:5433/dbname"
        )
    
    print(f"🔗 서버 DB 연결 정보 확인...")
    print(f"   연결 정보: {server_db_url.split('@')[0]}@***")
    return server_db_url


def sync_table(server_db_url, target_pool, table_name, batch_size=1000):
    """테이블 동기화"""
    print(f"\n📊 {table_name} 테이블 동기화 시작...")
    
    # 직접 연결 사용 (ConnectionPool 대신)
    with psycopg.connect(server_db_url) as source_conn:
        with source_conn.cursor() as source_cur:
            # 소스 테이블 데이터 개수 확인
            source_cur.execute(f"SELECT COUNT(*) FROM {table_name}")
            source_count = source_cur.fetchone()[0]
            print(f"  - 서버 데이터: {source_count}개")
            
            if source_count == 0:
                print(f"  ⚠️ 서버에 데이터가 없습니다. 건너뜁니다.")
                return 0
            
            # 타겟 테이블 존재 확인 및 컬럼 확인
            from db_manager import db_manager
            with db_manager.get_cursor(commit=False) as check_cur:
                # 테이블 존재 확인
                check_cur.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = %s
                    )
                """, (table_name,))
                table_exists = check_cur.fetchone()[0]
                
                if not table_exists:
                    print(f"  ⚠️ 로컬 DB에 {table_name} 테이블이 없습니다. 건너뜁니다.")
                    return 0
                
                check_cur.execute(f"""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = %s 
                    ORDER BY ordinal_position
                """, (table_name,))
                target_columns = [row[0] for row in check_cur.fetchall()]
            
            if not target_columns:
                print(f"  ⚠️ 로컬 DB에 {table_name} 테이블의 컬럼이 없습니다. 건너뜁니다.")
                return 0
            
            # 소스 데이터 가져오기 (타겟에 있는 컬럼만)
            columns_str = ', '.join(target_columns)
            source_cur.execute(f"SELECT {columns_str} FROM {table_name}")
            columns = [desc[0] for desc in source_cur.description]
            print(f"  - 컬럼: {len(columns)}개 (타겟과 일치하는 컬럼만)")
            
            # JSONB 컬럼 확인 (dict 타입 처리 필요)
            jsonb_columns = set()
            for i, col in enumerate(columns):
                col_type = source_cur.description[i].type_code
                if col_type and 'json' in str(col_type).lower():
                    jsonb_columns.add(col)
            
            # 타겟 테이블에 데이터 삽입
            from db_manager import db_manager
            import json
            with db_manager.get_cursor(commit=True) as target_cur:
                # 기존 데이터 삭제 (선택사항 - 주석 해제하면 전체 교체)
                # target_cur.execute(f"TRUNCATE TABLE {table_name} CASCADE")
                
                inserted = 0
                batch = []
                
                for row in source_cur:
                    # 모든 dict/list 타입을 Json으로 변환
                    processed_row = list(row)
                    for i, (val, col) in enumerate(zip(processed_row, columns)):
                        if val is not None and isinstance(val, (dict, list)):
                            # psycopg의 Json 어댑터 사용
                            processed_row[i] = Json(val)
                        # users 테이블의 provider_id가 null이면 email 사용
                        elif table_name == 'users' and col == 'provider_id' and val is None:
                            # email 컬럼 찾기
                            email_idx = columns.index('email') if 'email' in columns else None
                            if email_idx is not None and processed_row[email_idx]:
                                processed_row[i] = processed_row[email_idx]
                            else:
                                processed_row[i] = 'local'
                    batch.append(tuple(processed_row))
                    
                    if len(batch) >= batch_size:
                        # 배치 삽입
                        placeholders = ', '.join(['%s'] * len(columns))
                        columns_str = ', '.join(columns)
                        
                        # Primary Key 동적 확인
                        from db_manager import db_manager
                        with db_manager.get_cursor(commit=False) as pk_cur:
                            pk_cur.execute("""
                                SELECT constraint_name, constraint_type
                                FROM information_schema.table_constraints
                                WHERE table_name = %s AND constraint_type = 'PRIMARY KEY'
                            """, (table_name,))
                            pk_info = pk_cur.fetchone()
                            
                            if pk_info:
                                pk_cur.execute("""
                                    SELECT column_name
                                    FROM information_schema.key_column_usage
                                    WHERE constraint_name = %s
                                    ORDER BY ordinal_position
                                """, (pk_info[0],))
                                pk_cols = [row[0] for row in pk_cur.fetchall()]
                                conflict_cols = ', '.join(pk_cols)
                                
                                # UPSERT (ON CONFLICT DO UPDATE)
                                update_set = ', '.join([f"{col} = EXCLUDED.{col}" for col in columns if col not in pk_cols])
                                query = f"""
                                    INSERT INTO {table_name} ({columns_str})
                                    VALUES ({placeholders})
                                    ON CONFLICT ({conflict_cols}) DO UPDATE SET {update_set}
                                """
                            else:
                                # Primary Key가 없으면 일반 INSERT
                                query = f"""
                                    INSERT INTO {table_name} ({columns_str})
                                    VALUES ({placeholders})
                                    ON CONFLICT DO NOTHING
                                """
                        
                        target_cur.executemany(query, batch)
                        inserted += len(batch)
                        batch = []
                        
                        if inserted % (batch_size * 10) == 0:
                            print(f"  - 진행: {inserted}/{source_count} ({inserted*100//source_count}%)")
                
                # 남은 배치 처리
                if batch:
                    placeholders = ', '.join(['%s'] * len(columns))
                    columns_str = ', '.join(columns)
                    
                    # Primary Key 동적 확인 (배치 처리용)
                    from db_manager import db_manager
                    with db_manager.get_cursor(commit=False) as pk_cur:
                        pk_cur.execute("""
                            SELECT constraint_name, constraint_type
                            FROM information_schema.table_constraints
                            WHERE table_name = %s AND constraint_type = 'PRIMARY KEY'
                        """, (table_name,))
                        pk_info = pk_cur.fetchone()
                        
                        if pk_info:
                            pk_cur.execute("""
                                SELECT column_name
                                FROM information_schema.key_column_usage
                                WHERE constraint_name = %s
                                ORDER BY ordinal_position
                            """, (pk_info[0],))
                            pk_cols = [row[0] for row in pk_cur.fetchall()]
                            conflict_cols = ', '.join(pk_cols)
                            
                            # UPSERT (ON CONFLICT DO UPDATE)
                            update_set = ', '.join([f"{col} = EXCLUDED.{col}" for col in columns if col not in pk_cols])
                            query = f"""
                                INSERT INTO {table_name} ({columns_str})
                                VALUES ({placeholders})
                                ON CONFLICT ({conflict_cols}) DO UPDATE SET {update_set}
                            """
                        else:
                            # Primary Key가 없으면 일반 INSERT
                            query = f"""
                                INSERT INTO {table_name} ({columns_str})
                                VALUES ({placeholders})
                                ON CONFLICT DO NOTHING
                            """
                    
                    target_cur.executemany(query, batch)
                    inserted += len(batch)
                
                # 타겟 테이블 데이터 개수 확인
                target_cur.execute(f"SELECT COUNT(*) FROM {table_name}")
                target_count = target_cur.fetchone()[0]
                
                print(f"  ✅ 동기화 완료: {inserted}개 삽입, 총 {target_count}개")
                return inserted


def main():
    """메인 함수"""
    print("=" * 60)
    print("🚀 서버 DB → 로컬 DB 동기화 시작")
    print("=" * 60)
    
    try:
        # 서버 DB 연결 정보 확인
        server_db_url = get_server_db_url()
        
        # 로컬 DB 연결 확인
        print(f"\n🔗 로컬 DB 연결 확인...")
        with db_manager.get_cursor(commit=False) as cur:
            cur.execute("SELECT version()")
            version = cur.fetchone()[0]
            print(f"  ✅ 로컬 DB 연결 성공: {version[:50]}...")
        
        # 동기화할 테이블 목록 (전체 테이블)
        # 서버 DB에서 테이블 목록 가져오기
        with psycopg.connect(server_db_url) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_type = 'BASE TABLE'
                    AND table_name NOT IN ('pg_stat_statements', 'pg_stat_statements_info')
                    ORDER BY table_name
                """)
                tables_to_sync = [row[0] for row in cur.fetchall()]
        
        print(f"\n📋 동기화할 테이블: {len(tables_to_sync)}개")
        for table in tables_to_sync:
            print(f"   - {table}")
        
        total_synced = 0
        start_time = datetime.now()
        
        # 서버 DB URL 가져오기
        server_db_url = get_server_db_url()
        
        for table_name in tables_to_sync:
            try:
                synced = sync_table(server_db_url, None, table_name)
                total_synced += synced
            except Exception as e:
                print(f"  ❌ {table_name} 동기화 실패: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        elapsed = (datetime.now() - start_time).total_seconds()
        
        print("\n" + "=" * 60)
        print(f"✅ 동기화 완료!")
        print(f"  - 총 {total_synced}개 레코드 동기화")
        print(f"  - 소요 시간: {elapsed:.2f}초")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 동기화 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()


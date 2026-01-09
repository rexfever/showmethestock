"""
스캐너 설정 DB 관리
"""
from typing import Optional, Dict
from db_manager import db_manager
import json


def create_scanner_settings_table(cur):
    """scanner_settings 테이블 생성"""
    cur.execute("""
        CREATE TABLE IF NOT EXISTS scanner_settings(
            id SERIAL PRIMARY KEY,
            setting_key TEXT NOT NULL UNIQUE,
            setting_value TEXT NOT NULL,
            description TEXT,
            updated_by TEXT,
            updated_at TIMESTAMP DEFAULT NOW(),
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    
    # 기본값 설정 (없는 경우만)
    cur.execute("SELECT COUNT(*) FROM scanner_settings WHERE setting_key = 'scanner_version'")
    if cur.fetchone()[0] == 0:
        cur.execute("""
            INSERT INTO scanner_settings (setting_key, setting_value, description)
            VALUES ('scanner_version', 'v1', '스캐너 버전 (v1 또는 v2)')
        """)
    
    cur.execute("SELECT COUNT(*) FROM scanner_settings WHERE setting_key = 'scanner_v2_enabled'")
    if cur.fetchone()[0] == 0:
        cur.execute("""
            INSERT INTO scanner_settings (setting_key, setting_value, description)
            VALUES ('scanner_v2_enabled', 'false', '스캐너 V2 활성화 여부')
        """)
    
    cur.execute("SELECT COUNT(*) FROM scanner_settings WHERE setting_key = 'regime_version'")
    if cur.fetchone()[0] == 0:
        cur.execute("""
            INSERT INTO scanner_settings (setting_key, setting_value, description)
            VALUES ('regime_version', 'v1', '레짐 분석 버전 (v1, v3, v4)')
        """)


def get_scanner_setting(key: str, default: str = None) -> Optional[str]:
    """
    스캐너 설정 조회 (DB에서)
    
    Args:
        key: 설정 키
        default: 기본값 (DB에 없을 때)
    
    Returns:
        설정 값 또는 기본값
    """
    try:
        with db_manager.get_cursor(commit=False) as cur:
            create_scanner_settings_table(cur)
            cur.execute("""
                SELECT setting_value 
                FROM scanner_settings 
                WHERE setting_key = %s
            """, (key,))
            row = cur.fetchone()
            if row:
                return row[0]
            return default
    except Exception as e:
        print(f"스캐너 설정 조회 오류 ({key}): {e}")
        return default


def set_scanner_setting(key: str, value: str, description: str = None, updated_by: str = None) -> bool:
    """
    스캐너 설정 저장/업데이트 (DB에)
    
    Args:
        key: 설정 키
        value: 설정 값
        description: 설명 (선택)
        updated_by: 수정자 (선택)
    
    Returns:
        성공 여부
    """
    try:
        with db_manager.get_cursor(commit=True) as cur:
            create_scanner_settings_table(cur)
            cur.execute("""
                INSERT INTO scanner_settings (setting_key, setting_value, description, updated_by)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (setting_key) 
                DO UPDATE SET 
                    setting_value = EXCLUDED.setting_value,
                    description = COALESCE(EXCLUDED.description, scanner_settings.description),
                    updated_by = EXCLUDED.updated_by,
                    updated_at = NOW()
            """, (key, value, description, updated_by))
            return True
    except Exception as e:
        print(f"스캐너 설정 저장 오류 ({key}): {e}")
        return False


def get_all_scanner_settings() -> Dict[str, str]:
    """
    모든 스캐너 설정 조회
    
    Returns:
        {key: value} 딕셔너리
    """
    try:
        with db_manager.get_cursor(commit=False) as cur:
            create_scanner_settings_table(cur)
            cur.execute("""
                SELECT setting_key, setting_value 
                FROM scanner_settings
            """)
            rows = cur.fetchall()
            return {row[0]: row[1] for row in rows}
    except Exception as e:
        print(f"스캐너 설정 전체 조회 오류: {e}")
        return {}


def get_scanner_version() -> str:
    """스캐너 버전 조회 (DB 우선, 없으면 .env)"""
    db_value = get_scanner_setting('scanner_version')
    if db_value:
        return db_value
    
    # DB에 없으면 .env에서 읽기
    import os
    return os.getenv("SCANNER_VERSION", "v1")


def get_scanner_v2_enabled() -> bool:
    """스캐너 V2 활성화 여부 조회 (DB 우선, 없으면 .env)"""
    db_value = get_scanner_setting('scanner_v2_enabled')
    if db_value:
        return db_value.lower() == 'true'
    
    # DB에 없으면 .env에서 읽기
    import os
    return os.getenv("SCANNER_V2_ENABLED", "false").lower() == "true"


def get_regime_version() -> str:
    """레짐 분석 버전 조회 (DB 우선, 없으면 .env)"""
    db_value = get_scanner_setting('regime_version')
    if db_value:
        return db_value
    
    # DB에 없으면 .env에서 읽기
    import os
    return os.getenv("REGIME_VERSION", "v1")


def get_active_engine() -> str:
    """활성 엔진 조회 (DB 우선, 없으면 기본값 v1)"""
    db_value = get_scanner_setting('active_engine')
    if db_value:
        return db_value
    
    # DB에 없으면 기본값 v1 반환
    return "v1"


def set_active_engine(engine: str, updated_by: str = None) -> bool:
    """활성 엔진 설정 (v1, v2, v3)"""
    if engine not in ['v1', 'v2', 'v3']:
        return False
    
    return set_scanner_setting(
        'active_engine', 
        engine, 
        description=f'활성 스캐너 엔진 ({engine})',
        updated_by=updated_by
    )


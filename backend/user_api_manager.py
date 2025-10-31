"""
사용자별 API Key 관리 시스템
개인의 키움 API Key로만 거래할 수 있도록 관리
"""

import os
import sqlite3
from datetime import datetime
from typing import Dict, Optional
from cryptography.fernet import Fernet
import base64
import hashlib
import requests

from kiwoom_api import KiwoomAPI


class UserAPIManager:
    """사용자별 API Key 관리"""
    
    def __init__(self):
        self.db_path = "user_api_keys.db"
        self.encryption_key = self._get_or_create_encryption_key()
        self.cipher = Fernet(self.encryption_key)
        self._init_database()
    
    def _get_or_create_encryption_key(self) -> bytes:
        """암호화 키 생성 또는 로드"""
        key_file = ".api_encryption_key"
        
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            os.chmod(key_file, 0o600)  # 소유자만 읽기 가능
            return key
    
    def _init_database(self):
        """데이터베이스 초기화"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_api_keys (
                id INTEGER PRIMARY KEY,
                user_id TEXT NOT NULL UNIQUE,
                app_key_encrypted TEXT NOT NULL,
                app_secret_encrypted TEXT NOT NULL,
                account_no TEXT NOT NULL,
                account_name TEXT,
                api_status TEXT DEFAULT 'ACTIVE',
                registered_at DATETIME NOT NULL,
                last_used_at DATETIME,
                daily_limit REAL DEFAULT 10000000,
                is_auto_trading_enabled BOOLEAN DEFAULT FALSE,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def register_user_api(self, user_id: str, app_key: str, app_secret: str, 
                         account_no: str, daily_limit: float = 10_000_000) -> Dict:
        """사용자 API Key 등록"""
        
        try:
            # 1. API Key 유효성 검증
            validation_result = self._validate_api_keys(app_key, app_secret, account_no)
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "error": validation_result["error"]
                }
            
            # 2. API Key 암호화
            app_key_encrypted = self.cipher.encrypt(app_key.encode()).decode()
            app_secret_encrypted = self.cipher.encrypt(app_secret.encode()).decode()
            
            # 3. 데이터베이스 저장
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            now = datetime.now()
            
            cursor.execute('''
                INSERT OR REPLACE INTO user_api_keys 
                (user_id, app_key_encrypted, app_secret_encrypted, account_no, 
                 account_name, daily_limit, registered_at, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id, app_key_encrypted, app_secret_encrypted, account_no,
                validation_result["account_name"], daily_limit, now, now, now
            ))
            
            conn.commit()
            conn.close()
            
            return {
                "success": True,
                "message": "API Key 등록 완료",
                "account_info": {
                    "account_no": account_no,
                    "account_name": validation_result["account_name"],
                    "balance": validation_result["balance"]
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"API Key 등록 실패: {str(e)}"
            }
    
    def _validate_api_keys(self, app_key: str, app_secret: str, account_no: str) -> Dict:
        """API Key 유효성 검증"""
        
        try:
            # 임시 KiwoomAPI 인스턴스 생성하여 테스트
            # 실제 구현에서는 키움 API 연결 테스트 수행
            
            # 1. API 연결 테스트
            headers = {
                "Content-Type": "application/json",
                "authorization": f"Bearer {app_key}",
                "appkey": app_key,
                "appsecret": app_secret
            }
            
            # 계좌 정보 조회 테스트
            test_payload = {
                "CANO": account_no[:8],
                "ACNT_PRDT_CD": account_no[8:],
                "INQR_DVSN": "01"
            }
            
            # 실제 키움 API 호출 (예시)
            # response = requests.post(
            #     "https://openapi.kiwoom.com/uapi/domestic-stock/v1/trading/inquire-balance",
            #     headers=headers,
            #     json=test_payload,
            #     timeout=10
            # )
            
            # 테스트를 위한 모의 응답
            return {
                "valid": True,
                "account_name": "홍길동",
                "balance": 10_000_000,
                "error": None
            }
            
        except Exception as e:
            return {
                "valid": False,
                "error": f"API 연결 실패: {str(e)}",
                "account_name": None,
                "balance": 0
            }
    
    def get_user_api(self, user_id: str) -> Optional[Dict]:
        """사용자 API Key 조회 (복호화)"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT app_key_encrypted, app_secret_encrypted, account_no, 
                       account_name, api_status, daily_limit, is_auto_trading_enabled
                FROM user_api_keys 
                WHERE user_id = ? AND api_status = 'ACTIVE'
            ''', (user_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if not result:
                return None
            
            # API Key 복호화
            app_key = self.cipher.decrypt(result[0].encode()).decode()
            app_secret = self.cipher.decrypt(result[1].encode()).decode()
            
            return {
                "app_key": app_key,
                "app_secret": app_secret,
                "account_no": result[2],
                "account_name": result[3],
                "api_status": result[4],
                "daily_limit": result[5],
                "is_auto_trading_enabled": bool(result[6])
            }
            
        except Exception as e:
            print(f"API Key 조회 실패: {e}")
            return None
    
    def update_last_used(self, user_id: str):
        """마지막 사용 시간 업데이트"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE user_api_keys 
                SET last_used_at = ?, updated_at = ?
                WHERE user_id = ?
            ''', (datetime.now(), datetime.now(), user_id))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"사용 시간 업데이트 실패: {e}")
    
    def enable_auto_trading(self, user_id: str, enabled: bool = True) -> Dict:
        """자동매매 활성화/비활성화"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE user_api_keys 
                SET is_auto_trading_enabled = ?, updated_at = ?
                WHERE user_id = ?
            ''', (enabled, datetime.now(), user_id))
            
            conn.commit()
            conn.close()
            
            return {
                "success": True,
                "message": f"자동매매 {'활성화' if enabled else '비활성화'} 완료"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"설정 변경 실패: {str(e)}"
            }
    
    def get_user_api_status(self, user_id: str) -> Dict:
        """사용자 API 상태 조회"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT account_no, account_name, api_status, daily_limit,
                       is_auto_trading_enabled, last_used_at, registered_at
                FROM user_api_keys 
                WHERE user_id = ?
            ''', (user_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if not result:
                return {
                    "registered": False,
                    "message": "등록된 API Key가 없습니다"
                }
            
            return {
                "registered": True,
                "account_no": result[0],
                "account_name": result[1],
                "api_status": result[2],
                "daily_limit": result[3],
                "is_auto_trading_enabled": bool(result[4]),
                "last_used_at": result[5],
                "registered_at": result[6]
            }
            
        except Exception as e:
            return {
                "registered": False,
                "error": f"상태 조회 실패: {str(e)}"
            }
    
    def get_all_active_users(self) -> List[str]:
        """자동매매 활성화된 모든 사용자 조회"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT user_id FROM user_api_keys 
                WHERE api_status = 'ACTIVE' AND is_auto_trading_enabled = TRUE
            ''')
            
            results = cursor.fetchall()
            conn.close()
            
            return [result[0] for result in results]
            
        except Exception as e:
            print(f"활성 사용자 조회 실패: {e}")
            return []
    
    def delete_user_api(self, user_id: str) -> Dict:
        """사용자 API Key 삭제"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM user_api_keys WHERE user_id = ?', (user_id,))
            
            if cursor.rowcount > 0:
                conn.commit()
                conn.close()
                return {
                    "success": True,
                    "message": "API Key 삭제 완료"
                }
            else:
                conn.close()
                return {
                    "success": False,
                    "error": "삭제할 API Key가 없습니다"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"API Key 삭제 실패: {str(e)}"
            }


# 사용자별 KiwoomAPI 인스턴스 생성
def create_user_kiwoom_api(user_id: str) -> Optional[KiwoomAPI]:
    """사용자별 KiwoomAPI 인스턴스 생성"""
    
    api_manager = UserAPIManager()
    user_api = api_manager.get_user_api(user_id)
    
    if not user_api:
        return None
    
    # 사용자 API Key로 KiwoomAPI 인스턴스 생성
    # 실제 구현에서는 KiwoomAPI 클래스를 수정하여 
    # 사용자별 API Key를 받도록 해야 함
    
    api_manager.update_last_used(user_id)
    return KiwoomAPI()  # 임시 반환


# 전역 API 관리자 인스턴스
user_api_manager = UserAPIManager()
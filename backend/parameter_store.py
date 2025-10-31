"""
AWS Parameter Store 관리 클래스
"""
import boto3
from botocore.exceptions import ClientError
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)

class ParameterStoreManager:
    def __init__(self, region_name='ap-northeast-2'):
        self.ssm = boto3.client('ssm', region_name=region_name)
        self.base_path = '/showmethestock'
    
    def get_parameter(self, path: str, decrypt: bool = True) -> Optional[str]:
        """Parameter Store에서 값 조회"""
        try:
            response = self.ssm.get_parameter(
                Name=path,
                WithDecryption=decrypt
            )
            return response['Parameter']['Value']
        except ClientError as e:
            if e.response['Error']['Code'] == 'ParameterNotFound':
                logger.warning(f"Parameter not found: {path}")
                return None
            else:
                logger.error(f"Error getting parameter {path}: {e}")
                raise
    
    def set_parameter(self, path: str, value: str, description: str = "", secure: bool = True) -> bool:
        """Parameter Store에 값 저장"""
        try:
            self.ssm.put_parameter(
                Name=path,
                Value=value,
                Description=description,
                Type='SecureString' if secure else 'String',
                Overwrite=True
            )
            return True
        except ClientError as e:
            logger.error(f"Error setting parameter {path}: {e}")
            return False
    
    def delete_parameter(self, path: str) -> bool:
        """Parameter Store에서 값 삭제"""
        try:
            self.ssm.delete_parameter(Name=path)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ParameterNotFound':
                return True  # 이미 없으면 성공으로 처리
            logger.error(f"Error deleting parameter {path}: {e}")
            return False
    
    def get_user_kiwoom_credentials(self, user_id: int) -> Dict[str, Optional[str]]:
        """사용자별 키움 API 인증 정보 조회"""
        base_path = f"{self.base_path}/users/{user_id}/kiwoom"
        return {
            'api_key': self.get_parameter(f"{base_path}/api_key"),
            'api_secret': self.get_parameter(f"{base_path}/api_secret"),
            'account_no': self.get_parameter(f"{base_path}/account_no")
        }
    
    def set_user_kiwoom_credentials(self, user_id: int, api_key: str, api_secret: str, account_no: str = None) -> bool:
        """사용자별 키움 API 인증 정보 저장"""
        try:
            base_path = f"{self.base_path}/users/{user_id}/kiwoom"
            success = True
            success &= self.set_parameter(f"{base_path}/api_key", api_key, f'Kiwoom API Key for user {user_id}')
            success &= self.set_parameter(f"{base_path}/api_secret", api_secret, f'Kiwoom API Secret for user {user_id}')
            if account_no:
                success &= self.set_parameter(f"{base_path}/account_no", account_no, f'Kiwoom Account Number for user {user_id}')
            return success
        except Exception as e:
            logger.error(f"Error setting kiwoom credentials for user {user_id}: {e}")
            return False
    
    def delete_user_kiwoom_credentials(self, user_id: int) -> bool:
        """사용자별 키움 API 인증 정보 삭제"""
        try:
            base_path = f"{self.base_path}/users/{user_id}/kiwoom"
            success = True
            success &= self.delete_parameter(f"{base_path}/api_key")
            success &= self.delete_parameter(f"{base_path}/api_secret")
            success &= self.delete_parameter(f"{base_path}/account_no")
            return success
        except Exception as e:
            logger.error(f"Error deleting kiwoom credentials for user {user_id}: {e}")
            return False
    
    def list_all_user_keys(self) -> Dict[int, Dict[str, bool]]:
        """모든 사용자의 키 존재 여부 조회 (관리자용)"""
        try:
            response = self.ssm.get_parameters_by_path(
                Path=f"{self.base_path}/users",
                Recursive=True
            )
            
            users = {}
            for param in response['Parameters']:
                # /showmethestock/users/123/kiwoom/api_key 형태에서 user_id 추출
                parts = param['Name'].split('/')
                if len(parts) >= 5 and parts[3].isdigit():
                    user_id = int(parts[3])
                    key_type = parts[5]  # api_key, api_secret, account_no
                    
                    if user_id not in users:
                        users[user_id] = {'api_key': False, 'api_secret': False, 'account_no': False}
                    
                    users[user_id][key_type] = True
            
            return users
        except Exception as e:
            logger.error(f"Error listing user keys: {e}")
            return {}
    
    def delete_all_user_keys(self, user_id: int) -> bool:
        """특정 사용자의 모든 키 삭제 (관리자용)"""
        return self.delete_user_kiwoom_credentials(user_id)

# 전역 인스턴스
parameter_store = ParameterStoreManager()
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
        self.base_path = '/showmethestock/kiwoom'
    
    def get_parameter(self, name: str, decrypt: bool = True) -> Optional[str]:
        """Parameter Store에서 값 조회"""
        try:
            response = self.ssm.get_parameter(
                Name=f"{self.base_path}/{name}",
                WithDecryption=decrypt
            )
            return response['Parameter']['Value']
        except ClientError as e:
            if e.response['Error']['Code'] == 'ParameterNotFound':
                logger.warning(f"Parameter not found: {name}")
                return None
            else:
                logger.error(f"Error getting parameter {name}: {e}")
                raise
    
    def set_parameter(self, name: str, value: str, description: str = "", secure: bool = True) -> bool:
        """Parameter Store에 값 저장"""
        try:
            self.ssm.put_parameter(
                Name=f"{self.base_path}/{name}",
                Value=value,
                Description=description,
                Type='SecureString' if secure else 'String',
                Overwrite=True
            )
            return True
        except ClientError as e:
            logger.error(f"Error setting parameter {name}: {e}")
            return False
    
    def delete_parameter(self, name: str) -> bool:
        """Parameter Store에서 값 삭제"""
        try:
            self.ssm.delete_parameter(Name=f"{self.base_path}/{name}")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ParameterNotFound':
                return True  # 이미 없으면 성공으로 처리
            logger.error(f"Error deleting parameter {name}: {e}")
            return False
    
    def get_kiwoom_credentials(self) -> Dict[str, Optional[str]]:
        """키움 API 인증 정보 조회"""
        return {
            'api_key': self.get_parameter('api_key'),
            'api_secret': self.get_parameter('api_secret'),
            'account_no': self.get_parameter('account_no')
        }
    
    def set_kiwoom_credentials(self, api_key: str, api_secret: str, account_no: str = None) -> bool:
        """키움 API 인증 정보 저장"""
        try:
            success = True
            success &= self.set_parameter('api_key', api_key, 'Kiwoom API Key')
            success &= self.set_parameter('api_secret', api_secret, 'Kiwoom API Secret')
            if account_no:
                success &= self.set_parameter('account_no', account_no, 'Kiwoom Account Number')
            return success
        except Exception as e:
            logger.error(f"Error setting kiwoom credentials: {e}")
            return False
    
    def delete_kiwoom_credentials(self) -> bool:
        """키움 API 인증 정보 삭제"""
        try:
            success = True
            success &= self.delete_parameter('api_key')
            success &= self.delete_parameter('api_secret')
            success &= self.delete_parameter('account_no')
            return success
        except Exception as e:
            logger.error(f"Error deleting kiwoom credentials: {e}")
            return False

# 전역 인스턴스
parameter_store = ParameterStoreManager()
"""
AWS Parameter Store 설정 관리
"""
import boto3
import os
from typing import Dict, Optional
from botocore.exceptions import ClientError

class AWSParameterStore:
    def __init__(self):
        self.ssm = boto3.client('ssm', region_name=os.getenv('AWS_REGION', 'ap-northeast-2'))
        self.app_name = os.getenv('APP_NAME', 'showmethestock')
        self.env = os.getenv('ENVIRONMENT', 'dev')
        self.cache = {}
    
    def get_parameter(self, key: str, decrypt: bool = True) -> Optional[str]:
        """단일 파라미터 조회"""
        parameter_name = f"/{self.app_name}/{self.env}/{key}"
        
        if parameter_name in self.cache:
            return self.cache[parameter_name]
        
        try:
            response = self.ssm.get_parameter(
                Name=parameter_name,
                WithDecryption=decrypt
            )
            value = response['Parameter']['Value']
            self.cache[parameter_name] = value
            return value
        except ClientError as e:
            print(f"Parameter Store 오류 ({parameter_name}): {e}")
            return None
    
    def get_parameters_by_path(self, path: str = "") -> Dict[str, str]:
        """경로별 파라미터 일괄 조회"""
        parameter_path = f"/{self.app_name}/{self.env}/{path}"
        
        try:
            paginator = self.ssm.get_paginator('get_parameters_by_path')
            parameters = {}
            
            for page in paginator.paginate(
                Path=parameter_path,
                Recursive=True,
                WithDecryption=True
            ):
                for param in page['Parameters']:
                    # 파라미터 이름에서 경로 제거
                    key = param['Name'].replace(f"/{self.app_name}/{self.env}/", "")
                    parameters[key] = param['Value']
                    self.cache[param['Name']] = param['Value']
            
            return parameters
        except ClientError as e:
            print(f"Parameter Store 경로 조회 오류 ({parameter_path}): {e}")
            return {}
    
    def load_all_parameters(self):
        """모든 파라미터를 환경변수로 로드"""
        parameters = self.get_parameters_by_path()
        
        for key, value in parameters.items():
            # 슬래시를 언더스코어로 변환하고 대문자로 변환
            env_key = key.replace('/', '_').upper()
            os.environ[env_key] = value

# 전역 인스턴스
parameter_store = AWSParameterStore()
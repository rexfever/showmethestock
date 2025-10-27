"""
설정 로더 - 환경변수와 Parameter Store 통합
"""
import os
from aws_config import parameter_store

def load_config():
    """설정 로드 - Parameter Store 우선, 환경변수 fallback"""
    
    # AWS Parameter Store에서 설정 로드 시도
    if os.getenv('USE_PARAMETER_STORE', 'false').lower() == 'true':
        try:
            parameter_store.load_all_parameters()
            print("AWS Parameter Store에서 설정을 로드했습니다.")
        except Exception as e:
            print(f"Parameter Store 로드 실패, 환경변수 사용: {e}")
    
    # 필수 설정 검증
    required_configs = [
        'APP_KEY',
        'APP_SECRET',
        'KAKAO_ADMIN_KEY',
        'PORTONE_IMP_KEY',
        'TOSS_SECRET_KEY'
    ]
    
    missing_configs = []
    for config in required_configs:
        if not os.getenv(config):
            missing_configs.append(config)
    
    if missing_configs:
        print(f"누락된 설정: {', '.join(missing_configs)}")

def get_config(key: str, default: str = None) -> str:
    """설정값 조회 - Parameter Store 우선, 환경변수 fallback"""
    
    # Parameter Store에서 조회 시도
    if os.getenv('USE_PARAMETER_STORE', 'false').lower() == 'true':
        value = parameter_store.get_parameter(key)
        if value:
            return value
    
    # 환경변수에서 조회
    return os.getenv(key.upper(), default)

# 앱 시작 시 설정 로드
load_config()
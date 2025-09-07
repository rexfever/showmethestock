import os
import socket
from typing import Dict, Any

class EnvironmentDetector:
    """로컬 PC와 서버 환경을 구분하는 클래스"""
    
    def __init__(self):
        self._environment = None
        self._is_local = None
        self._is_server = None
    
    @property
    def environment(self) -> str:
        """환경 타입 반환: local, server, production"""
        if self._environment is None:
            self._environment = self._detect_environment()
        return self._environment
    
    @property
    def is_local(self) -> bool:
        """로컬 환경인지 확인"""
        if self._is_local is None:
            self._is_local = self.environment == "local"
        return self._is_local
    
    @property
    def is_server(self) -> bool:
        """서버 환경인지 확인"""
        if self._is_server is None:
            self._is_server = self.environment in ["server", "production"]
        return self._is_server
    
    def _detect_environment(self) -> str:
        """환경을 자동 감지"""
        
        # 1. 환경변수로 명시적 설정
        env_var = os.getenv("ENVIRONMENT", "").lower()
        if env_var in ["local", "server", "production", "development"]:
            return env_var
        
        # 2. 호스트명으로 구분
        hostname = socket.gethostname().lower()
        
        # 로컬 환경 특징
        local_indicators = [
            "macbook", "macbook-pro", "macbook-air",
            "localhost", "127.0.0.1",
            "rexsmac", "rexsmui"  # 사용자별 로컬 호스트명
        ]
        
        # 서버 환경 특징
        server_indicators = [
            "ip-", "ec2", "ubuntu", "aws",
            "stock-finder-server"
        ]
        
        for indicator in local_indicators:
            if indicator in hostname:
                return "local"
        
        for indicator in server_indicators:
            if indicator in hostname:
                return "server"
        
        # 3. 파일 경로로 구분
        if os.path.exists("/home/ubuntu/showmethestock"):
            return "server"
        elif os.path.exists("/Users/rexsmac/workspace/stock-finder"):
            return "local"
        
        # 4. IP 주소로 구분
        try:
            local_ip = self._get_local_ip()
            if local_ip.startswith("172.") or local_ip.startswith("10."):
                return "server"
            elif local_ip.startswith("192.168.") or local_ip == "127.0.0.1":
                return "local"
        except:
            pass
        
        # 기본값
        return "local"
    
    def _get_local_ip(self) -> str:
        """로컬 IP 주소 가져오기"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"
    
    def get_environment_info(self) -> Dict[str, Any]:
        """환경 정보 반환"""
        return {
            "environment": self.environment,
            "is_local": self.is_local,
            "is_server": self.is_server,
            "hostname": socket.gethostname(),
            "local_ip": self._get_local_ip(),
            "working_directory": os.getcwd(),
            "user": os.getenv("USER", "unknown"),
            "python_path": os.getenv("PYTHONPATH", ""),
        }
    
    def get_config_overrides(self) -> Dict[str, Any]:
        """환경별 설정 오버라이드"""
        if self.is_local:
            return {
                "debug": True,
                "log_level": "DEBUG",
                "universe_kospi": 10,  # 로컬에서는 적은 수로 테스트
                "universe_kosdaq": 10,
                "rate_limit_delay_ms": 100,  # 로컬에서는 빠르게
            }
        else:  # 서버
            return {
                "debug": False,
                "log_level": "INFO",
                "universe_kospi": 100,  # 서버에서는 전체
                "universe_kosdaq": 100,
                "rate_limit_delay_ms": 250,  # 서버에서는 안전하게
            }

# 전역 인스턴스
env_detector = EnvironmentDetector()

# 편의 함수들
def is_local() -> bool:
    """로컬 환경인지 확인"""
    return env_detector.is_local

def is_server() -> bool:
    """서버 환경인지 확인"""
    return env_detector.is_server

def get_environment() -> str:
    """현재 환경 반환"""
    return env_detector.environment

def get_environment_info() -> Dict[str, Any]:
    """환경 정보 반환"""
    return env_detector.get_environment_info()

def get_config_overrides() -> Dict[str, Any]:
    """환경별 설정 오버라이드 반환"""
    return env_detector.get_config_overrides()

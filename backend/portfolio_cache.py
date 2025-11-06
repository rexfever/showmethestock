import time
import json
from typing import Dict, Any, Optional

class PortfolioCache:
    """포트폴리오 데이터 캐싱 클래스"""
    
    def __init__(self, ttl: int = 300):  # 5분 TTL
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl = ttl
    
    def _get_cache_key(self, user_id: int, cache_type: str) -> str:
        """캐시 키 생성"""
        return f"{cache_type}:{user_id}"
    
    def get(self, user_id: int, cache_type: str = "portfolio") -> Optional[Any]:
        """캐시에서 데이터 조회"""
        key = self._get_cache_key(user_id, cache_type)
        
        if key not in self.cache:
            return None
        
        cache_entry = self.cache[key]
        
        # TTL 확인
        if time.time() - cache_entry['timestamp'] > self.ttl:
            del self.cache[key]
            return None
        
        return cache_entry['data']
    
    def set(self, user_id: int, data: Any, cache_type: str = "portfolio") -> None:
        """캐시에 데이터 저장"""
        key = self._get_cache_key(user_id, cache_type)
        
        self.cache[key] = {
            'data': data,
            'timestamp': time.time()
        }
    
    def invalidate(self, user_id: int, cache_type: str = "portfolio") -> None:
        """캐시 무효화"""
        key = self._get_cache_key(user_id, cache_type)
        
        if key in self.cache:
            del self.cache[key]
    
    def clear_expired(self) -> None:
        """만료된 캐시 항목 정리"""
        current_time = time.time()
        expired_keys = []
        
        for key, entry in self.cache.items():
            if current_time - entry['timestamp'] > self.ttl:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.cache[key]

# 전역 캐시 인스턴스
portfolio_cache = PortfolioCache()
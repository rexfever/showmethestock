import secrets
import hashlib
import time
from functools import wraps
from flask import request, session, jsonify

class CSRFProtection:
    def __init__(self, secret_key, token_lifetime=3600):
        self.secret_key = secret_key
        self.token_lifetime = token_lifetime
    
    def generate_token(self, user_id=None):
        """CSRF 토큰 생성"""
        timestamp = str(int(time.time()))
        random_value = secrets.token_urlsafe(32)
        user_part = str(user_id) if user_id else "anonymous"
        
        token_data = f"{timestamp}:{user_part}:{random_value}"
        signature = hashlib.sha256(f"{token_data}:{self.secret_key}".encode()).hexdigest()
        
        return f"{token_data}:{signature}"
    
    def validate_token(self, token, user_id=None):
        """CSRF 토큰 검증"""
        try:
            parts = token.split(':')
            if len(parts) != 4:
                return False
            
            timestamp, user_part, random_value, signature = parts
            
            # 시간 검증
            if int(time.time()) - int(timestamp) > self.token_lifetime:
                return False
            
            # 사용자 검증
            expected_user = str(user_id) if user_id else "anonymous"
            if user_part != expected_user:
                return False
            
            # 서명 검증
            token_data = f"{timestamp}:{user_part}:{random_value}"
            expected_signature = hashlib.sha256(f"{token_data}:{self.secret_key}".encode()).hexdigest()
            
            return secrets.compare_digest(signature, expected_signature)
        except:
            return False

def csrf_protect(csrf_protection):
    """CSRF 보호 데코레이터"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if request.method in ['POST', 'PUT', 'DELETE']:
                token = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token')
                user_id = session.get('user_id')
                
                if not token or not csrf_protection.validate_token(token, user_id):
                    return jsonify({'error': 'CSRF token validation failed'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
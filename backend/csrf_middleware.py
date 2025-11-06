from flask import request, jsonify, session
from functools import wraps
from csrf_protection import CSRFProtection
import os

# CSRF 보호 인스턴스
csrf_protection = CSRFProtection(
    secret_key=os.getenv('CSRF_SECRET', 'default-csrf-secret'),
    token_lifetime=3600
)

def csrf_middleware():
    """CSRF 미들웨어 - 모든 POST/PUT/DELETE 요청을 자동으로 보호"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # GET 요청은 통과
            if request.method == 'GET':
                return f(*args, **kwargs)
            
            # POST/PUT/DELETE 요청은 CSRF 토큰 검증
            if request.method in ['POST', 'PUT', 'DELETE']:
                token = request.headers.get('X-CSRF-Token')
                user_id = session.get('user_id')
                
                if not token or not csrf_protection.validate_token(token, user_id):
                    return jsonify({'error': 'CSRF token validation failed'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def generate_csrf_token_for_user(user_id=None):
    """사용자용 CSRF 토큰 생성"""
    return csrf_protection.generate_token(user_id)
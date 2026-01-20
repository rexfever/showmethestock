#!/usr/bin/env python3
"""
목업 서버 시작
"""

# 목업 먼저 로드
exec(open('mock_dependencies.py').read())

import sys
import os
sys.path.insert(0, 'backend')

# 필수 모듈들 목업
import types

# 추가 목업들
def create_mock_module(name, attrs=None):
    mock = types.ModuleType(name)
    if attrs:
        for key, value in attrs.items():
            setattr(mock, key, value)
    return mock

# 복잡한 모듈들 목업
sys.modules['environment'] = create_mock_module('environment', {
    'get_environment_info': lambda: {
        'environment': 'local', 'is_local': True, 'is_server': False,
        'hostname': 'localhost', 'local_ip': '127.0.0.1',
        'working_directory': '/mock', 'user': 'mock'
    }
})

sys.modules['market_analyzer'] = create_mock_module('market_analyzer', {
    'market_analyzer': type('MockAnalyzer', (), {
        'clear_cache': lambda: None,
        'analyze_market_condition': lambda x: None
    })()
})

sys.modules['models'] = create_mock_module('models', {
    'ScanResponse': dict, 'ScanItem': dict, 'IndicatorPayload': dict,
    'TrendPayload': dict, 'AnalyzeResponse': dict, 'UniverseResponse': dict,
    'UniverseItem': dict, 'ScoreFlags': dict, 'PositionResponse': dict,
    'PositionItem': dict, 'AddPositionRequest': dict, 'UpdatePositionRequest': dict,
    'PortfolioResponse': dict, 'PortfolioItem': dict, 'AddToPortfolioRequest': dict,
    'UpdatePortfolioRequest': dict, 'MaintenanceSettingsRequest': dict,
    'TradingHistory': dict, 'AddTradingRequest': dict, 'TradingHistoryResponse': dict
})

sys.modules['utils'] = create_mock_module('utils', {
    'is_code': lambda x: len(x) == 6 and x.isdigit(),
    'normalize_code_or_name': lambda x: x
})

sys.modules['kakao'] = create_mock_module('kakao', {
    'send_alert': lambda *args: {'ok': True},
    'format_scan_message': lambda *args: 'mock message',
    'format_scan_alert_message': lambda *args: {'message': 'mock alert'}
})

# 인증 관련 목업
sys.modules['auth_models'] = create_mock_module('auth_models', {
    'User': dict, 'Token': dict, 'SocialLoginRequest': dict,
    'EmailSignupRequest': dict, 'EmailLoginRequest': dict,
    'EmailVerificationRequest': dict, 'PasswordResetRequest': dict,
    'PasswordResetConfirmRequest': dict, 'PaymentRequest': dict,
    'PaymentResponse': dict, 'AdminUserUpdateRequest': dict,
    'AdminUserDeleteRequest': dict, 'AdminStatsResponse': dict,
    'PopupNoticeRequest': dict, 'UserCreate': dict, 'TokenData': dict,
    'MembershipTier': type('MockEnum', (), {'FREE': 'free', 'value': 'free'}),
    'SubscriptionStatus': type('MockEnum', (), {'ACTIVE': 'active', 'value': 'active'})
})

# 서비스 목업들
mock_auth_service = type('MockAuthService', (), {
    'init_db': lambda: None,
    'create_user': lambda x: {'id': 1, 'email': 'test@test.com', 'name': 'Test'},
    'get_user_by_id': lambda x: {'id': x, 'email': 'test@test.com'},
    'get_user_by_email': lambda x: None,
    'update_last_login': lambda x: None,
    'create_access_token': lambda *args, **kwargs: 'mock_token',
    'verify_token': lambda x: type('TokenData', (), {'user_id': 1})(),
    'authenticate_user': lambda x: {'id': 1, 'email': x}
})()

sys.modules['auth_service'] = create_mock_module('auth_service', {
    'auth_service': mock_auth_service
})

sys.modules['social_auth'] = create_mock_module('social_auth', {
    'social_auth_service': type('MockSocialAuth', (), {
        'verify_social_token': lambda *args: {'provider': 'mock'},
        'create_user_from_social': lambda x: type('UserCreate', (), x)()
    })()
})

# 기타 서비스들
for module_name in ['subscription_service', 'parameter_store', 'payment_service', 
                   'subscription_plans', 'admin_service', 'portfolio_service',
                   'new_recurrence_api', 'services.report_generator', 'email_service']:
    sys.modules[module_name] = create_mock_module(module_name, {
        'router': type('MockRouter', (), {})(),
        'get_all_plans': lambda: [],
        'get_plan': lambda x: None
    })

try:
    # FastAPI 앱 시작
    from fastapi import FastAPI
    import uvicorn
    
    # main.py에서 필요한 부분만 import
    app = FastAPI(title='Mock Stock Scanner API')
    
    @app.get('/')
    def root():
        return {'status': 'running', 'mode': 'mock'}
    
    @app.get('/scan_positions')
    def get_scan_positions():
        return {'items': [], 'count': 0, 'status': 'mock_no_duplicates'}
    
    @app.post('/auto_add_positions')
    def auto_add_positions():
        return {'ok': True, 'added_count': 0, 'status': 'mock_no_duplicates'}
    
    @app.get('/environment')
    def get_environment():
        return {'environment': 'mock', 'is_local': True}
    
    if __name__ == "__main__":
        print("🚀 목업 서버 시작 (포트 8000)")
        uvicorn.run(app, host="127.0.0.1", port=8000, log_level="error")
        
except Exception as e:
    print(f"❌ 서버 시작 실패: {e}")
    import traceback
    traceback.print_exc()
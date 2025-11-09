# API Key 보안 위험 분석 및 대응방안 - 2025.10.24

## 1. API Key 노출 시 위험도 분석

### 1.1 키움 API Key 노출 시 가능한 피해
```
🔴 매우 높은 위험
├── 계좌 잔고 조회
├── 보유 종목 조회  
├── 매수/매도 주문 실행
├── 조건부 주문 설정/취소
├── 계좌 이체 (일부 API)
└── 개인 투자 정보 유출
```

### 1.2 실제 피해 시나리오
- **무단 매매**: 악의적 매수/매도로 손실 발생
- **정보 유출**: 투자 패턴, 보유 종목 정보 노출
- **계좌 조작**: 조건부 주문 무단 설정/취소
- **자금 이동**: API 권한에 따라 계좌 이체 가능

## 2. 현재 보안 체계의 한계

### 2.1 기본 암호화만으로는 부족
```python
# 현재 방식의 한계
class UserAPIManager:
    def __init__(self):
        self.cipher = Fernet(encryption_key)  # 단순 암호화
    
    def get_user_api(self, user_id):
        # 복호화 시 메모리에 평문 노출
        app_key = self.cipher.decrypt(encrypted_key).decode()
        return app_key  # 평문으로 반환
```

### 2.2 주요 보안 취약점
- **메모리 노출**: 복호화 시 평문이 메모리에 잔존
- **로그 노출**: 디버그 로그에 API Key 기록 가능
- **네트워크 스니핑**: HTTPS 미적용 시 전송 중 노출
- **서버 해킹**: 서버 침해 시 암호화 키와 함께 노출
- **내부자 위험**: 시스템 관리자의 악의적 접근

## 3. 강화된 보안 대응방안

### 3.1 다층 보안 아키텍처
```python
class SecureAPIKeyManager:
    """다층 보안이 적용된 API Key 관리자"""
    
    def __init__(self):
        # 1단계: 하드웨어 보안 모듈 (HSM) 또는 AWS KMS
        self.kms_client = boto3.client('kms')
        self.master_key_id = os.getenv('AWS_KMS_KEY_ID')
        
        # 2단계: 사용자별 솔트 생성
        self.salt_generator = secrets.SystemRandom()
        
        # 3단계: 시간 기반 토큰
        self.token_ttl = 300  # 5분
    
    def encrypt_api_key(self, user_id: str, api_key: str) -> Dict:
        """다층 암호화로 API Key 저장"""
        
        # 1. 사용자별 고유 솔트 생성
        user_salt = self._generate_user_salt(user_id)
        
        # 2. 솔트 + API Key 결합
        salted_key = f"{user_salt}:{api_key}"
        
        # 3. AWS KMS로 암호화
        encrypted_data = self.kms_client.encrypt(
            KeyId=self.master_key_id,
            Plaintext=salted_key.encode()
        )
        
        # 4. 추가 메타데이터
        return {
            'encrypted_blob': base64.b64encode(encrypted_data['CiphertextBlob']).decode(),
            'encryption_context': {
                'user_id': user_id,
                'created_at': datetime.now().isoformat(),
                'key_version': '1.0'
            }
        }
    
    def get_temporary_token(self, user_id: str) -> str:
        """임시 토큰 발급 (5분 유효)"""
        
        # 1. 사용자 인증 확인
        if not self._verify_user_session(user_id):
            raise SecurityError("Invalid user session")
        
        # 2. API Key 복호화 (메모리에서 즉시 삭제)
        try:
            api_key = self._decrypt_api_key_secure(user_id)
            
            # 3. 임시 토큰 생성
            token_data = {
                'user_id': user_id,
                'api_key_hash': hashlib.sha256(api_key.encode()).hexdigest()[:16],
                'expires_at': (datetime.now() + timedelta(seconds=self.token_ttl)).timestamp()
            }
            
            # 4. JWT 토큰 생성
            temp_token = jwt.encode(token_data, self._get_jwt_secret(), algorithm='HS256')
            
            return temp_token
            
        finally:
            # 5. 메모리에서 API Key 완전 삭제
            if 'api_key' in locals():
                api_key = '0' * len(api_key)  # 메모리 덮어쓰기
                del api_key
    
    def _decrypt_api_key_secure(self, user_id: str) -> str:
        """보안 강화된 API Key 복호화"""
        
        # 1. 사용자별 접근 권한 확인
        if not self._check_user_permission(user_id):
            raise PermissionError("Access denied")
        
        # 2. 접근 로그 기록
        self._log_api_access(user_id, "decrypt_attempt")
        
        # 3. KMS로 복호화
        encrypted_data = self._get_encrypted_data(user_id)
        decrypted_data = self.kms_client.decrypt(
            CiphertextBlob=base64.b64decode(encrypted_data['encrypted_blob'])
        )
        
        # 4. 솔트 제거 후 API Key 추출
        salted_key = decrypted_data['Plaintext'].decode()
        salt, api_key = salted_key.split(':', 1)
        
        return api_key
```

### 3.2 Zero-Trust 아키텍처
```python
class ZeroTrustAPIProxy:
    """Zero-Trust 기반 API 프록시"""
    
    def __init__(self):
        self.session_manager = SecureSessionManager()
        self.audit_logger = AuditLogger()
        self.risk_analyzer = RiskAnalyzer()
    
    def execute_api_call(self, user_id: str, api_request: Dict) -> Dict:
        """모든 API 호출을 프록시를 통해 실행"""
        
        # 1. 사용자 세션 검증
        session = self.session_manager.validate_session(user_id)
        if not session.is_valid():
            raise SecurityError("Invalid session")
        
        # 2. 위험도 분석
        risk_score = self.risk_analyzer.analyze_request(user_id, api_request)
        if risk_score > 0.7:  # 고위험 요청
            return self._handle_high_risk_request(user_id, api_request, risk_score)
        
        # 3. 임시 토큰으로 API 호출
        temp_token = self._get_temp_token(user_id)
        
        try:
            # 4. 실제 API 호출 (토큰 사용)
            response = self._call_kiwoom_api(temp_token, api_request)
            
            # 5. 성공 로그
            self.audit_logger.log_success(user_id, api_request, response)
            
            return response
            
        except Exception as e:
            # 6. 실패 로그 및 보안 이벤트
            self.audit_logger.log_failure(user_id, api_request, str(e))
            self._trigger_security_alert(user_id, e)
            raise
        
        finally:
            # 7. 토큰 즉시 무효화
            self._revoke_temp_token(temp_token)
    
    def _handle_high_risk_request(self, user_id: str, request: Dict, risk_score: float) -> Dict:
        """고위험 요청 처리"""
        
        # 1. 추가 인증 요구
        if not self._require_additional_auth(user_id):
            raise SecurityError("Additional authentication required")
        
        # 2. 관리자 승인 요구 (매우 고위험 시)
        if risk_score > 0.9:
            approval_id = self._request_admin_approval(user_id, request)
            if not self._wait_for_approval(approval_id, timeout=300):
                raise SecurityError("Admin approval required")
        
        # 3. 제한된 권한으로 실행
        return self._execute_with_limited_permission(user_id, request)
```

### 3.3 실시간 모니터링 및 이상 탐지
```python
class SecurityMonitor:
    """실시간 보안 모니터링"""
    
    def __init__(self):
        self.anomaly_detector = AnomalyDetector()
        self.alert_manager = AlertManager()
        self.auto_response = AutoResponseSystem()
    
    def monitor_api_usage(self, user_id: str, api_call: Dict):
        """API 사용 패턴 모니터링"""
        
        # 1. 이상 패턴 탐지
        anomalies = self.anomaly_detector.detect([
            self._check_unusual_time(user_id, api_call),      # 비정상 시간대
            self._check_unusual_location(user_id, api_call),  # 비정상 위치
            self._check_unusual_volume(user_id, api_call),    # 비정상 거래량
            self._check_unusual_pattern(user_id, api_call),   # 비정상 패턴
        ])
        
        # 2. 위험도별 대응
        if anomalies.high_risk:
            self._handle_high_risk_anomaly(user_id, anomalies)
        elif anomalies.medium_risk:
            self._handle_medium_risk_anomaly(user_id, anomalies)
    
    def _handle_high_risk_anomaly(self, user_id: str, anomalies: List):
        """고위험 이상 징후 대응"""
        
        # 1. 즉시 API Key 비활성화
        self.auto_response.disable_api_key(user_id, reason="High risk anomaly detected")
        
        # 2. 긴급 알림 발송
        self.alert_manager.send_emergency_alert(
            user_id=user_id,
            message="보안 위험으로 인해 API 접근이 차단되었습니다.",
            anomalies=anomalies
        )
        
        # 3. 관리자 알림
        self.alert_manager.notify_admin(
            severity="CRITICAL",
            user_id=user_id,
            anomalies=anomalies
        )
        
        # 4. 보안 로그 기록
        self._log_security_incident(user_id, "HIGH_RISK_ANOMALY", anomalies)
```

## 4. 사용자 보안 교육 및 가이드

### 4.1 API Key 관리 가이드
```markdown
# 🔐 API Key 보안 수칙

## 필수 보안 수칙
1. **API Key 절대 공유 금지**
   - 가족, 친구에게도 절대 알려주지 마세요
   - 온라인 커뮤니티, 카톡방 등에 절대 게시 금지

2. **정기적 비밀번호 변경**
   - 키움증권 계정 비밀번호 월 1회 변경
   - 복잡한 비밀번호 사용 (영문+숫자+특수문자)

3. **안전한 환경에서만 접속**
   - 공용 PC, 카페 WiFi 사용 금지
   - 개인 기기에서만 접속

4. **이상 징후 즉시 신고**
   - 본인이 하지 않은 거래 발견 시 즉시 연락
   - 비정상적인 알림 수신 시 확인 요청
```

### 4.2 보안 체크리스트
```python
class UserSecurityChecker:
    """사용자 보안 상태 체크"""
    
    def check_user_security(self, user_id: str) -> Dict:
        """사용자 보안 상태 종합 점검"""
        
        checks = {
            'password_strength': self._check_password_strength(user_id),
            'recent_login_locations': self._check_login_locations(user_id),
            'api_usage_pattern': self._check_api_usage_pattern(user_id),
            'device_security': self._check_device_security(user_id),
            'two_factor_auth': self._check_2fa_status(user_id)
        }
        
        security_score = self._calculate_security_score(checks)
        
        return {
            'security_score': security_score,
            'checks': checks,
            'recommendations': self._get_security_recommendations(checks)
        }
```

## 5. 비상 대응 계획

### 5.1 API Key 노출 시 즉시 대응
```python
class EmergencyResponse:
    """비상 대응 시스템"""
    
    def handle_api_key_compromise(self, user_id: str, incident_type: str):
        """API Key 노출 시 비상 대응"""
        
        # 1. 즉시 차단 (1분 이내)
        self._immediate_lockdown(user_id)
        
        # 2. 피해 범위 조사 (5분 이내)
        damage_assessment = self._assess_damage(user_id)
        
        # 3. 사용자 알림 (즉시)
        self._notify_user_emergency(user_id, damage_assessment)
        
        # 4. 복구 절차 안내 (10분 이내)
        recovery_plan = self._create_recovery_plan(user_id, damage_assessment)
        
        return recovery_plan
    
    def _immediate_lockdown(self, user_id: str):
        """즉시 차단 조치"""
        
        # API Key 비활성화
        self.api_manager.disable_api_key(user_id, reason="Security incident")
        
        # 모든 활성 세션 종료
        self.session_manager.terminate_all_sessions(user_id)
        
        # 진행 중인 주문 취소
        self.trading_manager.cancel_all_pending_orders(user_id)
        
        # 조건부 주문 일시 중단
        self.conditional_manager.suspend_all_conditions(user_id)
```

### 5.2 복구 절차
```python
def api_key_recovery_process(user_id: str) -> Dict:
    """API Key 복구 절차"""
    
    recovery_steps = [
        {
            'step': 1,
            'title': '키움증권 비밀번호 변경',
            'description': '키움증권 홈페이지에서 계정 비밀번호를 즉시 변경하세요',
            'required': True
        },
        {
            'step': 2, 
            'title': '새로운 API Key 발급',
            'description': '키움증권에서 기존 API Key 폐기 후 새로운 Key 발급',
            'required': True
        },
        {
            'step': 3,
            'title': '보안 점검',
            'description': '사용 기기의 바이러스 검사 및 보안 업데이트',
            'required': True
        },
        {
            'step': 4,
            'title': '새 API Key 등록',
            'description': '시스템에 새로운 API Key 등록 및 테스트',
            'required': True
        },
        {
            'step': 5,
            'title': '거래 내역 확인',
            'description': '최근 거래 내역 확인 및 이상 거래 신고',
            'required': True
        }
    ]
    
    return {
        'recovery_id': generate_recovery_id(),
        'steps': recovery_steps,
        'estimated_time': '30-60분',
        'support_contact': '1588-1234'
    }
```

## 6. 보험 및 보상 체계

### 6.1 보안 사고 보상 정책
```python
class SecurityInsurance:
    """보안 사고 보상 시스템"""
    
    def evaluate_compensation(self, user_id: str, incident: Dict) -> Dict:
        """보상 금액 산정"""
        
        # 1. 사고 원인 분석
        cause_analysis = self._analyze_incident_cause(incident)
        
        # 2. 보상 범위 결정
        if cause_analysis['system_fault']:
            # 시스템 결함으로 인한 피해 - 100% 보상
            compensation_rate = 1.0
        elif cause_analysis['user_negligence']:
            # 사용자 과실 - 보상 제한
            compensation_rate = 0.3
        else:
            # 외부 공격 - 부분 보상
            compensation_rate = 0.7
        
        # 3. 보상 금액 계산
        max_compensation = 10_000_000  # 최대 1천만원
        actual_damage = incident['financial_loss']
        
        compensation = min(
            actual_damage * compensation_rate,
            max_compensation
        )
        
        return {
            'compensation_amount': compensation,
            'compensation_rate': compensation_rate,
            'cause': cause_analysis,
            'processing_time': '7-14 영업일'
        }
```

## 7. 최종 권장사항

### 7.1 단계별 보안 강화 계획
```
Phase 1: 기본 보안 강화 (즉시)
├── API Key 암호화 강화 (AES-256 → AWS KMS)
├── 접근 로그 강화
├── 사용자 보안 교육
└── 비상 대응 체계 구축

Phase 2: 고급 보안 시스템 (1개월)
├── Zero-Trust 아키텍처 도입
├── 실시간 이상 탐지 시스템
├── 자동 대응 시스템
└── 보안 모니터링 대시보드

Phase 3: 완전 보안 체계 (3개월)
├── 하드웨어 보안 모듈 (HSM) 도입
├── 블록체인 기반 감사 로그
├── AI 기반 위험 분석
└── 보험 연계 보상 시스템
```

### 7.2 핵심 보안 원칙
1. **최소 권한 원칙**: 필요한 최소한의 권한만 부여
2. **다층 방어**: 여러 보안 계층으로 위험 분산
3. **Zero-Trust**: 모든 접근을 의심하고 검증
4. **실시간 모니터링**: 24/7 보안 상태 감시
5. **신속한 대응**: 보안 사고 시 즉시 대응

---

**결론**: API Key 노출은 심각한 보안 위험이지만, **다층 보안 체계와 실시간 모니터링**으로 위험을 최소화할 수 있습니다. 특히 **Zero-Trust 아키텍처와 자동 대응 시스템**을 통해 안전한 자동매매 서비스를 제공할 수 있습니다.
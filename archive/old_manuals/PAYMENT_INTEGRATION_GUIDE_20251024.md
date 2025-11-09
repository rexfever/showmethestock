# 카카오페이/네이버페이 결제 연동 가이드 - 2025.10.24

## 1. 결제 연동 필요성

### 1.1 자동매매 서비스 수익화 모델
```
무료 서비스 (기본)
├── AI 스캔 결과 조회
├── 종목 분석 기본 기능
└── 가상 포트폴리오

유료 서비스 (프리미엄)
├── 자동매매 기능
├── 실시간 알림 서비스
├── 개인별 맞춤 전략
├── 고급 분석 도구
└── 우선 고객 지원
```

### 1.2 예상 요금제
| 플랜 | 월 요금 | 주요 기능 |
|------|---------|-----------|
| 기본 | 무료 | 스캔 조회, 기본 분석 |
| 스탠다드 | 29,000원 | 자동매매 (월 500만원 한도) |
| 프리미엄 | 59,000원 | 자동매매 (월 1,000만원 한도) + 알림 |
| 프로 | 99,000원 | 무제한 + 맞춤 전략 + 우선 지원 |

## 2. 카카오페이 연동

### 2.1 카카오페이 개발자 등록
```bash
# 1. 카카오 개발자 센터 접속
https://developers.kakao.com

# 2. 애플리케이션 등록
- 앱 이름: ShowMeTheStock
- 플랫폼: Web
- 도메인: sohntech.ai.kr

# 3. 카카오페이 서비스 활성화
- 제품 설정 > 카카오페이 > 활성화
- 가맹점 정보 입력
- 사업자등록증 업로드
```

### 2.2 카카오페이 API 구현
```python
import requests
import json
from datetime import datetime

class KakaoPayService:
    def __init__(self):
        self.admin_key = os.getenv('KAKAO_ADMIN_KEY')
        self.cid = os.getenv('KAKAO_CID')  # 가맹점 코드
        self.base_url = 'https://kapi.kakao.com'
    
    def create_payment(self, user_id: str, plan: str, amount: int) -> Dict:
        """카카오페이 결제 요청"""
        
        url = f"{self.base_url}/v1/payment/ready"
        
        headers = {
            'Authorization': f'KakaoAK {self.admin_key}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'cid': self.cid,
            'partner_order_id': f"ORDER_{user_id}_{int(datetime.now().timestamp())}",
            'partner_user_id': user_id,
            'item_name': f"ShowMeTheStock {plan} 플랜",
            'quantity': 1,
            'total_amount': amount,
            'tax_free_amount': 0,
            'approval_url': f'https://sohntech.ai.kr/payment/success',
            'cancel_url': f'https://sohntech.ai.kr/payment/cancel',
            'fail_url': f'https://sohntech.ai.kr/payment/fail'
        }
        
        response = requests.post(url, headers=headers, data=data)
        
        if response.status_code == 200:
            result = response.json()
            
            # 결제 정보 DB 저장
            self._save_payment_request(user_id, result['tid'], plan, amount)
            
            return {
                'success': True,
                'payment_url': result['next_redirect_pc_url'],
                'tid': result['tid']
            }
        else:
            return {
                'success': False,
                'error': response.json()
            }
    
    def approve_payment(self, tid: str, pg_token: str) -> Dict:
        """카카오페이 결제 승인"""
        
        url = f"{self.base_url}/v1/payment/approve"
        
        headers = {
            'Authorization': f'KakaoAK {self.admin_key}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        # DB에서 결제 정보 조회
        payment_info = self._get_payment_info(tid)
        
        data = {
            'cid': self.cid,
            'tid': tid,
            'partner_order_id': payment_info['order_id'],
            'partner_user_id': payment_info['user_id'],
            'pg_token': pg_token
        }
        
        response = requests.post(url, headers=headers, data=data)
        
        if response.status_code == 200:
            result = response.json()
            
            # 결제 완료 처리
            self._complete_payment(tid, result)
            
            # 사용자 플랜 업그레이드
            self._upgrade_user_plan(payment_info['user_id'], payment_info['plan'])
            
            return {
                'success': True,
                'payment_result': result
            }
        else:
            return {
                'success': False,
                'error': response.json()
            }
    
    def _save_payment_request(self, user_id: str, tid: str, plan: str, amount: int):
        """결제 요청 정보 저장"""
        conn = sqlite3.connect('payments.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO payment_requests 
            (tid, user_id, plan, amount, status, created_at)
            VALUES (?, ?, ?, ?, 'PENDING', ?)
        ''', (tid, user_id, plan, amount, datetime.now()))
        
        conn.commit()
        conn.close()
```

### 2.3 카카오페이 프론트엔드 연동
```javascript
// 결제 요청 함수
async function requestKakaoPayment(plan, amount) {
    try {
        const response = await fetch('/api/payment/kakaopay/ready', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()}`
            },
            body: JSON.stringify({
                plan: plan,
                amount: amount
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            // 카카오페이 결제 페이지로 리다이렉트
            window.location.href = result.payment_url;
        } else {
            alert('결제 요청 실패: ' + result.error);
        }
    } catch (error) {
        console.error('결제 요청 오류:', error);
        alert('결제 요청 중 오류가 발생했습니다.');
    }
}

// 결제 성공 페이지
function PaymentSuccess() {
    const [loading, setLoading] = useState(true);
    const [result, setResult] = useState(null);
    const router = useRouter();
    const { pg_token } = router.query;
    
    useEffect(() => {
        if (pg_token) {
            approvePayment(pg_token);
        }
    }, [pg_token]);
    
    const approvePayment = async (pgToken) => {
        try {
            const response = await fetch('/api/payment/kakaopay/approve', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    pg_token: pgToken
                })
            });
            
            const result = await response.json();
            setResult(result);
            setLoading(false);
            
            if (result.success) {
                // 결제 성공 시 플랜 페이지로 이동
                setTimeout(() => {
                    router.push('/subscription');
                }, 3000);
            }
        } catch (error) {
            console.error('결제 승인 오류:', error);
            setLoading(false);
        }
    };
    
    return (
        <div className="payment-result">
            {loading ? (
                <div>결제 처리 중...</div>
            ) : result?.success ? (
                <div>
                    <h2>결제가 완료되었습니다!</h2>
                    <p>플랜이 업그레이드되었습니다.</p>
                </div>
            ) : (
                <div>
                    <h2>결제 실패</h2>
                    <p>결제 처리 중 오류가 발생했습니다.</p>
                </div>
            )}
        </div>
    );
}
```

## 3. 네이버페이 연동

### 3.1 네이버페이 개발자 등록
```bash
# 1. 네이버 개발자 센터 접속
https://developers.naver.com

# 2. 애플리케이션 등록
- 애플리케이션 이름: ShowMeTheStock
- 사용 API: 네이버페이 결제
- 서비스 URL: https://sohntech.ai.kr

# 3. 네이버페이 가맹점 신청
- 사업자등록증 제출
- 서비스 심사 진행
- 가맹점 승인 후 연동 가능
```

### 3.2 네이버페이 API 구현
```python
import hashlib
import time

class NaverPayService:
    def __init__(self):
        self.client_id = os.getenv('NAVER_PAY_CLIENT_ID')
        self.client_secret = os.getenv('NAVER_PAY_CLIENT_SECRET')
        self.base_url = 'https://dev.apis.naver.com/naverpay-partner/naverpay/payments/v2.2'
    
    def create_payment(self, user_id: str, plan: str, amount: int) -> Dict:
        """네이버페이 결제 요청"""
        
        merchant_pay_key = f"ORDER_{user_id}_{int(time.time())}"
        
        # 결제 요청 데이터
        payment_data = {
            'merchantPayKey': merchant_pay_key,
            'productName': f'ShowMeTheStock {plan} 플랜',
            'totalPayAmount': amount,
            'taxScopeAmount': amount,
            'taxExScopeAmount': 0,
            'returnUrl': 'https://sohntech.ai.kr/payment/naver/success',
            'productCount': 1,
            'merchantUserKey': user_id,
            'merchantOrderKey': merchant_pay_key,
            'useCfmYmdt': self._get_expire_date()
        }
        
        # 서명 생성
        signature = self._generate_signature('POST', '/naverpay-partner/naverpay/payments/v2.2/reserve', payment_data)
        
        headers = {
            'Content-Type': 'application/json',
            'X-Naver-Client-Id': self.client_id,
            'X-Naver-Client-Secret': self.client_secret,
            'X-NaverPay-Chain-Id': 'showmethestock',
            'X-NaverPay-Signature': signature,
            'X-Timestamp': str(int(time.time() * 1000))
        }
        
        response = requests.post(f"{self.base_url}/reserve", 
                               headers=headers, 
                               json=payment_data)
        
        if response.status_code == 200:
            result = response.json()
            
            # 결제 정보 저장
            self._save_payment_request(user_id, merchant_pay_key, plan, amount)
            
            return {
                'success': True,
                'payment_url': result['body']['paymentUrl'],
                'merchant_pay_key': merchant_pay_key
            }
        else:
            return {
                'success': False,
                'error': response.json()
            }
    
    def _generate_signature(self, method: str, uri: str, data: Dict) -> str:
        """네이버페이 서명 생성"""
        timestamp = str(int(time.time() * 1000))
        
        # 서명 문자열 생성
        signature_string = f"{method} {uri}\n{self.client_id}\n{timestamp}"
        
        # HMAC-SHA256 서명
        signature = hmac.new(
            self.client_secret.encode(),
            signature_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return signature
```

## 4. 통합 결제 시스템

### 4.1 결제 서비스 통합
```python
class PaymentService:
    def __init__(self):
        self.kakaopay = KakaoPayService()
        self.naverpay = NaverPayService()
    
    def create_payment(self, user_id: str, plan: str, amount: int, method: str) -> Dict:
        """통합 결제 요청"""
        
        if method == 'kakaopay':
            return self.kakaopay.create_payment(user_id, plan, amount)
        elif method == 'naverpay':
            return self.naverpay.create_payment(user_id, plan, amount)
        else:
            return {
                'success': False,
                'error': 'Unsupported payment method'
            }
    
    def process_subscription(self, user_id: str, plan: str):
        """구독 처리"""
        
        # 사용자 플랜 업데이트
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        
        # 구독 만료일 계산 (30일)
        expire_date = datetime.now() + timedelta(days=30)
        
        cursor.execute('''
            UPDATE users 
            SET subscription_plan = ?, 
                subscription_expire = ?,
                updated_at = ?
            WHERE user_id = ?
        ''', (plan, expire_date, datetime.now(), user_id))
        
        conn.commit()
        conn.close()
        
        # 자동매매 권한 활성화
        if plan in ['standard', 'premium', 'pro']:
            self._enable_auto_trading(user_id, plan)
    
    def _enable_auto_trading(self, user_id: str, plan: str):
        """자동매매 권한 활성화"""
        
        # 플랜별 한도 설정
        limits = {
            'standard': 5_000_000,   # 500만원
            'premium': 10_000_000,   # 1000만원
            'pro': 50_000_000        # 5000만원
        }
        
        daily_limit = limits.get(plan, 0)
        
        # API Key 관리자에서 한도 업데이트
        from user_api_manager import user_api_manager
        
        user_api_manager.update_user_limits(user_id, {
            'daily_limit': daily_limit,
            'auto_trading_enabled': True,
            'plan': plan
        })
```

### 4.2 구독 관리 API
```python
# FastAPI 엔드포인트
@app.post("/api/payment/{method}/ready")
async def create_payment(method: str, request: PaymentRequest, current_user: User = Depends(get_current_user)):
    """결제 요청"""
    
    payment_service = PaymentService()
    
    result = payment_service.create_payment(
        user_id=current_user.user_id,
        plan=request.plan,
        amount=request.amount,
        method=method
    )
    
    return result

@app.post("/api/payment/{method}/approve")
async def approve_payment(method: str, request: PaymentApprovalRequest):
    """결제 승인"""
    
    payment_service = PaymentService()
    
    if method == 'kakaopay':
        result = payment_service.kakaopay.approve_payment(
            tid=request.tid,
            pg_token=request.pg_token
        )
    elif method == 'naverpay':
        result = payment_service.naverpay.approve_payment(
            merchant_pay_key=request.merchant_pay_key
        )
    
    return result

@app.get("/api/subscription/status")
async def get_subscription_status(current_user: User = Depends(get_current_user)):
    """구독 상태 조회"""
    
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT subscription_plan, subscription_expire, auto_trading_enabled
        FROM users WHERE user_id = ?
    ''', (current_user.user_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            'plan': result[0],
            'expire_date': result[1],
            'auto_trading_enabled': result[2],
            'is_active': datetime.now() < datetime.fromisoformat(result[1]) if result[1] else False
        }
    else:
        return {
            'plan': 'free',
            'expire_date': None,
            'auto_trading_enabled': False,
            'is_active': False
        }
```

## 5. 프론트엔드 구독 페이지

### 5.1 요금제 선택 페이지
```javascript
export default function Subscription() {
    const [selectedPlan, setSelectedPlan] = useState('standard');
    const [paymentMethod, setPaymentMethod] = useState('kakaopay');
    
    const plans = [
        {
            id: 'standard',
            name: '스탠다드',
            price: 29000,
            features: ['자동매매 (월 500만원)', '기본 알림', '이메일 지원']
        },
        {
            id: 'premium',
            name: '프리미엄',
            price: 59000,
            features: ['자동매매 (월 1000만원)', '실시간 알림', '우선 지원']
        },
        {
            id: 'pro',
            name: '프로',
            price: 99000,
            features: ['무제한 자동매매', '맞춤 전략', '전담 지원']
        }
    ];
    
    const handlePayment = async () => {
        const plan = plans.find(p => p.id === selectedPlan);
        
        if (paymentMethod === 'kakaopay') {
            await requestKakaoPayment(selectedPlan, plan.price);
        } else if (paymentMethod === 'naverpay') {
            await requestNaverPayment(selectedPlan, plan.price);
        }
    };
    
    return (
        <div className="subscription-page">
            <h1>요금제 선택</h1>
            
            {/* 요금제 카드들 */}
            <div className="plans-grid">
                {plans.map(plan => (
                    <div 
                        key={plan.id}
                        className={`plan-card ${selectedPlan === plan.id ? 'selected' : ''}`}
                        onClick={() => setSelectedPlan(plan.id)}
                    >
                        <h3>{plan.name}</h3>
                        <div className="price">{plan.price.toLocaleString()}원/월</div>
                        <ul>
                            {plan.features.map(feature => (
                                <li key={feature}>{feature}</li>
                            ))}
                        </ul>
                    </div>
                ))}
            </div>
            
            {/* 결제 방법 선택 */}
            <div className="payment-methods">
                <h3>결제 방법</h3>
                <div className="payment-options">
                    <label>
                        <input 
                            type="radio" 
                            value="kakaopay" 
                            checked={paymentMethod === 'kakaopay'}
                            onChange={(e) => setPaymentMethod(e.target.value)}
                        />
                        <img src="/images/kakaopay-logo.png" alt="카카오페이" />
                    </label>
                    <label>
                        <input 
                            type="radio" 
                            value="naverpay" 
                            checked={paymentMethod === 'naverpay'}
                            onChange={(e) => setPaymentMethod(e.target.value)}
                        />
                        <img src="/images/naverpay-logo.png" alt="네이버페이" />
                    </label>
                </div>
            </div>
            
            {/* 결제 버튼 */}
            <button 
                className="payment-button"
                onClick={handlePayment}
            >
                {paymentMethod === 'kakaopay' ? '카카오페이로 결제' : '네이버페이로 결제'}
            </button>
        </div>
    );
}
```

## 6. 데이터베이스 설계

### 6.1 결제 관련 테이블
```sql
-- 결제 요청 테이블
CREATE TABLE payment_requests (
    id INTEGER PRIMARY KEY,
    tid TEXT NOT NULL,              -- 결제 고유 ID
    user_id TEXT NOT NULL,
    plan TEXT NOT NULL,             -- standard/premium/pro
    amount INTEGER NOT NULL,
    payment_method TEXT NOT NULL,   -- kakaopay/naverpay
    status TEXT DEFAULT 'PENDING',  -- PENDING/COMPLETED/FAILED/CANCELLED
    created_at DATETIME NOT NULL,
    completed_at DATETIME,
    FOREIGN KEY (user_id) REFERENCES users (user_id)
);

-- 구독 정보 테이블
CREATE TABLE subscriptions (
    id INTEGER PRIMARY KEY,
    user_id TEXT NOT NULL UNIQUE,
    plan TEXT NOT NULL,
    start_date DATETIME NOT NULL,
    end_date DATETIME NOT NULL,
    auto_renewal BOOLEAN DEFAULT TRUE,
    status TEXT DEFAULT 'ACTIVE',   -- ACTIVE/EXPIRED/CANCELLED
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users (user_id)
);

-- 결제 내역 테이블
CREATE TABLE payment_history (
    id INTEGER PRIMARY KEY,
    user_id TEXT NOT NULL,
    payment_request_id INTEGER NOT NULL,
    amount INTEGER NOT NULL,
    payment_method TEXT NOT NULL,
    transaction_id TEXT,            -- 결제사 거래 ID
    paid_at DATETIME NOT NULL,
    refunded_at DATETIME,
    refund_amount INTEGER DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users (user_id),
    FOREIGN KEY (payment_request_id) REFERENCES payment_requests (id)
);
```

## 7. 구현 우선순위

### 7.1 Phase 1: 기본 결제 시스템 (2주)
- [ ] 카카오페이 API 연동
- [ ] 기본 요금제 설정 (3개 플랜)
- [ ] 결제 요청/승인 플로우
- [ ] 구독 상태 관리

### 7.2 Phase 2: 네이버페이 추가 (1주)
- [ ] 네이버페이 API 연동
- [ ] 통합 결제 시스템 구축
- [ ] 결제 방법 선택 UI

### 7.3 Phase 3: 고도화 (1주)
- [ ] 자동 갱신 시스템
- [ ] 결제 실패 처리
- [ ] 환불 시스템
- [ ] 결제 내역 관리

## 8. 예상 비용

### 8.1 결제 수수료
- **카카오페이**: 2.9% + VAT
- **네이버페이**: 2.5% + VAT

### 8.2 월 매출 예상 (1000명 기준)
```
스탠다드 (500명): 29,000원 × 500 = 14,500,000원
프리미엄 (300명): 59,000원 × 300 = 17,700,000원
프로 (200명): 99,000원 × 200 = 19,800,000원

총 매출: 52,000,000원/월
결제 수수료 (3%): 1,560,000원/월
순 매출: 50,440,000원/월
```

## 9. 결론

카카오페이/네이버페이 연동을 통해 **월 5천만원 규모의 수익화**가 가능하며, 사용자에게는 편리한 결제 경험을 제공할 수 있습니다.

**핵심 구현 포인트:**
- 간단한 API 연동으로 빠른 구현 가능
- 3단계 요금제로 다양한 사용자 니즈 충족
- 자동매매 기능과 연계한 차별화된 가치 제공
- 안정적인 결제 시스템으로 서비스 신뢰도 향상
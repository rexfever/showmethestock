# 자동매매 시스템 구현 설계서 - 2025.10.24

## 1. 프로젝트 개요

### 1.1 목표
- AI 스캔 결과를 기반으로 한 완전 자동화 매매 시스템 구현
- 키움 REST API와 조건부 주문 시스템을 활용한 안전한 자동매매
- 3단계 청산 전략을 통한 리스크 관리 및 수익 최적화

### 1.2 핵심 전략
- **매수**: AI 스캔 선별 종목 자동 매수
- **손절**: -5% 도달 시 전체 매도 (발동률 7.8%)
- **보존**: +4% 도달 시 50% 매도 (확실한 수익 확보)
- **익절**: +8% 도달 시 나머지 50% 매도 (큰 수익 확보)

## 2. 시스템 아키텍처

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   AI 스캔 엔진   │───▶│  자동매매 엔진   │───▶│  키움 조건부주문  │
│                │    │                │    │                │
│ • 15:36 실행    │    │ • 매수 주문     │    │ • 실시간 감시   │
│ • 종목 선별     │    │ • 3단계 설정    │    │ • 자동 매도     │
│ • 신호 생성     │    │ • 리스크 관리   │    │ • 체결 처리     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        ↑                       ↑                       ↑
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   데이터 관리    │    │   계좌 관리     │    │   알림 시스템    │
│                │    │                │    │                │
│ • 매매 기록     │    │ • 잔고 확인     │    │ • 매매 알림     │
│ • 성과 분석     │    │ • 포지션 관리   │    │ • 상태 알림     │
│ • 백테스팅     │    │ • 손익 계산     │    │ • 오류 알림     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 3. 핵심 컴포넌트 설계

### 3.1 자동매매 엔진
```python
class AutoTradingEngine:
    def __init__(self, account_no: str):
        self.account_no = account_no
        self.risk_manager = RiskManager()
        self.order_manager = OrderManager()
        self.three_tier_manager = ThreeTierOrderManager()
    
    def execute_daily_trading(self, scan_results: List[Dict]) -> Dict:
        """일일 자동매매 실행"""
        # 1. 리스크 체크 및 신호 필터링
        # 2. 매수 주문 실행
        # 3. 3단계 청산 전략 설정
        # 4. 결과 알림 발송
```

### 3.2 3단계 청산 전략 관리자
```python
class ThreeTierOrderManager:
    def setup_three_tier_orders(self, strategy: ThreeTierExitStrategy) -> Dict:
        """3단계 청산 주문 설정"""
        # 손절: -5% 전체 수량
        # 보존: +4% 50% 수량  
        # 익절: +8% 나머지 50% 수량
```

### 3.3 개인별 API Key 관리자 (KMS 보안)
```python
class SecureUserAPIManager:
    def __init__(self):
        # AWS KMS 클라이언트
        self.kms_client = boto3.client('kms')
        self.master_key_id = os.getenv('AWS_KMS_KEY_ID')
        self.token_cache = {}  # 5분 캐시
        self.cache_ttl = 300
    
    def register_user_api(self, user_id: str, app_key: str, app_secret: str, account_no: str) -> Dict:
        """사용자 API 키 등록 (KMS 암호화)"""
        # 1. API 키 유효성 검증
        # 2. 사용자별 솔트 생성
        # 3. AWS KMS로 암호화 저장
        # 4. 계좌 정보 확인 및 저장
    
    def get_temporary_token(self, user_id: str) -> str:
        """임시 토큰 발급 (5분 유효, 캐싱 적용)"""
        # 1. 캐시 확인 (86% KMS 호출 절약)
        # 2. 캐시 미스 시에만 KMS 복호화
        # 3. JWT 임시 토큰 생성
        # 4. 메모리에서 API Key 즉시 삭제
    
    def _decrypt_with_kms(self, user_id: str) -> str:
        """KMS를 통한 안전한 복호화"""
        # 1. 사용자 권한 확인
        # 2. 접근 로그 기록
        # 3. KMS 복호화 실행
        # 4. 솔트 제거 후 API Key 반환
```

### 3.4 리스크 관리자
```python
class RiskManager:
    def __init__(self):
        self.max_daily_investment = 10_000_000  # 일일 최대 투자금
        self.max_stock_count = 10               # 최대 보유 종목 수
        self.max_per_stock = 1_000_000         # 종목당 최대 투자금
        self.min_ai_score = 7.0                # 최소 AI 점수
```

## 4. 데이터 모델

### 4.1 매매 신호
```python
@dataclass
class TradingSignal:
    code: str              # 종목코드
    name: str              # 종목명
    score: float           # AI 점수 (7.0 이상)
    current_price: float   # 현재가
    target_quantity: int   # 목표 수량
    confidence: float      # 신뢰도
    reasons: List[str]     # 선별 이유
    created_at: datetime   # 생성 시간
```

### 4.2 3단계 청산 전략
```python
@dataclass
class ThreeTierExitStrategy:
    code: str
    name: str
    quantity: int
    entry_price: float
    stop_loss_rate: float = 5.0      # 손절 -5%
    preserve_rate: float = 4.0       # 보존 +4%
    take_profit_rate: float = 8.0    # 익절 +8%
```

### 4.3 사용자 API 정보
```python
@dataclass
class UserAPIInfo:
    user_id: str
    app_key_encrypted: str     # 암호화된 APP_KEY
    app_secret_encrypted: str  # 암호화된 APP_SECRET
    account_no: str           # 계좌번호
    account_name: str         # 계좌명
    api_status: str           # ACTIVE/INACTIVE/EXPIRED
    registered_at: datetime   # 등록일시
    last_used_at: datetime    # 마지막 사용일시
    daily_limit: float        # 개인별 일일 한도
    is_auto_trading_enabled: bool  # 자동매매 활성화 여부
```

### 4.4 매매 기록
```python
@dataclass
class TradeRecord:
    trade_id: str
    user_id: str          # 사용자 ID 추가
    code: str
    name: str
    action: str           # BUY/SELL/PRESERVE
    quantity: int
    price: float
    amount: float
    executed_at: datetime
    signal_score: float   # 매수 시 AI 점수
    exit_reason: str      # 매도 시 청산 이유 (STOP_LOSS/PRESERVE/TAKE_PROFIT)
    profit_loss: float    # 손익
```

## 5. 데이터베이스 설계

### 5.1 테이블 구조
```sql
-- 사용자 API 정보 테이블
CREATE TABLE user_api_keys (
    id INTEGER PRIMARY KEY,
    user_id TEXT NOT NULL UNIQUE,
    app_key_encrypted TEXT NOT NULL,
    app_secret_encrypted TEXT NOT NULL,
    account_no TEXT NOT NULL,
    account_name TEXT,
    api_status TEXT DEFAULT 'ACTIVE',
    registered_at DATETIME NOT NULL,
    last_used_at DATETIME,
    daily_limit REAL DEFAULT 10000000,
    is_auto_trading_enabled BOOLEAN DEFAULT FALSE,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);

-- 매매 신호 테이블
CREATE TABLE trading_signals (
    id INTEGER PRIMARY KEY,
    user_id TEXT NOT NULL,
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    score REAL NOT NULL,
    current_price REAL NOT NULL,
    target_quantity INTEGER NOT NULL,
    confidence REAL NOT NULL,
    reasons TEXT NOT NULL,
    created_at DATETIME NOT NULL,
    status TEXT DEFAULT 'PENDING',
    FOREIGN KEY (user_id) REFERENCES user_api_keys (user_id)
);

-- 3단계 청산 전략 테이블
CREATE TABLE three_tier_strategies (
    id INTEGER PRIMARY KEY,
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    entry_price REAL NOT NULL,
    entry_date DATETIME NOT NULL,
    stop_loss_price REAL NOT NULL,
    preserve_price REAL NOT NULL,
    take_profit_price REAL NOT NULL,
    status TEXT DEFAULT 'ACTIVE',
    created_at DATETIME NOT NULL
);

-- 조건부 주문 테이블
CREATE TABLE conditional_orders (
    id INTEGER PRIMARY KEY,
    strategy_id INTEGER NOT NULL,
    order_no TEXT NOT NULL,
    order_type TEXT NOT NULL,  -- STOP_LOSS/PRESERVE/TAKE_PROFIT
    trigger_price REAL NOT NULL,
    quantity INTEGER NOT NULL,
    status TEXT DEFAULT 'ACTIVE',
    created_at DATETIME NOT NULL,
    executed_at DATETIME,
    FOREIGN KEY (strategy_id) REFERENCES three_tier_strategies (id)
);

-- 매매 기록 테이블
CREATE TABLE trade_records (
    id INTEGER PRIMARY KEY,
    trade_id TEXT UNIQUE NOT NULL,
    user_id TEXT NOT NULL,
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    action TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    price REAL NOT NULL,
    amount REAL NOT NULL,
    executed_at DATETIME NOT NULL,
    signal_score REAL,
    exit_reason TEXT,
    profit_loss REAL,
    strategy_id INTEGER,
    FOREIGN KEY (user_id) REFERENCES user_api_keys (user_id),
    FOREIGN KEY (strategy_id) REFERENCES three_tier_strategies (id)
);
```

## 6. API 설계

### 6.1 사용자 API Key 등록 API
```python
POST /api/user/register-api
{
    "app_key": "KIWOOM_APP_KEY",
    "app_secret": "KIWOOM_APP_SECRET", 
    "account_no": "12345678901",
    "daily_limit": 5000000
}

Response:
{
    "success": true,
    "message": "API 키 등록 완료",
    "account_info": {
        "account_no": "12345678901",
        "account_name": "홍길동",
        "balance": 10000000
    }
}
```

### 6.2 API Key 상태 확인 API
```python
GET /api/user/api-status

Response:
{
    "api_status": "ACTIVE",
    "account_no": "12345678901",
    "account_name": "홍길동",
    "daily_limit": 5000000,
    "is_auto_trading_enabled": true,
    "last_used_at": "2025-10-24T15:36:00Z"
}
```

### 6.3 자동매매 실행 API
```python
POST /api/auto-trading/execute
{
    "scan_results": [
        {
            "code": "005930",
            "name": "삼성전자",
            "score": 8.5,
            "current_price": 70000,
            "reasons": ["상승시작", "거래량증가"]
        }
    ],
    "config": {
        "max_investment": 10000000,
        "max_stocks": 10,
        "max_per_stock": 1000000
    }
}

Response:
{
    "success": true,
    "executed_orders": 5,
    "total_investment": 5000000,
    "strategies_created": 5,
    "message": "자동매매 실행 완료"
}
```

### 6.4 3단계 전략 현황 API
```python
GET /api/auto-trading/three-tier-strategies

Response:
{
    "active_strategies": [
        {
            "code": "005930",
            "name": "삼성전자",
            "entry_price": 70000,
            "current_price": 72800,
            "profit_rate": 4.0,
            "status": "PRESERVE_TRIGGERED",
            "orders": [
                {"type": "STOP_LOSS", "price": 66500, "status": "ACTIVE"},
                {"type": "PRESERVE", "price": 72800, "status": "EXECUTED"},
                {"type": "TAKE_PROFIT", "price": 75600, "status": "ACTIVE"}
            ]
        }
    ]
}
```

## 7. 운영 시나리오

### 7.1 사용자 API Key 등록 플로우
```
1. 사용자 로그인 및 권한 확인
2. 키움증권 API Key 발급 안내
   • 키움증권 홈페이지 접속
   • Open API 신청
   • APP_KEY, APP_SECRET 발급
3. API Key 등록 페이지 접속
4. API Key 입력 및 유효성 검증
   • 키움 API 연결 테스트
   • 계좌 정보 확인
   • 잔고 조회 테스트
5. 암호화 저장 및 등록 완료
6. 자동매매 설정 활성화
```

### 7.2 일일 자동매매 플로우
```
15:36 - AI 스캔 실행 완료
15:40 - 사용자별 매매 신호 생성
        • 등록된 API Key 사용자만 대상
        • AI 점수 7.0 이상 필터링
        • 개인별 리스크 한도 체크
        • 사용자별 매수 대상 확정
15:45 - 사용자별 매수 주문 실행
        • 개인 API Key로 주문
        • 개인별 투자 한도 적용
        • 계좌별 독립 실행
16:00 - 매수 주문 완료 및 대기

09:05 - 매수 체결 확인
09:10 - 3단계 청산 전략 설정
        • 손절 주문: -5% (전체 수량)
        • 보존 주문: +4% (50% 수량)
        • 익절 주문: +8% (50% 수량)
09:15 - 설정 완료 알림 발송
```

### 7.3 3단계 청산 시나리오
```
시나리오 1: 손절 발동 (-5%)
→ 전체 수량 시장가 매도
→ 모든 조건부 주문 자동 취소
→ 손실 확정 및 알림

시나리오 2: 보존 발동 (+4%)
→ 50% 수량 시장가 매도 (확실한 수익)
→ 손절 주문 수량 조정 (50%로 감소)
→ 익절 주문 유지 (나머지 50%)

시나리오 3: 익절 발동 (+8%)
→ 나머지 50% 수량 시장가 매도
→ 모든 조건부 주문 완료
→ 최대 수익 확정 및 알림
```

## 8. 구현 우선순위

### Phase 1: 보안 강화 API Key 관리 시스템 (1주)
- [ ] AWS KMS 설정 및 마스터 키 생성
- [ ] KMS 기반 API Key 암호화/복호화 시스템
- [ ] 임시 토큰 생성 및 캐싱 시스템
- [ ] 사용자 API Key 등록 페이지 (보안 강화)
- [ ] 키움 API 연결 테스트 및 계좌 정보 확인
- [ ] 실시간 보안 모니터링 기초 구축

### Phase 2: 기본 자동매매 (2주)
- [ ] 사용자별 매매 신호 생성 로직
- [ ] 개인 API Key 기반 주문 시스템
- [ ] 사용자별 리스크 관리 구현
- [ ] 개인별 매매 기록 저장

### Phase 3: 3단계 청산 전략 (2주)
- [ ] 키움 조건부 주문 API 연동
- [ ] 3단계 청산 주문 설정 구현
- [ ] 조건부 주문 상태 모니터링
- [ ] 청산 결과 처리 및 기록

### Phase 4: 모니터링 및 알림 (1주)
- [ ] 실시간 상태 모니터링 대시보드
- [ ] 매매 결과 알림 시스템
- [ ] 성과 분석 리포트 생성
- [ ] 오류 처리 및 로깅

### Phase 5: 최적화 및 고도화 (2주)
- [ ] 백테스팅 시스템 구현
- [ ] 전략 성과 분석 및 개선
- [ ] 다중 계좌 지원
- [ ] 고급 리스크 관리 기능

## 9. 기술 스택

### 9.1 백엔드
- **언어**: Python 3.9+
- **프레임워크**: FastAPI
- **데이터베이스**: SQLite (개발), PostgreSQL (운영)
- **외부 API**: 키움 REST API
- **스케줄링**: APScheduler

### 9.2 프론트엔드
- **프레임워크**: Next.js 13
- **UI 라이브러리**: Tailwind CSS
- **차트**: Chart.js
- **상태 관리**: React Context

### 9.3 인프라 및 보안
- **서버**: AWS EC2
- **데이터베이스**: AWS RDS (PostgreSQL)
- **암호화**: AWS KMS (FIPS 140-2 Level 3)
- **모니터링**: CloudWatch + 보안 이벤트 실시간 감시
- **알림**: AWS SNS + 카카오톡 알림톡 + 보안 긴급 알림
- **비용**: 월 338원~11,475원 (사용자 규모별 KMS 비용)

## 10. 보안 및 안전장치

### 10.1 다층 보안 체계
- **AWS KMS 암호화**: 하드웨어 수준 보안 (FIPS 140-2 Level 3)
- **Zero-Trust 아키텍처**: 모든 API 호출 프록시를 통해 실행
- **임시 토큰 시스템**: 5분 유효 JWT 토큰으로 API Key 노출 최소화
- **실시간 모니터링**: 이상 패턴 자동 탐지 및 차단
- **토큰 캐싱**: 86% KMS 호출 절약으로 비용 최적화
- **사용자별 완전 분리**: 개인 API Key로 독립적 거래 실행

### 10.2 리스크 관리 및 보안 모니터링
- **투자 한도**: 일일 1,000만원, 종목당 100만원, 최대 10종목
- **AI 점수 기준**: 최소 7.0점 이상
- **실시간 이상 탐지**: 비정상 시간대/위치/패턴 자동 차단
- **자동 대응 시스템**: 고위험 탐지 시 즉시 API Key 비활성화
- **비상 복구 절차**: API Key 노출 시 1분 내 차단, 복구 가이드 제공

### 10.3 보안 사고 대응 및 보상
- **즉시 대응**: API Key 노출 시 1분 내 자동 차단
- **피해 조사**: 5분 내 거래 내역 분석 및 피해 범위 산정
- **복구 절차**: 키움 비밀번호 변경 → 새 API Key 발급 → 재등록
- **보상 체계**: 시스템 결함 100%, 외부 공격 70%, 사용자 과실 30% 보상
- **최대 보상**: 1,000만원 (보험 연계)

### 10.4 모니터링
- 실시간 거래 상태 모니터링
- 성과 지표 추적 및 알림
- 시스템 오류 자동 감지
- 정기 백업 및 복구 시스템

## 11. 성과 지표 및 보안 ROI

### 11.1 수익성 지표
- **목표 월 수익률**: 5-10%
- **승률**: 80% 이상 (현재 데이터 기준 79.9%)
- **평균 보유 기간**: 3-7일
- **리스크/리워드 비율**: 1:2 이상

### 11.2 보안 비용 및 ROI
- **KMS 월 비용**: 338원~11,475원 (사용자 규모별)
- **사용자당 비용**: 월 1~3원 수준
- **보안 사고 예방 가치**: 5,000만원~50억원
- **보안 ROI**: 20,000%~58,824% (극히 높은 효율성)

### 11.3 운영 지표
- **시스템 가동률**: 99% 이상
- **주문 체결률**: 95% 이상
- **오류 발생률**: 1% 이하
- **응답 시간**: 평균 2초 이하

### 11.4 보안 지표
- **API Key 노출 대응 시간**: 1분 내 자동 차단
- **이상 탐지 정확도**: 95% 이상
- **보안 사고 발생률**: 0.1% 이하 목표
- **KMS 사용률 최적화**: 86% 비용 절약 (캐싱 적용)

## 12. 테스트 계획

### 12.1 단위 테스트
- 매매 신호 생성 로직
- 리스크 관리 규칙
- 3단계 청산 전략 계산
- API 연동 기능
- **보안 테스트**: KMS 암호화/복호화, 토큰 생성/검증

### 12.2 통합 테스트
- 전체 매매 플로우
- 키움 API 연동 (사용자별 API Key)
- 데이터베이스 연동
- 알림 시스템
- **보안 통합 테스트**: Zero-Trust 아키텍처, 이상 탐지 시스템

### 12.3 실전 테스트
- 모의투자 환경 테스트
- 소액 실전 테스트 (100만원)
- 점진적 투자 규모 확대
- 성과 검증 및 최적화
- **보안 침투 테스트**: API Key 노출 시나리오, 비상 대응 테스트

## 13. 배포 및 운영

### 13.1 배포 전략
- Blue-Green 배포 방식
- 단계적 배포 (모의→소액→전체)
- 롤백 계획 수립
- 모니터링 강화

### 13.2 운영 관리
- 일일 성과 리포트 생성
- 주간 전략 검토 및 조정
- 월간 백테스팅 및 최적화
- 분기별 전략 업데이트

## 14. KMS 보안 체계 도입 가치

### 14.1 보안 강화 효과
- **하드웨어 수준 암호화**: FIPS 140-2 Level 3 인증
- **Zero-Trust 아키텍처**: 모든 접근을 의심하고 검증
- **실시간 위협 대응**: 1분 내 자돔 차단 체계
- **금융권 수준 보안**: 은행/증권사 동등 보안 수준

### 14.2 비용 효율성
```
사용자 규모별 KMS 비용 (월간)
├── 100명: 338원 (사용자당 3.4원)
├── 1,000명: 1,620원 (사용자당 1.6원)
└── 10,000명: 11,475원 (사용자당 1.1원)

보안 사고 예방 가치 vs 비용
├── 예방 가치: 5,000만원~50억원
├── KMS 비용: 월 338원~11,475원
└── ROI: 20,000%~58,824%
```

### 14.3 전략적 가치
- **사용자 신뢰도 증대**: 최고 수준 보안으로 서비스 신뢰성 향상
- **규제 대응**: 금융권 보안 규제 완전 준수
- **사업 지속성**: 보안 사고로 인한 서비스 중단 위험 최소화
- **경쟁 우위**: 업계 최고 수준의 보안 체계로 차별화

### 14.4 최종 결론
**AWS KMS 기반 보안 체계는 극히 저렴한 비용으로 최고 수준의 보안을 제공하며, 자동매매 서비스의 신뢰성과 지속가능성을 보장하는 필수 투자입니다.**

---

**작성일**: 2025년 10월 24일  
**작성자**: AI 자동매매 시스템 개발팀  
**버전**: v1.1 (KMS 보안 체계 반영)  
**승인**: 대기 중
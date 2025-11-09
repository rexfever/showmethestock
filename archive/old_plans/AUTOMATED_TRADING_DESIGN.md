# 자동매매 시스템 설계

## 1. 시스템 아키텍처

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   AI 스캔 엔진   │───▶│  자동매매 엔진   │───▶│  키움 조건부주문  │
│                │    │                │    │                │
│ • 종목 선별     │    │ • 매수 실행     │    │ • 실시간 감시   │
│ • 신호 생성     │    │ • 조건 설정     │    │ • 자동 매도     │
│ • 점수 계산     │    │ • 리스크 관리   │    │ • 체결 처리     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        ↑                       ↑                       ↑
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   데이터 수집    │    │   계좌 관리     │    │   알림 시스템    │
│                │    │                │    │                │
│ • 시세 데이터   │    │ • 잔고 확인     │    │ • 매매 알림     │
│ • 기술지표     │    │ • 포지션 관리   │    │ • 상태 알림     │
│ • 거래량 분석   │    │ • 손익 계산     │    │ • 오류 알림     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 2. 핵심 컴포넌트

### 2.1 AI 스캔 엔진 (기존)
- **역할**: 상승 초입 종목 발굴
- **입력**: 전체 상장 종목 데이터
- **출력**: 선별된 종목 리스트 + 점수
- **주기**: 매일 15:36 (장 마감 후)

### 2.2 자동매매 엔진 (신규)
```python
class AutoTradingEngine:
    def __init__(self, account_no: str):
        self.account_no = account_no
        self.risk_manager = RiskManager()
        self.order_manager = OrderManager()
        self.conditional_manager = ConditionalOrderManager()
    
    def execute_daily_trading(self, scan_results: List[Dict]) -> Dict:
        """일일 자동매매 실행"""
        # 1. 리스크 체크
        # 2. 매수 주문 실행
        # 3. 조건부 주문 설정
        # 4. 결과 알림
```

### 2.3 리스크 관리자
```python
class RiskManager:
    def __init__(self):
        self.max_daily_investment = 10_000_000  # 일일 최대 투자금
        self.max_stock_count = 10               # 최대 보유 종목 수
        self.max_per_stock = 1_000_000         # 종목당 최대 투자금
    
    def check_investment_limit(self, signals: List[TradingSignal]) -> List[TradingSignal]:
        """투자 한도 체크 및 필터링"""
```

### 2.4 조건부 주문 관리자
```python
class ConditionalOrderManager:
    def setup_exit_strategy(self, position: Position) -> Dict:
        """청산 전략 설정"""
        # 손절: -5%
        # 익절: +7% 
        # 트레일링: 3%
        # 시간: 5일
```

## 3. 데이터 모델

### 3.1 매매 신호
```python
@dataclass
class TradingSignal:
    code: str              # 종목코드
    name: str              # 종목명
    score: float           # AI 점수
    current_price: float   # 현재가
    target_quantity: int   # 목표 수량
    confidence: float      # 신뢰도
    reasons: List[str]     # 선별 이유
    created_at: datetime   # 생성 시간
```

### 3.2 포지션
```python
@dataclass
class Position:
    code: str
    name: str
    quantity: int
    entry_price: float
    entry_date: datetime
    current_price: float
    profit_loss: float
    profit_rate: float
    conditional_orders: List[str]  # 설정된 조건부 주문 번호들
```

### 3.3 매매 기록
```python
@dataclass
class TradeRecord:
    trade_id: str
    code: str
    name: str
    action: str           # BUY/SELL
    quantity: int
    price: float
    amount: float
    fee: float
    executed_at: datetime
    signal_score: float   # 매수 시 AI 점수
    exit_reason: str      # 매도 시 청산 이유
```

## 4. 매매 전략

### 4.1 매수 전략
```python
class BuyStrategy:
    def __init__(self):
        self.min_score = 7.0           # 최소 AI 점수
        self.max_investment_per_stock = 1_000_000  # 종목당 최대 투자금
        self.min_price = 1000          # 최소 주가
        self.max_price = 100000        # 최대 주가
    
    def filter_signals(self, signals: List[TradingSignal]) -> List[TradingSignal]:
        """매수 신호 필터링"""
        return [s for s in signals if 
                s.score >= self.min_score and
                self.min_price <= s.current_price <= self.max_price]
    
    def calculate_quantity(self, signal: TradingSignal) -> int:
        """매수 수량 계산"""
        return min(
            self.max_investment_per_stock // int(signal.current_price),
            1000  # 최대 1000주
        )
```

### 4.2 매도 전략 (조건부 주문)
```python
class SellStrategy:
    def __init__(self):
        self.profit_target = 8.0    # 익절 목표 (%) - 큰 수익 확보
        self.stop_loss = 5.0        # 손절 기준 (%) - 관대하지만 안전 (7.8% 발동)
        self.preserve_profit = 4.0  # 수익 보존 (%) - 확실한 수익 확보
        self.trailing_rate = 3.0    # 트레일링 비율 (%) - 보조 전략
        self.max_hold_days = 5      # 최대 보유 일수
    
    def create_conditional_orders(self, position: Position) -> List[ConditionalOrder]:
        """조건부 주문 생성"""
        orders = []
        
        # 손절 주문
        stop_price = position.entry_price * (1 - self.stop_loss / 100)
        orders.append(ConditionalOrder(
            type="STOP_LOSS",
            trigger_price=stop_price,
            quantity=position.quantity
        ))
        
        # 익절 주문
        profit_price = position.entry_price * (1 + self.profit_target / 100)
        orders.append(ConditionalOrder(
            type="TAKE_PROFIT", 
            trigger_price=profit_price,
            quantity=position.quantity
        ))
        
        # 트레일링 스탑
        orders.append(ConditionalOrder(
            type="TRAILING_STOP",
            trail_rate=self.trailing_rate,
            quantity=position.quantity
        ))
        
        return orders
```

## 5. 운영 시나리오

### 5.1 일일 자동매매 플로우
```
15:36 - AI 스캔 실행
15:40 - 스캔 결과 분석 및 매매 신호 생성
15:45 - 리스크 체크 및 매수 대상 확정
16:00 - 매수 주문 실행 (다음날 시초가)
09:05 - 매수 체결 확인
09:10 - 조건부 주문 설정 (손절/익절/트레일링)
09:15 - 설정 완료 알림 발송
```

### 5.2 실시간 모니터링 (키움 시스템)
```
장중 - 키움에서 실시간 가격 감시
조건 달성 시 - 자동 매도 주문 실행
체결 시 - 포지션 정리 및 알림 발송
```

## 6. 데이터베이스 설계

### 6.1 테이블 구조
```sql
-- 매매 신호 테이블
CREATE TABLE trading_signals (
    id INTEGER PRIMARY KEY,
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    score REAL NOT NULL,
    current_price REAL NOT NULL,
    target_quantity INTEGER NOT NULL,
    confidence REAL NOT NULL,
    reasons TEXT NOT NULL,
    created_at DATETIME NOT NULL,
    status TEXT DEFAULT 'PENDING'  -- PENDING/EXECUTED/CANCELLED
);

-- 포지션 테이블
CREATE TABLE positions (
    id INTEGER PRIMARY KEY,
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    entry_price REAL NOT NULL,
    entry_date DATETIME NOT NULL,
    current_price REAL,
    profit_loss REAL,
    profit_rate REAL,
    status TEXT DEFAULT 'ACTIVE',  -- ACTIVE/CLOSED
    updated_at DATETIME NOT NULL
);

-- 조건부 주문 테이블
CREATE TABLE conditional_orders (
    id INTEGER PRIMARY KEY,
    position_id INTEGER NOT NULL,
    order_no TEXT NOT NULL,  -- 키움 주문번호
    order_type TEXT NOT NULL,  -- STOP_LOSS/TAKE_PROFIT/TRAILING_STOP
    trigger_price REAL,
    trail_rate REAL,
    status TEXT DEFAULT 'ACTIVE',  -- ACTIVE/EXECUTED/CANCELLED
    created_at DATETIME NOT NULL,
    FOREIGN KEY (position_id) REFERENCES positions (id)
);

-- 매매 기록 테이블
CREATE TABLE trade_records (
    id INTEGER PRIMARY KEY,
    trade_id TEXT UNIQUE NOT NULL,
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    action TEXT NOT NULL,  -- BUY/SELL
    quantity INTEGER NOT NULL,
    price REAL NOT NULL,
    amount REAL NOT NULL,
    fee REAL NOT NULL,
    executed_at DATETIME NOT NULL,
    signal_score REAL,
    exit_reason TEXT,
    profit_loss REAL
);
```

## 7. API 설계

### 7.1 자동매매 API
```python
# 자동매매 실행
POST /api/auto-trading/execute
{
    "scan_results": [...],
    "strategy_config": {
        "max_investment": 10000000,
        "max_stocks": 10,
        "profit_target": 7.0,
        "stop_loss": 5.0
    }
}

# 포지션 조회
GET /api/auto-trading/positions

# 매매 기록 조회
GET /api/auto-trading/trades?start_date=2025-01-01&end_date=2025-01-31

# 조건부 주문 현황
GET /api/auto-trading/conditional-orders

# 수익률 통계
GET /api/auto-trading/performance
```

### 7.2 설정 관리 API
```python
# 매매 설정 조회/수정
GET/PUT /api/auto-trading/config

# 리스크 설정
PUT /api/auto-trading/risk-config
{
    "max_daily_investment": 10000000,
    "max_stock_count": 10,
    "max_per_stock": 1000000
}
```

## 8. 보안 및 안전장치

### 8.1 접근 제어
- 관리자만 자동매매 설정 가능
- API 키 암호화 저장
- 거래 내역 로그 보관

### 8.2 안전장치
- 일일 투자 한도 제한
- 종목당 투자 한도 제한
- 비정상 거래 감지 및 중단
- 긴급 중단 기능

### 8.3 모니터링
- 실시간 알림 시스템
- 거래 성과 추적
- 오류 로그 수집
- 시스템 상태 모니터링

## 9. 구현 우선순위

### Phase 1: 기본 자동매매
- [ ] 매매 신호 생성 로직
- [ ] 키움 API 매수 주문 연동
- [ ] 기본 리스크 관리
- [ ] 매매 기록 저장

### Phase 2: 조건부 주문 연동
- [ ] 키움 조건부 주문 API 연동
- [ ] 손절/익절 자동 설정
- [ ] 포지션 관리 시스템
- [ ] 알림 시스템

### Phase 3: 고도화
- [ ] 트레일링 스탑 구현
- [ ] 성과 분석 대시보드
- [ ] 전략 백테스팅
- [ ] 다중 계좌 지원

### Phase 4: 최적화
- [ ] AI 모델 개선
- [ ] 동적 리스크 조정
- [ ] 시장 상황별 전략 변경
- [ ] 고급 알림 기능
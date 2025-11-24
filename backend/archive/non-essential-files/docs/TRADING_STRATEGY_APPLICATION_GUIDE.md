# 매매 전략 적용 가이드

## 현재 상태

### 1. 검증 전략 (`validate_trading_strategy.py`)
- **용도**: 과거 데이터로 전략 검증만 수행
- **적용 위치**: 실제 매매에 사용되지 않음
- **현재 사용**: 검증 및 분석 목적

### 2. 자동감시매매 서비스 (`auto_monitoring_service.py`)
- **용도**: 실제 자동매매 시 사용
- **적용 위치**: 
  - `create_monitoring_rules_from_signals()` 함수 (line 279-303)
  - `create_rules_from_positions()` 메서드 (line 253-275)
  
### 현재 하드코딩된 값

```python
# auto_monitoring_service.py line 291-294
profit_target=7.0,   # 7% 익절
stop_loss=5.0,       # 5% 손절
max_hold_days=5,     # 최대 5일 보유
```

**문제점:**
- 검증된 전략과 불일치
- 보존(preserve) 로직 없음
- 최소 보유일 로직 없음
- 환경변수/설정으로 관리되지 않음

## 검증된 최적 전략

### 전략 파라미터
- **손절**: -7%
- **익절**: +3%
- **보존**: +1.5%
- **최소 보유**: 5일
- **최대 보유**: 45일

### 성과
- 승률: 62.5%
- 익절률: 41.4%
- 손절률: 17.2%
- 평균 수익률: +0.70%
- 손익비: 0.71:1

## 적용 방법

### 방법 1: config.py에 추가 (권장)

#### 1단계: config.py에 전략 파라미터 추가

```python
# backend/config.py에 추가
@dataclass
class Config:
    # ... 기존 설정 ...
    
    # === 매매 전략 설정 ===
    trading_stop_loss: float = float(os.getenv("TRADING_STOP_LOSS", "-7.0"))  # 손절 (%)
    trading_take_profit: float = float(os.getenv("TRADING_TAKE_PROFIT", "3.0"))  # 익절 (%)
    trading_preserve: float = float(os.getenv("TRADING_PRESERVE", "1.5"))  # 보존 (%)
    trading_min_hold_days: int = int(os.getenv("TRADING_MIN_HOLD_DAYS", "5"))  # 최소 보유일
    trading_max_hold_days: int = int(os.getenv("TRADING_MAX_HOLD_DAYS", "45"))  # 최대 보유일
```

#### 2단계: auto_monitoring_service.py 수정

**변경 1: MonitoringRule에 보존 및 최소 보유일 추가**
```python
@dataclass
class MonitoringRule:
    code: str
    name: str
    profit_target: float  # 익절 목표 (%)
    stop_loss: float      # 손절 기준 (%)
    preserve_rate: float  # 보존 기준 (%) ⬅️ 추가
    trailing_stop: bool
    min_hold_days: int    # 최소 보유 일수 ⬅️ 추가
    max_hold_days: int    # 최대 보유 일수
    entry_date: datetime
    entry_price: float
    highest_price: float
    preserve_triggered: bool = False  # 보존 조건 달성 여부 ⬅️ 추가
```

**변경 2: create_monitoring_rules_from_signals() 수정**
```python
from config import config

def create_monitoring_rules_from_signals(monitoring_service: AutoMonitoringService, 
                                       executed_orders: List[Dict]) -> int:
    """매수 완료된 주문들에 대해 감시 규칙 생성"""
    created_count = 0
    
    for order in executed_orders:
        if "signal" in order:
            signal = order["signal"]
            
            rule = MonitoringRule(
                code=signal.code,
                name=signal.name,
                profit_target=config.trading_take_profit,      # 3.0% ⬅️ config에서
                stop_loss=abs(config.trading_stop_loss),       # 7.0% ⬅️ config에서
                preserve_rate=config.trading_preserve,         # 1.5% ⬅️ 추가
                trailing_stop=True,
                min_hold_days=config.trading_min_hold_days,    # 5일 ⬅️ 추가
                max_hold_days=config.trading_max_hold_days,    # 45일 ⬅️ config에서
                entry_date=datetime.now(),
                entry_price=signal.target_price,
                highest_price=signal.target_price,
                preserve_triggered=False
            )
            
            monitoring_service.add_monitoring_rule(rule)
            created_count += 1
    
    return created_count
```

**변경 3: _check_sell_signals() 수정 (보존 로직 추가)**
```python
def _check_sell_signals(self, rule: MonitoringRule, current_price: float, 
                       profit_rate: float, current_time: datetime) -> Optional[str]:
    """매도 신호 체크"""
    
    hold_days = (current_time - rule.entry_date).days
    
    # 최소 보유일 체크
    can_stop_loss = hold_days >= rule.min_hold_days
    
    # 보존 조건 체크
    if not rule.preserve_triggered and profit_rate >= rule.preserve_rate:
        rule.preserve_triggered = True
    
    # 1. 익절 체크
    if profit_rate >= rule.profit_target:
        return f"익절 달성 ({profit_rate:.2f}%)"
    
    # 2. 손절 체크 (최소 보유일 이후)
    if can_stop_loss:
        if rule.preserve_triggered:
            # 보존 후에는 원가 이하로 하락 시 손절
            if profit_rate < 0:
                return f"보존 후 손절 ({profit_rate:.2f}%)"
        else:
            # 보존 전에는 일반 손절
            if profit_rate <= -abs(rule.stop_loss):
                return f"손절 실행 ({profit_rate:.2f}%)"
    
    # 3. 트레일링 스탑 체크 (보존 후)
    if rule.trailing_stop and rule.preserve_triggered:
        trailing_loss = ((current_price - rule.highest_price) / rule.highest_price) * 100
        if trailing_loss <= -2.0:  # 최고점 대비 2% 하락 시
            return f"트레일링 스탑 ({trailing_loss:.2f}%)"
    
    # 4. 시간 기반 매도 체크
    if hold_days >= rule.max_hold_days:
        return f"보유기간 만료 ({hold_days}일)"
    
    return None
```

### 방법 2: 환경변수로 직접 설정

`.env` 파일에 추가:
```bash
TRADING_STOP_LOSS=-7.0
TRADING_TAKE_PROFIT=3.0
TRADING_PRESERVE=1.5
TRADING_MIN_HOLD_DAYS=5
TRADING_MAX_HOLD_DAYS=45
```

## 적용 위치 요약

| 항목 | 파일 | 함수/위치 | 현재 값 | 변경 후 값 |
|------|------|----------|---------|-----------|
| **익절** | `auto_monitoring_service.py` | `create_monitoring_rules_from_signals()` line 291 | 7.0% | 3.0% |
| **손절** | `auto_monitoring_service.py` | `create_monitoring_rules_from_signals()` line 292 | 5.0% | 7.0% |
| **최대 보유일** | `auto_monitoring_service.py` | `create_monitoring_rules_from_signals()` line 294 | 5일 | 45일 |
| **보존** | `auto_monitoring_service.py` | 없음 | - | 1.5% 추가 필요 |
| **최소 보유일** | `auto_monitoring_service.py` | 없음 | - | 5일 추가 필요 |

## 적용 순서

1. ✅ `config.py`에 전략 파라미터 추가
2. ✅ `MonitoringRule`에 보존 및 최소 보유일 필드 추가
3. ✅ `create_monitoring_rules_from_signals()` 수정
4. ✅ `_check_sell_signals()`에 보존 로직 추가
5. ✅ `create_rules_from_positions()` 수정 (기본값 변경)

## 참고사항

- `validate_trading_strategy.py`는 검증용이므로 수정 불필요
- 실제 자동매매는 `auto_monitoring_service.py`에서 동작
- 보존 로직은 익절/손절 체크보다 먼저 확인 필요
- 최소 보유일은 손절 체크 시에만 적용


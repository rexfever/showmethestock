"""
자동감시매매 서비스
보유 종목을 실시간 모니터링하여 자동으로 매도 신호 감지 및 실행
"""

import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import threading

from kiwoom_api import api
from auto_trading_service import AutoTradingService, TradingSignal, Position


@dataclass
class MonitoringRule:
    """감시 규칙"""
    code: str
    name: str
    profit_target: float  # 익절 목표 (%)
    stop_loss: float      # 손절 기준 (%)
    trailing_stop: bool   # 트레일링 스탑 사용 여부
    max_hold_days: int    # 최대 보유 일수
    entry_date: datetime  # 진입 날짜
    entry_price: float    # 진입 가격
    highest_price: float  # 최고가 (트레일링용)


class MonitoringStatus(Enum):
    ACTIVE = "active"
    PROFIT_TARGET = "profit_target"
    STOP_LOSS = "stop_loss"
    TIME_EXIT = "time_exit"
    MANUAL_EXIT = "manual_exit"


class AutoMonitoringService:
    """자동감시매매 서비스"""
    
    def __init__(self, account_no: str):
        self.account_no = account_no
        self.trading_service = AutoTradingService(account_no)
        self.monitoring_rules: Dict[str, MonitoringRule] = {}
        self.is_monitoring = False
        self.monitoring_thread = None
        
    def add_monitoring_rule(self, rule: MonitoringRule):
        """감시 규칙 추가"""
        self.monitoring_rules[rule.code] = rule
        print(f"📊 {rule.name} 감시 시작 - 익절:{rule.profit_target}%, 손절:{rule.stop_loss}%")
    
    def remove_monitoring_rule(self, code: str):
        """감시 규칙 제거"""
        if code in self.monitoring_rules:
            rule = self.monitoring_rules.pop(code)
            print(f"🔚 {rule.name} 감시 종료")
    
    def start_monitoring(self):
        """감시 시작"""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
        print("🔍 자동감시매매 시작")
    
    def stop_monitoring(self):
        """감시 중지"""
        self.is_monitoring = False
        if self.monitoring_thread:
            self.monitoring_thread.join()
        print("⏹️ 자동감시매매 중지")
    
    def _monitoring_loop(self):
        """감시 루프"""
        while self.is_monitoring:
            try:
                self._check_all_positions()
                time.sleep(10)  # 10초마다 체크
            except Exception as e:
                print(f"감시 중 오류: {e}")
                time.sleep(30)  # 오류 시 30초 대기
    
    def _check_all_positions(self):
        """모든 포지션 체크"""
        current_time = datetime.now()
        
        for code, rule in list(self.monitoring_rules.items()):
            try:
                # 현재가 조회
                quote = api.get_stock_quote(code)
                if "error" in quote:
                    continue
                
                current_price = quote.get("current_price", 0)
                if current_price <= 0:
                    continue
                
                # 수익률 계산
                profit_rate = ((current_price - rule.entry_price) / rule.entry_price) * 100
                
                # 트레일링 스탑 업데이트
                if rule.trailing_stop and current_price > rule.highest_price:
                    rule.highest_price = current_price
                
                # 매도 신호 체크
                sell_signal = self._check_sell_signals(rule, current_price, profit_rate, current_time)
                
                if sell_signal:
                    self._execute_sell_order(rule, current_price, sell_signal)
                    self.remove_monitoring_rule(code)
                
            except Exception as e:
                print(f"{rule.name} 체크 중 오류: {e}")
    
    def _check_sell_signals(self, rule: MonitoringRule, current_price: float, 
                           profit_rate: float, current_time: datetime) -> Optional[str]:
        """매도 신호 체크"""
        
        # 1. 익절 체크
        if profit_rate >= rule.profit_target:
            return f"익절 달성 ({profit_rate:.2f}%)"
        
        # 2. 손절 체크
        if profit_rate <= -abs(rule.stop_loss):
            return f"손절 실행 ({profit_rate:.2f}%)"
        
        # 3. 트레일링 스탑 체크
        if rule.trailing_stop:
            trailing_loss = ((current_price - rule.highest_price) / rule.highest_price) * 100
            if trailing_loss <= -5.0:  # 최고점 대비 5% 하락 시
                return f"트레일링 스탑 ({trailing_loss:.2f}%)"
        
        # 4. 시간 기반 매도 체크
        hold_days = (current_time - rule.entry_date).days
        if hold_days >= rule.max_hold_days:
            return f"보유기간 만료 ({hold_days}일)"
        
        # 5. 기술적 분석 기반 매도 신호 (추가 구현 가능)
        technical_signal = self._check_technical_sell_signals(rule.code, current_price)
        if technical_signal:
            return technical_signal
        
        return None
    
    def _check_technical_sell_signals(self, code: str, current_price: float) -> Optional[str]:
        """기술적 분석 기반 매도 신호"""
        try:
            # OHLCV 데이터 조회
            df = api.get_ohlcv(code, 20)
            if df.empty:
                return None
            
            # 간단한 기술적 신호들
            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest
            
            # 1. 거래량 급감 (전일 대비 50% 이하)
            if latest['volume'] < prev['volume'] * 0.5:
                return "거래량 급감"
            
            # 2. 상한가 근접 후 하락 (상한가 95% 이상에서 5% 이상 하락)
            high_price = latest['high']
            if (high_price / prev['close'] >= 1.25 and  # 전일 대비 25% 이상 상승했었고
                current_price / high_price <= 0.95):    # 고점 대비 5% 이상 하락
                return "고점 이탈"
            
            return None
            
        except Exception:
            return None
    
    def _execute_sell_order(self, rule: MonitoringRule, current_price: float, reason: str):
        """매도 주문 실행"""
        try:
            # 보유 수량 확인
            positions = self.trading_service.get_positions()
            position = None
            for pos in positions:
                if pos.code == rule.code:
                    position = pos
                    break
            
            if not position or position.quantity <= 0:
                print(f"⚠️ {rule.name} 보유 수량 없음")
                return
            
            # 매도 신호 생성
            sell_signal = TradingSignal(
                code=rule.code,
                name=rule.name,
                signal_type="SELL",
                target_price=current_price * 0.99,  # 시장가에 가까운 가격
                stop_loss_price=0,
                quantity=position.quantity,
                reason=reason
            )
            
            # 매도 주문 실행
            result = self.trading_service.place_order(sell_signal)
            
            if result.get("success"):
                profit_rate = ((current_price - rule.entry_price) / rule.entry_price) * 100
                print(f"✅ {rule.name} 매도 완료 - {reason}")
                print(f"   진입가: {rule.entry_price:,.0f}원 → 매도가: {current_price:,.0f}원")
                print(f"   수익률: {profit_rate:+.2f}%")
            else:
                print(f"❌ {rule.name} 매도 실패: {result.get('error')}")
                
        except Exception as e:
            print(f"매도 주문 실행 중 오류: {e}")
    
    def get_monitoring_status(self) -> Dict:
        """감시 현황 조회"""
        status = {
            "is_monitoring": self.is_monitoring,
            "total_rules": len(self.monitoring_rules),
            "rules": []
        }
        
        for code, rule in self.monitoring_rules.items():
            try:
                quote = api.get_stock_quote(code)
                current_price = quote.get("current_price", 0)
                profit_rate = ((current_price - rule.entry_price) / rule.entry_price) * 100 if current_price > 0 else 0
                hold_days = (datetime.now() - rule.entry_date).days
                
                rule_status = {
                    "code": code,
                    "name": rule.name,
                    "entry_price": rule.entry_price,
                    "current_price": current_price,
                    "profit_rate": profit_rate,
                    "profit_target": rule.profit_target,
                    "stop_loss": rule.stop_loss,
                    "hold_days": hold_days,
                    "max_hold_days": rule.max_hold_days,
                    "trailing_stop": rule.trailing_stop,
                    "highest_price": rule.highest_price
                }
                status["rules"].append(rule_status)
                
            except Exception as e:
                print(f"{rule.name} 상태 조회 오류: {e}")
        
        return status
    
    def create_rules_from_positions(self, profit_target: float = 10.0, 
                                  stop_loss: float = 5.0, max_hold_days: int = 7) -> int:
        """현재 보유 종목으로부터 감시 규칙 생성"""
        positions = self.trading_service.get_positions()
        created_count = 0
        
        for position in positions:
            if position.code not in self.monitoring_rules:
                rule = MonitoringRule(
                    code=position.code,
                    name=position.name,
                    profit_target=profit_target,
                    stop_loss=stop_loss,
                    trailing_stop=True,
                    max_hold_days=max_hold_days,
                    entry_date=datetime.now() - timedelta(days=1),  # 어제 진입으로 가정
                    entry_price=position.avg_price,
                    highest_price=position.current_price
                )
                self.add_monitoring_rule(rule)
                created_count += 1
        
        return created_count


# 스캔 결과 매수 후 자동으로 감시 규칙 생성
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
                profit_target=7.0,   # 7% 익절
                stop_loss=5.0,       # 5% 손절
                trailing_stop=True,  # 트레일링 스탑 사용
                max_hold_days=5,     # 최대 5일 보유
                entry_date=datetime.now(),
                entry_price=signal.target_price,
                highest_price=signal.target_price
            )
            
            monitoring_service.add_monitoring_rule(rule)
            created_count += 1
    
    return created_count


# 전체 자동매매 + 감시매매 통합 서비스
class IntegratedTradingService:
    """통합 자동매매 서비스"""
    
    def __init__(self, account_no: str):
        self.trading_service = AutoTradingService(account_no)
        self.monitoring_service = AutoMonitoringService(account_no)
    
    def execute_full_cycle(self, scan_results: List[Dict]) -> Dict:
        """전체 사이클 실행: 스캔 → 매수 → 감시 시작"""
        
        # 1. 스캔 결과를 매매 신호로 변환
        from auto_trading_service import convert_scan_to_signals
        signals = convert_scan_to_signals(scan_results)
        
        # 2. 매수 주문 실행
        trading_result = self.trading_service.execute_trading_strategy(signals)
        
        # 3. 매수 완료된 종목들에 대해 감시 시작
        monitoring_count = create_monitoring_rules_from_signals(
            self.monitoring_service, 
            trading_result.get("executed_orders", [])
        )
        
        # 4. 감시 서비스 시작
        if monitoring_count > 0:
            self.monitoring_service.start_monitoring()
        
        return {
            "trading_result": trading_result,
            "monitoring_rules_created": monitoring_count,
            "monitoring_started": monitoring_count > 0
        }
    
    def get_full_status(self) -> Dict:
        """전체 상태 조회"""
        return {
            "account_balance": self.trading_service.get_account_balance(),
            "positions": [pos.__dict__ for pos in self.trading_service.get_positions()],
            "monitoring_status": self.monitoring_service.get_monitoring_status()
        }
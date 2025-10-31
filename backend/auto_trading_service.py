"""
키움 REST API 자동매매 서비스
"""

import time
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

from kiwoom_api import api


class OrderType(Enum):
    BUY = "01"      # 매수
    SELL = "02"     # 매도


class OrderCondition(Enum):
    MARKET = "01"   # 시장가
    LIMIT = "02"    # 지정가


@dataclass
class TradingSignal:
    """매매 신호"""
    code: str
    name: str
    signal_type: str  # "BUY" or "SELL"
    target_price: float
    stop_loss_price: float
    quantity: int
    reason: str


@dataclass
class Position:
    """보유 포지션"""
    code: str
    name: str
    quantity: int
    avg_price: float
    current_price: float
    profit_loss: float
    profit_rate: float


class AutoTradingService:
    """자동매매 서비스"""
    
    def __init__(self, account_no: str):
        self.account_no = account_no
        self.positions: Dict[str, Position] = {}
        self.pending_orders: Dict[str, dict] = {}
        
    def get_account_balance(self) -> Dict:
        """계좌 잔고 조회"""
        try:
            # 키움 계좌 잔고 조회 API 호출
            api_id = "ka10003"  # 계좌 잔고 조회
            path = "/api/dostk/account"
            
            payload = {
                "acnt_no": self.account_no,
                "inqr_dvsn": "01"  # 잔고 조회
            }
            
            data = api._post(api_id, path, payload)
            
            # 응답 데이터 파싱
            output = data.get("output") or {}
            
            return {
                "cash_balance": float(output.get("dnca_tot_amt", 0)),  # 예수금 총액
                "buyable_cash": float(output.get("ord_psbl_cash", 0)),  # 주문 가능 현금
                "total_asset": float(output.get("tot_evlu_amt", 0)),   # 총 평가금액
                "profit_loss": float(output.get("evlu_pfls_smtl_amt", 0))  # 평가손익합계
            }
            
        except Exception as e:
            print(f"계좌 잔고 조회 실패: {e}")
            return {"error": str(e)}
    
    def get_positions(self) -> List[Position]:
        """보유 종목 조회"""
        try:
            # 키움 보유 종목 조회 API 호출
            api_id = "ka10004"  # 보유 종목 조회
            path = "/api/dostk/account"
            
            payload = {
                "acnt_no": self.account_no,
                "inqr_dvsn": "02"  # 보유 종목 조회
            }
            
            data = api._post(api_id, path, payload)
            
            positions = []
            holdings = data.get("output") or []
            
            for holding in holdings:
                code = holding.get("pdno", "")
                if not code:
                    continue
                    
                position = Position(
                    code=code,
                    name=holding.get("prdt_name", ""),
                    quantity=int(holding.get("hldg_qty", 0)),
                    avg_price=float(holding.get("pchs_avg_pric", 0)),
                    current_price=float(holding.get("prpr", 0)),
                    profit_loss=float(holding.get("evlu_pfls_amt", 0)),
                    profit_rate=float(holding.get("evlu_pfls_rt", 0))
                )
                positions.append(position)
                self.positions[code] = position
            
            return positions
            
        except Exception as e:
            print(f"보유 종목 조회 실패: {e}")
            return []
    
    def place_order(self, signal: TradingSignal) -> Dict:
        """주문 실행"""
        try:
            # 키움 주문 API 호출
            api_id = "ka10005"  # 주식 주문
            path = "/api/dostk/order"
            
            # 매수/매도 구분
            ord_dvsn = OrderType.BUY.value if signal.signal_type == "BUY" else OrderType.SELL.value
            
            payload = {
                "acnt_no": self.account_no,
                "pdno": signal.code,  # 종목코드
                "ord_dvsn": ord_dvsn,  # 주문구분
                "ord_qty": str(signal.quantity),  # 주문수량
                "ord_prc": str(int(signal.target_price)),  # 주문가격
                "ord_unpr": OrderCondition.LIMIT.value  # 주문조건 (지정가)
            }
            
            data = api._post(api_id, path, payload)
            
            # 주문 결과 확인
            if data.get("rt_cd") == "0":
                order_no = data.get("output", {}).get("odno", "")
                
                # 대기 주문에 추가
                self.pending_orders[order_no] = {
                    "signal": signal,
                    "order_time": datetime.now(),
                    "status": "pending"
                }
                
                return {
                    "success": True,
                    "order_no": order_no,
                    "message": f"{signal.name} {signal.signal_type} 주문 완료"
                }
            else:
                return {
                    "success": False,
                    "error": data.get("msg1", "주문 실패")
                }
                
        except Exception as e:
            print(f"주문 실행 실패: {e}")
            return {"success": False, "error": str(e)}
    
    def cancel_order(self, order_no: str) -> Dict:
        """주문 취소"""
        try:
            # 키움 주문 취소 API 호출
            api_id = "ka10006"  # 주문 취소
            path = "/api/dostk/order"
            
            payload = {
                "acnt_no": self.account_no,
                "odno": order_no,  # 주문번호
                "ord_dvsn": "03"   # 취소
            }
            
            data = api._post(api_id, path, payload)
            
            if data.get("rt_cd") == "0":
                # 대기 주문에서 제거
                if order_no in self.pending_orders:
                    del self.pending_orders[order_no]
                
                return {"success": True, "message": "주문 취소 완료"}
            else:
                return {"success": False, "error": data.get("msg1", "취소 실패")}
                
        except Exception as e:
            print(f"주문 취소 실패: {e}")
            return {"success": False, "error": str(e)}
    
    def check_order_status(self) -> List[Dict]:
        """주문 체결 확인"""
        try:
            # 키움 주문 체결 조회 API 호출
            api_id = "ka10007"  # 주문 체결 조회
            path = "/api/dostk/order"
            
            payload = {
                "acnt_no": self.account_no,
                "inqr_strt_dt": datetime.now().strftime("%Y%m%d"),
                "inqr_end_dt": datetime.now().strftime("%Y%m%d")
            }
            
            data = api._post(api_id, path, payload)
            
            executions = []
            orders = data.get("output") or []
            
            for order in orders:
                order_no = order.get("odno", "")
                if order_no in self.pending_orders:
                    execution = {
                        "order_no": order_no,
                        "code": order.get("pdno", ""),
                        "name": order.get("prdt_name", ""),
                        "executed_qty": int(order.get("tot_ccld_qty", 0)),
                        "executed_price": float(order.get("avg_prvs", 0)),
                        "status": order.get("ord_stat_name", "")
                    }
                    executions.append(execution)
                    
                    # 완전 체결된 경우 대기 주문에서 제거
                    if execution["status"] == "체결":
                        del self.pending_orders[order_no]
            
            return executions
            
        except Exception as e:
            print(f"주문 체결 확인 실패: {e}")
            return []
    
    def execute_trading_strategy(self, signals: List[TradingSignal]) -> Dict:
        """매매 전략 실행"""
        results = {
            "executed_orders": [],
            "failed_orders": [],
            "total_signals": len(signals)
        }
        
        # 계좌 잔고 확인
        balance = self.get_account_balance()
        if "error" in balance:
            return {"error": "계좌 정보 조회 실패"}
        
        available_cash = balance.get("buyable_cash", 0)
        
        for signal in signals:
            # 매수 신호인 경우 자금 확인
            if signal.signal_type == "BUY":
                required_cash = signal.target_price * signal.quantity
                if required_cash > available_cash:
                    results["failed_orders"].append({
                        "signal": signal,
                        "reason": "자금 부족"
                    })
                    continue
                available_cash -= required_cash
            
            # 매도 신호인 경우 보유 수량 확인
            elif signal.signal_type == "SELL":
                if signal.code not in self.positions:
                    results["failed_orders"].append({
                        "signal": signal,
                        "reason": "보유 종목 없음"
                    })
                    continue
                
                position = self.positions[signal.code]
                if position.quantity < signal.quantity:
                    results["failed_orders"].append({
                        "signal": signal,
                        "reason": "보유 수량 부족"
                    })
                    continue
            
            # 주문 실행
            order_result = self.place_order(signal)
            if order_result.get("success"):
                results["executed_orders"].append(order_result)
            else:
                results["failed_orders"].append({
                    "signal": signal,
                    "reason": order_result.get("error", "주문 실패")
                })
            
            # API 호출 간격 조절
            time.sleep(0.5)
        
        return results


# 자동매매 서비스 인스턴스 생성 함수
def create_auto_trading_service(account_no: str) -> AutoTradingService:
    """자동매매 서비스 생성"""
    return AutoTradingService(account_no)


# 스캔 결과를 매매 신호로 변환
def convert_scan_to_signals(scan_results: List[Dict], max_investment_per_stock: int = 1000000) -> List[TradingSignal]:
    """스캔 결과를 매매 신호로 변환"""
    signals = []
    
    for result in scan_results:
        code = result.get("code", "")
        name = result.get("name", "")
        current_price = result.get("current_price", 0)
        
        if not code or not current_price:
            continue
        
        # 매수 수량 계산 (최대 투자금액 기준)
        quantity = max_investment_per_stock // int(current_price)
        if quantity < 1:
            continue
        
        # 목표가 설정 (현재가 + 5~10%)
        target_price = current_price * 1.07  # 7% 목표
        stop_loss_price = current_price * 0.95  # 5% 손절
        
        signal = TradingSignal(
            code=code,
            name=name,
            signal_type="BUY",
            target_price=target_price,
            stop_loss_price=stop_loss_price,
            quantity=quantity,
            reason=f"AI 스캔 선별 (점수: {result.get('score', 0)})"
        )
        
        signals.append(signal)
    
    return signals
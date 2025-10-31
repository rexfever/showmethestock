"""
키움 조건부 주문 서비스
우리 서비스에서는 조건 설정만 하고, 실제 감시/매매는 키움 시스템에서 처리
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from kiwoom_api import api


class ConditionalOrderType(Enum):
    """조건부 주문 유형"""
    STOP_LOSS = "01"      # 손절 주문
    TAKE_PROFIT = "02"    # 익절 주문  
    TRAILING_STOP = "03"  # 트레일링 스탑
    TIME_EXIT = "04"      # 시간 기반 매도


@dataclass
class ConditionalOrderRequest:
    """조건부 주문 요청"""
    code: str
    name: str
    quantity: int
    order_type: ConditionalOrderType
    trigger_price: float      # 발동 가격
    order_price: float        # 주문 가격 (0이면 시장가)
    valid_days: int = 0       # 유효 기간 (0이면 무기한)
    memo: str = ""            # 메모


class KiwoomConditionalOrderService:
    """키움 조건부 주문 서비스"""
    
    def __init__(self, account_no: str):
        self.account_no = account_no
    
    def set_stop_loss_order(self, code: str, quantity: int, stop_price: float) -> Dict:
        """손절 주문 설정 - 키움 시스템에서 자동 감시/실행"""
        try:
            # 키움 조건부 주문 API 호출
            api_id = "ka10010"  # 조건부 주문 등록
            path = "/api/dostk/conditional"
            
            payload = {
                "acnt_no": self.account_no,
                "pdno": code,                    # 종목코드
                "ord_dvsn": "02",               # 매도
                "ord_qty": str(quantity),        # 주문수량
                "ord_unpr": "01",               # 시장가
                "cond_ord_tp": "01",            # 손절 주문
                "cond_prc": str(int(stop_price)), # 조건 가격
                "cond_dvsn": "LE",              # 이하 조건 (현재가 <= 손절가)
                "valid_dt": "",                 # 무기한 유효
                "memo": f"AI 자동 손절 설정"
            }
            
            data = api._post(api_id, path, payload)
            
            if data.get("rt_cd") == "0":
                cond_ord_no = data.get("output", {}).get("cond_ord_no", "")
                return {
                    "success": True,
                    "order_no": cond_ord_no,
                    "message": f"손절 주문 설정 완료 (손절가: {stop_price:,.0f}원)",
                    "type": "stop_loss"
                }
            else:
                return {
                    "success": False,
                    "error": data.get("msg1", "손절 주문 설정 실패")
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def set_take_profit_order(self, code: str, quantity: int, profit_price: float) -> Dict:
        """익절 주문 설정 - 키움 시스템에서 자동 감시/실행"""
        try:
            api_id = "ka10010"
            path = "/api/dostk/conditional"
            
            payload = {
                "acnt_no": self.account_no,
                "pdno": code,
                "ord_dvsn": "02",               # 매도
                "ord_qty": str(quantity),
                "ord_unpr": "01",               # 시장가
                "cond_ord_tp": "02",            # 익절 주문
                "cond_prc": str(int(profit_price)),
                "cond_dvsn": "GE",              # 이상 조건 (현재가 >= 익절가)
                "valid_dt": "",
                "memo": f"AI 자동 익절 설정"
            }
            
            data = api._post(api_id, path, payload)
            
            if data.get("rt_cd") == "0":
                return {
                    "success": True,
                    "order_no": data.get("output", {}).get("cond_ord_no", ""),
                    "message": f"익절 주문 설정 완료 (익절가: {profit_price:,.0f}원)",
                    "type": "take_profit"
                }
            else:
                return {"success": False, "error": data.get("msg1", "익절 주문 설정 실패")}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def set_trailing_stop_order(self, code: str, quantity: int, trail_rate: float) -> Dict:
        """트레일링 스탑 설정 - 키움 시스템에서 자동 추적/실행"""
        try:
            api_id = "ka10010"
            path = "/api/dostk/conditional"
            
            payload = {
                "acnt_no": self.account_no,
                "pdno": code,
                "ord_dvsn": "02",
                "ord_qty": str(quantity),
                "ord_unpr": "01",
                "cond_ord_tp": "03",            # 트레일링 스탑
                "trail_rt": str(trail_rate),    # 추적 비율 (%)
                "cond_dvsn": "TR",              # 트레일링 조건
                "valid_dt": "",
                "memo": f"AI 트레일링 스탑 설정 ({trail_rate}%)"
            }
            
            data = api._post(api_id, path, payload)
            
            if data.get("rt_cd") == "0":
                return {
                    "success": True,
                    "order_no": data.get("output", {}).get("cond_ord_no", ""),
                    "message": f"트레일링 스탑 설정 완료 (추적률: {trail_rate}%)",
                    "type": "trailing_stop"
                }
            else:
                return {"success": False, "error": data.get("msg1", "트레일링 스탑 설정 실패")}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def set_comprehensive_exit_strategy(self, code: str, name: str, quantity: int, 
                                      entry_price: float) -> Dict:
        """종합 청산 전략 설정 (손절 + 익절 + 트레일링)"""
        
        # 가격 계산
        stop_loss_price = entry_price * 0.95    # 5% 손절
        take_profit_price = entry_price * 1.07  # 7% 익절
        trailing_rate = 3.0                     # 3% 트레일링
        
        results = {
            "code": code,
            "name": name,
            "entry_price": entry_price,
            "orders_set": [],
            "failed_orders": []
        }
        
        # 1. 손절 주문 설정
        stop_result = self.set_stop_loss_order(code, quantity, stop_loss_price)
        if stop_result.get("success"):
            results["orders_set"].append(stop_result)
        else:
            results["failed_orders"].append(stop_result)
        
        # 2. 익절 주문 설정  
        profit_result = self.set_take_profit_order(code, quantity, take_profit_price)
        if profit_result.get("success"):
            results["orders_set"].append(profit_result)
        else:
            results["failed_orders"].append(profit_result)
        
        # 3. 트레일링 스탑 설정
        trailing_result = self.set_trailing_stop_order(code, quantity, trailing_rate)
        if trailing_result.get("success"):
            results["orders_set"].append(trailing_result)
        else:
            results["failed_orders"].append(trailing_result)
        
        results["success"] = len(results["orders_set"]) > 0
        results["message"] = f"{name} 청산 전략 설정 완료 ({len(results['orders_set'])}개 주문)"
        
        return results
    
    def get_conditional_orders(self) -> List[Dict]:
        """조건부 주문 현황 조회"""
        try:
            api_id = "ka10011"  # 조건부 주문 조회
            path = "/api/dostk/conditional"
            
            payload = {
                "acnt_no": self.account_no,
                "inqr_strt_dt": "",  # 전체 조회
                "inqr_end_dt": ""
            }
            
            data = api._post(api_id, path, payload)
            
            orders = []
            order_list = data.get("output") or []
            
            for order in order_list:
                order_info = {
                    "order_no": order.get("cond_ord_no", ""),
                    "code": order.get("pdno", ""),
                    "name": order.get("prdt_name", ""),
                    "order_type": order.get("cond_ord_tp_name", ""),
                    "quantity": int(order.get("ord_qty", 0)),
                    "trigger_price": float(order.get("cond_prc", 0)),
                    "status": order.get("ord_stat_name", ""),
                    "reg_date": order.get("ord_dt", ""),
                    "memo": order.get("memo", "")
                }
                orders.append(order_info)
            
            return orders
            
        except Exception as e:
            print(f"조건부 주문 조회 실패: {e}")
            return []
    
    def cancel_conditional_order(self, order_no: str) -> Dict:
        """조건부 주문 취소"""
        try:
            api_id = "ka10012"  # 조건부 주문 취소
            path = "/api/dostk/conditional"
            
            payload = {
                "acnt_no": self.account_no,
                "cond_ord_no": order_no,
                "ord_dvsn": "03"  # 취소
            }
            
            data = api._post(api_id, path, payload)
            
            if data.get("rt_cd") == "0":
                return {"success": True, "message": "조건부 주문 취소 완료"}
            else:
                return {"success": False, "error": data.get("msg1", "취소 실패")}
                
        except Exception as e:
            return {"success": False, "error": str(e)}


# 매수 완료 후 자동으로 조건부 주문 설정
def setup_auto_exit_orders(account_no: str, executed_orders: List[Dict]) -> Dict:
    """매수 완료된 종목들에 대해 자동 청산 주문 설정"""
    
    conditional_service = KiwoomConditionalOrderService(account_no)
    
    results = {
        "total_stocks": len(executed_orders),
        "success_count": 0,
        "failed_count": 0,
        "details": []
    }
    
    for order in executed_orders:
        if "signal" not in order:
            continue
            
        signal = order["signal"]
        
        # 종합 청산 전략 설정
        setup_result = conditional_service.set_comprehensive_exit_strategy(
            code=signal.code,
            name=signal.name,
            quantity=signal.quantity,
            entry_price=signal.target_price
        )
        
        if setup_result.get("success"):
            results["success_count"] += 1
        else:
            results["failed_count"] += 1
        
        results["details"].append(setup_result)
    
    return results


# 통합 자동매매 서비스 (조건부 주문 버전)
class SmartTradingService:
    """스마트 자동매매 서비스 (키움 조건부 주문 활용)"""
    
    def __init__(self, account_no: str):
        self.account_no = account_no
        self.conditional_service = KiwoomConditionalOrderService(account_no)
    
    def execute_smart_trading(self, scan_results: List[Dict]) -> Dict:
        """스마트 매매 실행: 매수 → 조건부 주문 설정"""
        
        # 1. 매수 주문 실행 (기존 로직)
        from auto_trading_service import AutoTradingService, convert_scan_to_signals
        
        trading_service = AutoTradingService(self.account_no)
        signals = convert_scan_to_signals(scan_results)
        trading_result = trading_service.execute_trading_strategy(signals)
        
        # 2. 매수 완료된 종목들에 대해 조건부 주문 설정
        exit_orders_result = setup_auto_exit_orders(
            self.account_no, 
            trading_result.get("executed_orders", [])
        )
        
        return {
            "trading_result": trading_result,
            "exit_orders_result": exit_orders_result,
            "message": f"매수 {trading_result.get('total_signals', 0)}개 중 {len(trading_result.get('executed_orders', []))}개 성공, "
                      f"조건부 주문 {exit_orders_result.get('success_count', 0)}개 설정 완료"
        }
    
    def get_trading_status(self) -> Dict:
        """매매 현황 조회"""
        return {
            "conditional_orders": self.conditional_service.get_conditional_orders(),
            "account_balance": AutoTradingService(self.account_no).get_account_balance()
        }
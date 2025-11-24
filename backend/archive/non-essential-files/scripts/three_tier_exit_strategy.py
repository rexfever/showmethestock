"""
3단계 청산 전략: 손절 -5%, 보존 4%, 익절 8%
"""

from typing import Dict, List
from dataclasses import dataclass
from kiwoom_api import api


@dataclass
class ThreeTierExitStrategy:
    """3단계 청산 전략"""
    code: str
    name: str
    quantity: int
    entry_price: float
    
    # 전략 설정
    stop_loss_rate: float = 5.0      # 손절 -5%
    preserve_rate: float = 4.0       # 보존 4%
    take_profit_rate: float = 8.0    # 익절 8%


class ThreeTierOrderManager:
    """3단계 청산 주문 관리"""
    
    def __init__(self, account_no: str):
        self.account_no = account_no
    
    def setup_three_tier_orders(self, strategy: ThreeTierExitStrategy) -> Dict:
        """3단계 청산 주문 설정"""
        
        # 가격 계산
        stop_price = strategy.entry_price * (1 - strategy.stop_loss_rate / 100)
        preserve_price = strategy.entry_price * (1 + strategy.preserve_rate / 100)
        profit_price = strategy.entry_price * (1 + strategy.take_profit_rate / 100)
        
        results = {
            "code": strategy.code,
            "name": strategy.name,
            "entry_price": strategy.entry_price,
            "stop_price": stop_price,
            "preserve_price": preserve_price,
            "profit_price": profit_price,
            "orders": [],
            "failed_orders": []
        }
        
        # 1단계: 손절 주문 (전체 수량)
        stop_result = self._set_stop_loss_order(
            strategy.code, strategy.quantity, stop_price
        )
        if stop_result.get("success"):
            results["orders"].append({
                "type": "stop_loss",
                "price": stop_price,
                "quantity": strategy.quantity,
                "order_no": stop_result.get("order_no")
            })
        else:
            results["failed_orders"].append(stop_result)
        
        # 2단계: 보존 주문 (50% 수량)
        preserve_quantity = strategy.quantity // 2
        if preserve_quantity > 0:
            preserve_result = self._set_preserve_order(
                strategy.code, preserve_quantity, preserve_price
            )
            if preserve_result.get("success"):
                results["orders"].append({
                    "type": "preserve",
                    "price": preserve_price,
                    "quantity": preserve_quantity,
                    "order_no": preserve_result.get("order_no")
                })
            else:
                results["failed_orders"].append(preserve_result)
        
        # 3단계: 익절 주문 (나머지 50% 수량)
        profit_quantity = strategy.quantity - preserve_quantity
        if profit_quantity > 0:
            profit_result = self._set_take_profit_order(
                strategy.code, profit_quantity, profit_price
            )
            if profit_result.get("success"):
                results["orders"].append({
                    "type": "take_profit",
                    "price": profit_price,
                    "quantity": profit_quantity,
                    "order_no": profit_result.get("order_no")
                })
            else:
                results["failed_orders"].append(profit_result)
        
        results["success"] = len(results["orders"]) >= 2  # 최소 2개 주문 성공
        results["message"] = f"{strategy.name} 3단계 청산 전략 설정 완료"
        
        return results
    
    def _set_stop_loss_order(self, code: str, quantity: int, stop_price: float) -> Dict:
        """손절 주문 설정"""
        try:
            api_id = "ka10010"
            path = "/api/dostk/conditional"
            
            payload = {
                "acnt_no": self.account_no,
                "pdno": code,
                "ord_dvsn": "02",  # 매도
                "ord_qty": str(quantity),
                "ord_unpr": "01",  # 시장가
                "cond_ord_tp": "01",  # 손절 주문
                "cond_prc": str(int(stop_price)),
                "cond_dvsn": "LE",  # 이하 조건
                "valid_dt": "",
                "memo": f"3단계 전략 - 손절 {stop_price:,.0f}원"
            }
            
            data = api._post(api_id, path, payload)
            
            if data.get("rt_cd") == "0":
                return {
                    "success": True,
                    "order_no": data.get("output", {}).get("cond_ord_no", ""),
                    "message": f"손절 주문 설정 완료"
                }
            else:
                return {"success": False, "error": data.get("msg1", "손절 주문 실패")}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _set_preserve_order(self, code: str, quantity: int, preserve_price: float) -> Dict:
        """보존 주문 설정 (4% 수익 확보)"""
        try:
            api_id = "ka10010"
            path = "/api/dostk/conditional"
            
            payload = {
                "acnt_no": self.account_no,
                "pdno": code,
                "ord_dvsn": "02",  # 매도
                "ord_qty": str(quantity),
                "ord_unpr": "01",  # 시장가
                "cond_ord_tp": "02",  # 지정가 조건 주문
                "cond_prc": str(int(preserve_price)),
                "cond_dvsn": "GE",  # 이상 조건
                "valid_dt": "",
                "memo": f"3단계 전략 - 보존 {preserve_price:,.0f}원 (4% 수익)"
            }
            
            data = api._post(api_id, path, payload)
            
            if data.get("rt_cd") == "0":
                return {
                    "success": True,
                    "order_no": data.get("output", {}).get("cond_ord_no", ""),
                    "message": f"보존 주문 설정 완료"
                }
            else:
                return {"success": False, "error": data.get("msg1", "보존 주문 실패")}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _set_take_profit_order(self, code: str, quantity: int, profit_price: float) -> Dict:
        """익절 주문 설정 (8% 수익 확보)"""
        try:
            api_id = "ka10010"
            path = "/api/dostk/conditional"
            
            payload = {
                "acnt_no": self.account_no,
                "pdno": code,
                "ord_dvsn": "02",  # 매도
                "ord_qty": str(quantity),
                "ord_unpr": "01",  # 시장가
                "cond_ord_tp": "02",  # 지정가 조건 주문
                "cond_prc": str(int(profit_price)),
                "cond_dvsn": "GE",  # 이상 조건
                "valid_dt": "",
                "memo": f"3단계 전략 - 익절 {profit_price:,.0f}원 (8% 수익)"
            }
            
            data = api._post(api_id, path, payload)
            
            if data.get("rt_cd") == "0":
                return {
                    "success": True,
                    "order_no": data.get("output", {}).get("cond_ord_no", ""),
                    "message": f"익절 주문 설정 완료"
                }
            else:
                return {"success": False, "error": data.get("msg1", "익절 주문 실패")}
                
        except Exception as e:
            return {"success": False, "error": str(e)}


# 사용 예시
def setup_three_tier_strategy_for_position(account_no: str, code: str, name: str, 
                                          quantity: int, entry_price: float) -> Dict:
    """포지션에 대해 3단계 청산 전략 설정"""
    
    strategy = ThreeTierExitStrategy(
        code=code,
        name=name,
        quantity=quantity,
        entry_price=entry_price
    )
    
    order_manager = ThreeTierOrderManager(account_no)
    result = order_manager.setup_three_tier_orders(strategy)
    
    print(f"🎯 {name} 3단계 청산 전략:")
    print(f"   손절: {result['stop_price']:,.0f}원 (-5%)")
    print(f"   보존: {result['preserve_price']:,.0f}원 (+4%) - {quantity//2}주")
    print(f"   익절: {result['profit_price']:,.0f}원 (+8%) - {quantity - quantity//2}주")
    
    return result
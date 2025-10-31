"""
사용자별 키움 API 클래스
각 사용자의 개인 API Key로 모든 API 호출 수행
"""

import time
from datetime import datetime
import os
from typing import List, Dict, Optional
import requests
import pandas as pd
import numpy as np

from user_api_manager import UserAPIManager


class UserSpecificKiwoomAPI:
    """사용자별 키움 API 클래스"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.api_manager = UserAPIManager()
        self.user_api_info = None
        self._load_user_api()
    
    def _load_user_api(self):
        """사용자 API 정보 로드"""
        self.user_api_info = self.api_manager.get_user_api(self.user_id)
        if not self.user_api_info:
            raise ValueError(f"사용자 {self.user_id}의 API Key가 등록되지 않았습니다")
    
    def _get_auth_headers(self, api_id: str) -> Dict[str, str]:
        """사용자별 인증 헤더 생성"""
        if not self.user_api_info:
            raise ValueError("API 정보가 로드되지 않았습니다")
        
        # 키움 API 인증 헤더 생성
        headers = {
            "Content-Type": "application/json",
            "authorization": f"Bearer {self._get_access_token()}",
            "appkey": self.user_api_info["app_key"],
            "appsecret": self.user_api_info["app_secret"],
            "tr_id": api_id
        }
        
        return headers
    
    def _get_access_token(self) -> str:
        """사용자별 액세스 토큰 발급"""
        try:
            # 키움 OAuth2 토큰 발급
            token_url = "https://openapi.kiwoom.com/oauth2/tokenP"
            
            payload = {
                "grant_type": "client_credentials",
                "appkey": self.user_api_info["app_key"],
                "appsecret": self.user_api_info["app_secret"]
            }
            
            response = requests.post(token_url, json=payload, timeout=10)
            response.raise_for_status()
            
            token_data = response.json()
            return token_data.get("access_token", "")
            
        except Exception as e:
            print(f"토큰 발급 실패 ({self.user_id}): {e}")
            return ""
    
    def _post(self, api_id: str, path: str, payload: dict, extra_headers: Dict[str, str] = None) -> dict:
        """사용자별 API 호출"""
        
        # 사용자별 인증 헤더 생성
        headers = self._get_auth_headers(api_id)
        if extra_headers:
            headers.update(extra_headers)
        
        # API 호출
        url = f"https://openapi.kiwoom.com{path}"
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        
        # 레이트 리밋 준수
        time.sleep(0.25)
        
        response.raise_for_status()
        data = response.json()
        
        # 사용 시간 업데이트
        self.api_manager.update_last_used(self.user_id)
        
        return data
    
    def get_account_balance(self) -> Dict:
        """사용자 계좌 잔고 조회"""
        try:
            api_id = "TTTC8434R"  # 계좌 잔고 조회
            path = "/uapi/domestic-stock/v1/trading/inquire-balance"
            
            payload = {
                "CANO": self.user_api_info["account_no"][:8],
                "ACNT_PRDT_CD": self.user_api_info["account_no"][8:],
                "INQR_DVSN": "01"
            }
            
            data = self._post(api_id, path, payload)
            
            # 응답 데이터 파싱
            output = data.get("output2", [{}])[0] if data.get("output2") else {}
            
            return {
                "user_id": self.user_id,
                "account_no": self.user_api_info["account_no"],
                "cash_balance": float(output.get("dnca_tot_amt", 0)),
                "buyable_cash": float(output.get("ord_psbl_cash", 0)),
                "total_asset": float(output.get("tot_evlu_amt", 0)),
                "profit_loss": float(output.get("evlu_pfls_smtl_amt", 0))
            }
            
        except Exception as e:
            print(f"계좌 잔고 조회 실패 ({self.user_id}): {e}")
            return {"error": str(e)}
    
    def place_buy_order(self, code: str, quantity: int, price: float) -> Dict:
        """사용자별 매수 주문"""
        try:
            api_id = "TTTC0802U"  # 주식 현금 매수 주문
            path = "/uapi/domestic-stock/v1/trading/order-cash"
            
            payload = {
                "CANO": self.user_api_info["account_no"][:8],
                "ACNT_PRDT_CD": self.user_api_info["account_no"][8:],
                "PDNO": code,
                "ORD_DVSN": "00",  # 지정가
                "ORD_QTY": str(quantity),
                "ORD_UNPR": str(int(price))
            }
            
            data = self._post(api_id, path, payload)
            
            if data.get("rt_cd") == "0":
                return {
                    "success": True,
                    "user_id": self.user_id,
                    "order_no": data.get("output", {}).get("ODNO", ""),
                    "message": f"{code} 매수 주문 완료"
                }
            else:
                return {
                    "success": False,
                    "user_id": self.user_id,
                    "error": data.get("msg1", "매수 주문 실패")
                }
                
        except Exception as e:
            return {
                "success": False,
                "user_id": self.user_id,
                "error": str(e)
            }
    
    def place_conditional_order(self, code: str, quantity: int, condition_type: str, 
                              trigger_price: float) -> Dict:
        """사용자별 조건부 주문"""
        try:
            api_id = "TTTC0803U"  # 조건부 주문
            path = "/uapi/domestic-stock/v1/trading/order-condition"
            
            payload = {
                "CANO": self.user_api_info["account_no"][:8],
                "ACNT_PRDT_CD": self.user_api_info["account_no"][8:],
                "PDNO": code,
                "ORD_DVSN": "01",  # 시장가
                "ORD_QTY": str(quantity),
                "ORD_UNPR": "0",
                "STCK_COND_TP": condition_type,  # 조건 유형
                "STCK_COND_PRC": str(int(trigger_price))
            }
            
            data = self._post(api_id, path, payload)
            
            if data.get("rt_cd") == "0":
                return {
                    "success": True,
                    "user_id": self.user_id,
                    "order_no": data.get("output", {}).get("ODNO", ""),
                    "message": f"{code} 조건부 주문 설정 완료"
                }
            else:
                return {
                    "success": False,
                    "user_id": self.user_id,
                    "error": data.get("msg1", "조건부 주문 실패")
                }
                
        except Exception as e:
            return {
                "success": False,
                "user_id": self.user_id,
                "error": str(e)
            }
    
    def get_stock_quote(self, code: str) -> Dict:
        """종목 현재가 조회 (사용자 API로)"""
        try:
            api_id = "FHKST01010100"  # 주식 현재가 시세
            path = "/uapi/domestic-stock/v1/quotations/inquire-price"
            
            payload = {
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_INPUT_ISCD": code
            }
            
            data = self._post(api_id, path, payload)
            
            output = data.get("output", {})
            
            return {
                "user_id": self.user_id,
                "code": code,
                "current_price": float(output.get("stck_prpr", 0)),
                "change_rate": float(output.get("prdy_ctrt", 0)),
                "volume": int(output.get("acml_vol", 0))
            }
            
        except Exception as e:
            return {
                "user_id": self.user_id,
                "code": code,
                "error": str(e)
            }
    
    def get_ohlcv(self, code: str, count: int = 220) -> pd.DataFrame:
        """일봉 OHLCV 조회 (사용자 API로)"""
        try:
            api_id = "FHKST03010100"  # 국내주식 기간별 시세
            path = "/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
            
            payload = {
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_INPUT_ISCD": code,
                "FID_INPUT_DATE_1": "",  # 시작일 (공백시 최근)
                "FID_INPUT_DATE_2": "",  # 종료일 (공백시 오늘)
                "FID_PERIOD_DIV_CODE": "D"  # 일봉
            }
            
            data = self._post(api_id, path, payload)
            
            output = data.get("output2", [])
            
            df_data = []
            for item in output[:count]:
                df_data.append({
                    "date": item.get("stck_bsop_date", ""),
                    "open": float(item.get("stck_oprc", 0)),
                    "high": float(item.get("stck_hgpr", 0)),
                    "low": float(item.get("stck_lwpr", 0)),
                    "close": float(item.get("stck_clpr", 0)),
                    "volume": int(item.get("acml_vol", 0))
                })
            
            df = pd.DataFrame(df_data)
            if not df.empty:
                df = df.sort_values("date").reset_index(drop=True)
            
            return df
            
        except Exception as e:
            print(f"OHLCV 조회 실패 ({self.user_id}, {code}): {e}")
            return pd.DataFrame()


class UserSpecificTradingEngine:
    """사용자별 자동매매 엔진"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.api = UserSpecificKiwoomAPI(user_id)
        self.api_manager = UserAPIManager()
    
    def execute_user_trading(self, scan_results: List[Dict]) -> Dict:
        """사용자별 자동매매 실행"""
        
        # 1. 사용자 설정 확인
        user_status = self.api_manager.get_user_api_status(self.user_id)
        if not user_status.get("is_auto_trading_enabled"):
            return {
                "success": False,
                "user_id": self.user_id,
                "error": "자동매매가 비활성화되어 있습니다"
            }
        
        # 2. 계좌 잔고 확인
        balance = self.api.get_account_balance()
        if "error" in balance:
            return {
                "success": False,
                "user_id": self.user_id,
                "error": "계좌 정보 조회 실패"
            }
        
        available_cash = balance.get("buyable_cash", 0)
        daily_limit = user_status.get("daily_limit", 10_000_000)
        
        # 3. 투자 가능 금액 계산
        max_investment = min(available_cash, daily_limit)
        
        # 4. 매수 주문 실행
        executed_orders = []
        failed_orders = []
        total_investment = 0
        
        for signal in scan_results:
            if total_investment >= max_investment:
                break
            
            code = signal.get("code", "")
            current_price = signal.get("current_price", 0)
            
            if not code or current_price <= 0:
                continue
            
            # 종목당 투자금 계산
            per_stock_limit = min(1_000_000, max_investment - total_investment)
            quantity = per_stock_limit // int(current_price)
            
            if quantity < 1:
                continue
            
            # 매수 주문 실행
            order_result = self.api.place_buy_order(code, quantity, current_price)
            
            if order_result.get("success"):
                executed_orders.append(order_result)
                total_investment += quantity * current_price
            else:
                failed_orders.append(order_result)
        
        return {
            "success": True,
            "user_id": self.user_id,
            "executed_orders": len(executed_orders),
            "failed_orders": len(failed_orders),
            "total_investment": total_investment,
            "available_cash": available_cash,
            "daily_limit": daily_limit
        }


# 사용자별 API 인스턴스 생성 함수
def create_user_api(user_id: str) -> Optional[UserSpecificKiwoomAPI]:
    """사용자별 키움 API 인스턴스 생성"""
    try:
        return UserSpecificKiwoomAPI(user_id)
    except Exception as e:
        print(f"사용자 API 생성 실패 ({user_id}): {e}")
        return None


# 모든 활성 사용자에 대해 자동매매 실행
def execute_all_users_trading(scan_results: List[Dict]) -> Dict:
    """모든 활성 사용자에 대해 자동매매 실행"""
    
    api_manager = UserAPIManager()
    active_users = api_manager.get_all_active_users()
    
    results = {
        "total_users": len(active_users),
        "successful_users": 0,
        "failed_users": 0,
        "user_results": []
    }
    
    for user_id in active_users:
        try:
            trading_engine = UserSpecificTradingEngine(user_id)
            user_result = trading_engine.execute_user_trading(scan_results)
            
            if user_result.get("success"):
                results["successful_users"] += 1
            else:
                results["failed_users"] += 1
            
            results["user_results"].append(user_result)
            
        except Exception as e:
            results["failed_users"] += 1
            results["user_results"].append({
                "success": False,
                "user_id": user_id,
                "error": str(e)
            })
    
    return results
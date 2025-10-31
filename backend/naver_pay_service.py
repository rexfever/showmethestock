"""
네이버페이 결제 서비스
"""
import os
import httpx
from datetime import datetime, timedelta
from typing import Optional
from auth_models import PaymentResponse
from subscription_plans import get_plan

class NaverPayService:
    def __init__(self):
        self.client_id = os.getenv("NAVER_PAY_CLIENT_ID")
        self.client_secret = os.getenv("NAVER_PAY_CLIENT_SECRET")
        self.base_url = "https://dev.apis.naver.com/naverpay-partner/naverpay/payments/v2.2"
        self.test_mode = os.getenv("NAVER_PAY_TEST_MODE", "true").lower() == "true"
        
        if not self.test_mode:
            self.base_url = "https://apis.naver.com/naverpay-partner/naverpay/payments/v2.2"
    
    async def create_payment(
        self, 
        user_id: int, 
        plan_id: str, 
        return_url: str, 
        cancel_url: str
    ) -> Optional[PaymentResponse]:
        """네이버페이 결제 생성"""
        try:
            plan = get_plan(plan_id)
            if not plan:
                return None
            
            merchant_pay_key = f"NAVER_{user_id}_{int(datetime.now().timestamp())}"
            
            payment_data = {
                "merchantPayKey": merchant_pay_key,
                "productName": plan.name,
                "totalPayAmount": plan.price,
                "returnUrl": return_url,
                "taxScopeAmount": plan.price,
                "taxExScopeAmount": 0,
                "purchaserName": f"user_{user_id}",
                "purchaserBirthday": "19900101",
                "orderNo": merchant_pay_key,
                "useCfmYmdt": (datetime.now() + timedelta(days=7)).strftime("%Y%m%d")
            }
            
            headers = {
                "X-Naver-Client-Id": self.client_id,
                "X-Naver-Client-Secret": self.client_secret,
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/reserve",
                    json=payment_data,
                    headers=headers
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    return PaymentResponse(
                        payment_id=result.get("paymentId"),
                        payment_url=result.get("paymentUrl"),
                        amount=plan.price,
                        status="ready"
                    )
                else:
                    print(f"네이버페이 결제 생성 실패: {response.status_code}, {response.text}")
                    return None
                    
        except Exception as e:
            print(f"네이버페이 결제 생성 오류: {e}")
            return None
    
    async def approve_payment(self, payment_id: str, user_id: int, plan_id: str) -> Optional[dict]:
        """네이버페이 결제 승인"""
        try:
            plan = get_plan(plan_id)
            if not plan:
                return None
            
            headers = {
                "X-Naver-Client-Id": self.client_id,
                "X-Naver-Client-Secret": self.client_secret,
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/primary/approve",
                    json={"paymentId": payment_id},
                    headers=headers
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    subscription_data = {
                        "user_id": user_id,
                        "plan_id": plan_id,
                        "payment_id": payment_id,
                        "amount": result.get("body", {}).get("totalPayAmount"),
                        "status": "approved",
                        "expires_at": datetime.now() + timedelta(days=plan.duration_days)
                    }
                    
                    return subscription_data
                else:
                    print(f"네이버페이 결제 승인 실패: {response.status_code}, {response.text}")
                    return None
                    
        except Exception as e:
            print(f"네이버페이 결제 승인 오류: {e}")
            return None
    
    async def cancel_payment(self, payment_id: str, cancel_amount: int, reason: str = "사용자 요청") -> bool:
        """네이버페이 결제 취소"""
        try:
            cancel_data = {
                "paymentId": payment_id,
                "cancelAmount": cancel_amount,
                "cancelReason": reason,
                "cancelRequester": "CUSTOMER"
            }
            
            headers = {
                "X-Naver-Client-Id": self.client_id,
                "X-Naver-Client-Secret": self.client_secret,
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/cancel",
                    json=cancel_data,
                    headers=headers
                )
                
                return response.status_code == 200
                
        except Exception as e:
            print(f"네이버페이 결제 취소 오류: {e}")
            return False

# 전역 인스턴스
naver_pay_service = NaverPayService()
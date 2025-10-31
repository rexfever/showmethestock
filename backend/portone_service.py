"""
포트원(PortOne) 결제 서비스
"""
import os
import httpx
from datetime import datetime, timedelta
from typing import Optional
from auth_models import PaymentResponse
from subscription_plans import get_plan

class PortOneService:
    def __init__(self):
        self.imp_key = os.getenv("PORTONE_IMP_KEY")
        self.imp_secret = os.getenv("PORTONE_IMP_SECRET")
        self.base_url = "https://api.iamport.kr"
        self.access_token = None
    
    async def get_access_token(self):
        """포트원 액세스 토큰 발급"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/users/getToken",
                    json={
                        "imp_key": self.imp_key,
                        "imp_secret": self.imp_secret
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    self.access_token = result["response"]["access_token"]
                    return self.access_token
                return None
        except Exception as e:
            print(f"포트원 토큰 발급 오류: {e}")
            return None
    
    async def create_payment(
        self, 
        user_id: int, 
        plan_id: str, 
        pay_method: str = "card"
    ) -> Optional[PaymentResponse]:
        """포트원 결제 생성"""
        try:
            plan = get_plan(plan_id)
            if not plan:
                return None
            
            merchant_uid = f"ORDER_{user_id}_{int(datetime.now().timestamp())}"
            
            payment_data = {
                "merchant_uid": merchant_uid,
                "name": plan.name,
                "amount": plan.price,
                "buyer_name": f"user_{user_id}",
                "buyer_email": f"user{user_id}@example.com",
                "pay_method": pay_method,  # card, kakaopay, naverpay, tosspay
                "notice_url": f"{os.getenv('BASE_URL')}/payment/portone/webhook"
            }
            
            return PaymentResponse(
                payment_id=merchant_uid,
                payment_url=None,  # 클라이언트에서 직접 결제창 호출
                amount=plan.price,
                status="ready",
                payment_data=payment_data
            )
                    
        except Exception as e:
            print(f"포트원 결제 생성 오류: {e}")
            return None
    
    async def verify_payment(self, imp_uid: str, merchant_uid: str) -> Optional[dict]:
        """포트원 결제 검증"""
        try:
            if not self.access_token:
                await self.get_access_token()
            
            headers = {"Authorization": f"Bearer {self.access_token}"}
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/payments/{imp_uid}",
                    headers=headers
                )
                
                if response.status_code == 200:
                    result = response.json()
                    payment_data = result["response"]
                    
                    # 결제 금액 검증
                    if payment_data["status"] == "paid":
                        return {
                            "imp_uid": imp_uid,
                            "merchant_uid": merchant_uid,
                            "amount": payment_data["amount"],
                            "status": "approved"
                        }
                return None
                    
        except Exception as e:
            print(f"포트원 결제 검증 오류: {e}")
            return None
    
    async def cancel_payment(self, imp_uid: str, amount: int, reason: str = "사용자 요청") -> bool:
        """포트원 결제 취소"""
        try:
            if not self.access_token:
                await self.get_access_token()
            
            headers = {"Authorization": f"Bearer {self.access_token}"}
            
            cancel_data = {
                "imp_uid": imp_uid,
                "amount": amount,
                "reason": reason
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/payments/cancel",
                    json=cancel_data,
                    headers=headers
                )
                
                return response.status_code == 200
                
        except Exception as e:
            print(f"포트원 결제 취소 오류: {e}")
            return False

portone_service = PortOneService()
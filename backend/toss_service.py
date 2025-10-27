"""
토스페이먼츠 결제 서비스
"""
import os
import httpx
import base64
from datetime import datetime, timedelta
from typing import Optional
from auth_models import PaymentResponse
from subscription_plans import get_plan

class TossPaymentsService:
    def __init__(self):
        self.secret_key = os.getenv("TOSS_SECRET_KEY")
        self.client_key = os.getenv("TOSS_CLIENT_KEY")
        self.base_url = "https://api.tosspayments.com/v1"
        self.test_mode = os.getenv("TOSS_TEST_MODE", "true").lower() == "true"
        
        if self.test_mode:
            self.secret_key = "test_sk_" + (self.secret_key or "")
    
    def get_auth_header(self):
        """토스페이먼츠 인증 헤더"""
        credentials = base64.b64encode(f"{self.secret_key}:".encode()).decode()
        return {"Authorization": f"Basic {credentials}"}
    
    async def create_payment(
        self, 
        user_id: int, 
        plan_id: str
    ) -> Optional[PaymentResponse]:
        """토스페이먼츠 결제 생성"""
        try:
            plan = get_plan(plan_id)
            if not plan:
                return None
            
            order_id = f"ORDER_{user_id}_{int(datetime.now().timestamp())}"
            
            payment_data = {
                "orderId": order_id,
                "orderName": plan.name,
                "amount": plan.price,
                "successUrl": f"{os.getenv('BASE_URL')}/payment/toss/success",
                "failUrl": f"{os.getenv('BASE_URL')}/payment/toss/fail",
                "customerName": f"user_{user_id}",
                "customerEmail": f"user{user_id}@example.com"
            }
            
            return PaymentResponse(
                payment_id=order_id,
                payment_url=None,  # 클라이언트에서 직접 결제창 호출
                amount=plan.price,
                status="ready",
                payment_data=payment_data
            )
                    
        except Exception as e:
            print(f"토스페이먼츠 결제 생성 오류: {e}")
            return None
    
    async def confirm_payment(
        self, 
        payment_key: str, 
        order_id: str, 
        amount: int
    ) -> Optional[dict]:
        """토스페이먼츠 결제 승인"""
        try:
            headers = {
                **self.get_auth_header(),
                "Content-Type": "application/json"
            }
            
            confirm_data = {
                "paymentKey": payment_key,
                "orderId": order_id,
                "amount": amount
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/payments/confirm",
                    json=confirm_data,
                    headers=headers
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    return {
                        "payment_key": payment_key,
                        "order_id": order_id,
                        "amount": result["totalAmount"],
                        "status": "approved",
                        "method": result["method"]
                    }
                else:
                    print(f"토스페이먼츠 결제 승인 실패: {response.status_code}, {response.text}")
                    return None
                    
        except Exception as e:
            print(f"토스페이먼츠 결제 승인 오류: {e}")
            return None
    
    async def cancel_payment(
        self, 
        payment_key: str, 
        cancel_reason: str = "사용자 요청"
    ) -> bool:
        """토스페이먼츠 결제 취소"""
        try:
            headers = {
                **self.get_auth_header(),
                "Content-Type": "application/json"
            }
            
            cancel_data = {
                "cancelReason": cancel_reason
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/payments/{payment_key}/cancel",
                    json=cancel_data,
                    headers=headers
                )
                
                return response.status_code == 200
                
        except Exception as e:
            print(f"토스페이먼츠 결제 취소 오류: {e}")
            return False

toss_service = TossPaymentsService()
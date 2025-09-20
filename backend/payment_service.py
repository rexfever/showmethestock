"""
카카오페이 결제 서비스
"""
import os
import httpx
import uuid
from datetime import datetime, timedelta
from typing import Optional
from auth_models import KakaoPayRequest, KakaoPayResponse, PaymentResponse, MembershipTier
from subscription_plans import get_plan

class KakaoPayService:
    def __init__(self):
        self.admin_key = os.getenv("KAKAO_ADMIN_KEY")  # 카카오페이 관리자 키
        self.base_url = "https://kapi.kakao.com"
        self.test_mode = os.getenv("KAKAO_PAY_TEST_MODE", "true").lower() == "true"
        
        if self.test_mode:
            self.cid = "TC0ONETIME"  # 테스트용 CID
        else:
            self.cid = os.getenv("KAKAO_PAY_CID")  # 실제 CID
    
    async def create_payment(
        self, 
        user_id: int, 
        plan_id: str, 
        return_url: str, 
        cancel_url: str, 
        fail_url: str
    ) -> Optional[PaymentResponse]:
        """카카오페이 결제 생성"""
        try:
            plan = get_plan(plan_id)
            if not plan:
                return None
            
            # 주문 ID 생성
            partner_order_id = f"ORDER_{user_id}_{int(datetime.now().timestamp())}"
            partner_user_id = str(user_id)
            
            # 카카오페이 결제 요청 데이터
            payment_data = {
                "cid": self.cid,
                "partner_order_id": partner_order_id,
                "partner_user_id": partner_user_id,
                "item_name": plan.name,
                "quantity": 1,
                "total_amount": plan.price,
                "tax_free_amount": 0,
                "approval_url": return_url,
                "cancel_url": cancel_url,
                "fail_url": fail_url
            }
            
            headers = {
                "Authorization": f"KakaoAK {self.admin_key}",
                "Content-Type": "application/x-www-form-urlencoded;charset=utf-8"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/v1/payment/ready",
                    data=payment_data,
                    headers=headers
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # 결제 정보 저장 (실제로는 데이터베이스에 저장)
                    payment_id = result.get("tid")
                    
                    return PaymentResponse(
                        payment_id=payment_id,
                        payment_url=result.get("next_redirect_pc_url"),
                        amount=plan.price,
                        status="ready"
                    )
                else:
                    print(f"카카오페이 결제 생성 실패: {response.status_code}, {response.text}")
                    return None
                    
        except Exception as e:
            print(f"카카오페이 결제 생성 오류: {e}")
            return None
    
    async def approve_payment(
        self, 
        payment_id: str, 
        pg_token: str, 
        user_id: int, 
        plan_id: str
    ) -> Optional[dict]:
        """카카오페이 결제 승인"""
        try:
            plan = get_plan(plan_id)
            if not plan:
                return None
            
            partner_order_id = f"ORDER_{user_id}_{int(datetime.now().timestamp())}"
            partner_user_id = str(user_id)
            
            approval_data = {
                "cid": self.cid,
                "tid": payment_id,
                "partner_order_id": partner_order_id,
                "partner_user_id": partner_user_id,
                "pg_token": pg_token
            }
            
            headers = {
                "Authorization": f"KakaoAK {self.admin_key}",
                "Content-Type": "application/x-www-form-urlencoded;charset=utf-8"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/v1/payment/approve",
                    data=approval_data,
                    headers=headers
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # 결제 성공 시 구독 정보 업데이트
                    subscription_data = {
                        "user_id": user_id,
                        "plan_id": plan_id,
                        "payment_id": payment_id,
                        "amount": result.get("amount", {}).get("total"),
                        "status": "approved",
                        "expires_at": datetime.now() + timedelta(days=plan.duration_days)
                    }
                    
                    return subscription_data
                else:
                    print(f"카카오페이 결제 승인 실패: {response.status_code}, {response.text}")
                    return None
                    
        except Exception as e:
            print(f"카카오페이 결제 승인 오류: {e}")
            return None
    
    async def cancel_payment(self, payment_id: str, cancel_amount: int) -> bool:
        """카카오페이 결제 취소"""
        try:
            cancel_data = {
                "cid": self.cid,
                "tid": payment_id,
                "cancel_amount": cancel_amount,
                "cancel_tax_free_amount": 0
            }
            
            headers = {
                "Authorization": f"KakaoAK {self.admin_key}",
                "Content-Type": "application/x-www-form-urlencoded;charset=utf-8"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/v1/payment/cancel",
                    data=cancel_data,
                    headers=headers
                )
                
                return response.status_code == 200
                
        except Exception as e:
            print(f"카카오페이 결제 취소 오류: {e}")
            return False

# 전역 인스턴스
kakao_pay_service = KakaoPayService()

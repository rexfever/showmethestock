"""
결제 API 엔드포인트
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import RedirectResponse
from payment_service import kakao_pay_service
from naver_pay_service import naver_pay_service
from portone_service import portone_service
from toss_service import toss_service
from auth_service import get_current_user
from subscription_service import subscription_service

router = APIRouter()

@router.post("/payment/kakao/create")
async def create_kakao_payment(
    plan_id: str,
    current_user = Depends(get_current_user)
):
    """카카오페이 결제 생성"""
    try:
        return_url = f"{request.base_url}payment/kakao/success"
        cancel_url = f"{request.base_url}payment/cancel"
        fail_url = f"{request.base_url}payment/fail"
        
        payment = await kakao_pay_service.create_payment(
            user_id=current_user.id,
            plan_id=plan_id,
            return_url=return_url,
            cancel_url=cancel_url,
            fail_url=fail_url
        )
        
        if not payment:
            raise HTTPException(status_code=400, detail="결제 생성 실패")
        
        return payment
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/payment/naver/create")
async def create_naver_payment(
    plan_id: str,
    current_user = Depends(get_current_user)
):
    """네이버페이 결제 생성"""
    try:
        return_url = f"{request.base_url}payment/naver/success"
        cancel_url = f"{request.base_url}payment/cancel"
        
        payment = await naver_pay_service.create_payment(
            user_id=current_user.id,
            plan_id=plan_id,
            return_url=return_url,
            cancel_url=cancel_url
        )
        
        if not payment:
            raise HTTPException(status_code=400, detail="결제 생성 실패")
        
        return payment
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/payment/kakao/success")
async def kakao_payment_success(
    pg_token: str,
    payment_id: str,
    plan_id: str,
    current_user = Depends(get_current_user)
):
    """카카오페이 결제 성공 처리"""
    try:
        result = await kakao_pay_service.approve_payment(
            payment_id=payment_id,
            pg_token=pg_token,
            user_id=current_user.id,
            plan_id=plan_id
        )
        
        if result:
            # 구독 정보 업데이트
            await subscription_service.create_subscription(result)
            return RedirectResponse(url="/payment/success")
        else:
            return RedirectResponse(url="/payment/fail")
    except Exception as e:
        return RedirectResponse(url="/payment/fail")

@router.get("/payment/naver/success")
async def naver_payment_success(
    payment_id: str,
    plan_id: str,
    current_user = Depends(get_current_user)
):
    """네이버페이 결제 성공 처리"""
    try:
        result = await naver_pay_service.approve_payment(
            payment_id=payment_id,
            user_id=current_user.id,
            plan_id=plan_id
        )
        
        if result:
            # 구독 정보 업데이트
            await subscription_service.create_subscription(result)
            return RedirectResponse(url="/payment/success")
        else:
            return RedirectResponse(url="/payment/fail")
    except Exception as e:
        return RedirectResponse(url="/payment/fail")

@router.get("/payment/cancel")
async def payment_cancel():
    """결제 취소"""
    return RedirectResponse(url="/subscription?status=cancel")

@router.get("/payment/fail")
async def payment_fail():
    """결제 실패"""
    return RedirectResponse(url="/subscription?status=fail")

@router.post("/payment/portone/create")
async def create_portone_payment(
    plan_id: str,
    pay_method: str = "card",
    current_user = Depends(get_current_user)
):
    """포트원 결제 생성"""
    try:
        payment = await portone_service.create_payment(
            user_id=current_user.id,
            plan_id=plan_id,
            pay_method=pay_method
        )
        
        if not payment:
            raise HTTPException(status_code=400, detail="결제 생성 실패")
        
        return payment
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/payment/portone/verify")
async def verify_portone_payment(
    imp_uid: str,
    merchant_uid: str,
    current_user = Depends(get_current_user)
):
    """포트원 결제 검증"""
    try:
        result = await portone_service.verify_payment(imp_uid, merchant_uid)
        
        if result:
            # 구독 정보 업데이트
            await subscription_service.create_subscription(result)
            return {"success": True}
        else:
            raise HTTPException(status_code=400, detail="결제 검증 실패")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/payment/toss/create")
async def create_toss_payment(
    plan_id: str,
    current_user = Depends(get_current_user)
):
    """토스페이먼츠 결제 생성"""
    try:
        payment = await toss_service.create_payment(
            user_id=current_user.id,
            plan_id=plan_id
        )
        
        if not payment:
            raise HTTPException(status_code=400, detail="결제 생성 실패")
        
        return payment
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/payment/toss/confirm")
async def confirm_toss_payment(
    payment_key: str,
    order_id: str,
    amount: int,
    current_user = Depends(get_current_user)
):
    """토스페이먼츠 결제 승인"""
    try:
        result = await toss_service.confirm_payment(payment_key, order_id, amount)
        
        if result:
            # 구독 정보 업데이트
            await subscription_service.create_subscription(result)
            return {"success": True}
        else:
            raise HTTPException(status_code=400, detail="결제 승인 실패")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
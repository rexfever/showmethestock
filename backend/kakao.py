import os
import json
import requests
from datetime import datetime

SOLAPI_API_BASE = os.getenv('SOLAPI_API_BASE', 'https://api.solapi.com')
SOLAPI_API_KEY = os.getenv('SOLAPI_API_KEY', '섭')
SOLAPI_API_SECRET = os.getenv('SOLAPI_API_SECRET', '')
SOLAPI_PF_ID = os.getenv('SOLAPI_PF_ID', '')
SOLAPI_TEMPLATE_ID = os.getenv('SOLAPI_TEMPLATE_ID', '')


def format_scan_message(items, matched_count, top_n=5):
    tops = items[:top_n]
    lines = [f"매칭 {matched_count}건"]
    for it in tops:
        name = it.name
        code = it.ticker
        score = int(it.score)
        strat = it.strategy
        lines.append(f"{name}({code}) 점수 {score} · {strat}")
    return "\n".join(lines)


def format_scan_alert_message(matched_count: int, scan_date: str = None, user_name: str = None) -> dict:
    """스캔 결과 알림톡 메시지 포맷팅 (솔라피 템플릿 변수 사용)"""
    if scan_date is None:
        scan_date = datetime.now().strftime("%Y년 %m월 %d일")
    
    if user_name is None:
        user_name = "고객님"
    
    # 솔라피 알림톡 템플릿 변수 사용 (#{변수명} 형식)
    template_data = {
        "#{s_date}": scan_date,
        "#{s_num}": str(matched_count),
        "#{c_name}": user_name
    }
    
    return template_data


def send_alert(to: str, template_data: dict, template_id: str = None) -> dict:
    """솔라피 알림톡 발송"""
    if not SOLAPI_API_KEY:
        # 임시: 콘솔 출력으로 테스트
        print(f"솔라피 알림톡 발송 테스트:")
        print(f"수신자: {to}")
        print(f"템플릿 변수: {template_data}")
        return {"ok": True, "response": {"test": True, "message": "콘솔 출력으로 테스트 완료"}}
    
    # 기본 템플릿 ID
    if template_id is None:
        template_id = SOLAPI_TEMPLATE_ID
    
    url = f"{SOLAPI_API_BASE}/messages/v4/send"
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": f"HMAC-SHA256 {SOLAPI_API_KEY}",
    }
    
    # 솔라피 알림톡 페이로드
    payload = {
        "message": {
            "to": to,
            "from": "010-4220-0956",  # 발신번호
            "type": "ATA",  # 알림톡
            "kakaoOptions": {
                "pfId": SOLAPI_PF_ID,  # 환경변수에서 채널 ID
                "templateId": template_id,  # 환경변수에서 템플릿 ID
                "variables": template_data
            }
        }
    }
    
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        ok = resp.ok
        data = {}
        try:
            data = resp.json()
        except Exception:
            data = {"status_code": resp.status_code, "text": resp.text[:200]}
        return {"ok": ok, "response": data}
    except Exception as e:
        return {"ok": False, "error": str(e)}

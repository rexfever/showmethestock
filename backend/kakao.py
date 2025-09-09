import os
import json
import requests
from datetime import datetime

SOLAPI_API_BASE = os.getenv('SOLAPI_API_BASE', 'https://api.solapi.com')
SOLAPI_API_KEY = os.getenv('SOLAPI_API_KEY', '')
SOLAPI_API_SECRET = os.getenv('SOLAPI_API_SECRET', '')


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


def format_scan_alert_message(matched_count: int, scan_date: str = None, user_name: str = None) -> str:
    """스캔 결과 알림톡 메시지 포맷팅 (고객용 스캔 화면 링크 포함)"""
    if scan_date is None:
        scan_date = datetime.now().strftime("%Y년 %m월 %d일")
    
    # 기본 템플릿 사용
    message = f"""📊 스톡인사이트 일일 스캔 결과

안녕하세요! 오늘의 주식 스캔 결과를 알려드립니다.

🎯 매칭 종목: {matched_count}개
📈 강한 매수 신호 종목들이 발견되었습니다!

상세 정보는 아래 링크에서 확인하세요:
🔗 https://sohntech.ai.kr/customer-scanner

스톡인사이트"""
    
    return message


def send_alert(to: str, message: str) -> dict:
    if not SOLAPI_API_KEY:
        # 임시: 콘솔 출력으로 테스트
        print(f"카카오 알림톡 발송 테스트:")
        print(f"수신자: {to}")
        print(f"메시지: {message}")
        return {"ok": True, "response": {"test": True, "message": "콘솔 출력으로 테스트 완료"}}
    
    url = f"{SOLAPI_API_BASE}/messages/v4/send"
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": f"HMAC-SHA256 {SOLAPI_API_KEY}",
    }
    payload = {
        "message": {
            "to": to,
            "from": "010-4220-0956",  # 발신번호
            "text": message,
            "type": "ATA",  # 알림톡
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

import os
import json
import requests
from datetime import datetime

KAKAO_API_BASE = os.getenv('KAKAO_API_BASE', 'https://api.solapi.com')
KAKAO_API_KEY = os.getenv('KAKAO_API_KEY', '')
KAKAO_SENDER_KEY = os.getenv('KAKAO_SENDER_KEY', '')
KAKAO_TEMPLATE_ID = os.getenv('KAKAO_TEMPLATE_ID', '')


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


def send_alert(to: str, message: str) -> dict:
    if not (KAKAO_API_KEY and KAKAO_SENDER_KEY and KAKAO_TEMPLATE_ID):
        return {"ok": False, "error": "kakao env not set"}
    url = f"{KAKAO_API_BASE}/messages/v4/send"
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": f"HMAC-SHA256 {KAKAO_API_KEY}",
    }
    payload = {
        "messageType": "ATA",
        "senderKey": KAKAO_SENDER_KEY,
        "templateId": KAKAO_TEMPLATE_ID,
        "recipientList": [
            {
                "recipientNo": to,
                "templateParameter": {
                    "content": message,
                },
            }
        ],
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

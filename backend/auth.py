import time
import requests
from typing import Optional
from config import config


class KiwoomAuth:
    """키움 REST OAuth 토큰 발급/캐시/갱신"""

    def __init__(self):
        self._access_token: Optional[str] = None
        self._expires_at: float = 0.0

    def get_access_token(self) -> str:
        now = time.time()
        if self._access_token and now < self._expires_at - 30:
            return self._access_token

        url = f"{config.api_base}/oauth2/token"
        data = {
            "grant_type": "client_credentials",
            "appkey": config.app_key,
            "secretkey": config.app_secret,
        }
        headers = {"Content-Type": "application/json;charset=UTF-8"}
        resp = requests.post(url, json=data, headers=headers, timeout=10)
        resp.raise_for_status()
        payload = resp.json()

        if payload.get("return_code") != 0:
            raise RuntimeError(f"Token error: {payload}")

        token = payload.get("token")
        expires_dt = payload.get("expires_dt")  # 'YYYYMMDDHHMMSS'
        # 간단히 1시간 유효로 처리 (문자열 파싱 대신 안전한 버퍼)
        self._access_token = token
        self._expires_at = now + 3600
        return token

    def auth_headers(self, api_id: str) -> dict:
        return {
            "api-id": api_id,
            "authorization": f"Bearer {self.get_access_token()}",
            "Content-Type": "application/json;charset=UTF-8",
        }



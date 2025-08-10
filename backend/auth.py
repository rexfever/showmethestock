import time
import requests
from typing import Optional
from backend.config import config


class KiwoomAuth:
    """키움 REST OAuth 토큰 발급/캐시/갱신"""

    def __init__(self):
        self._access_token: Optional[str] = None
        self._expires_at: float = 0.0

    def get_access_token(self) -> str:
        now = time.time()
        if self._access_token and now < self._expires_at - 30:
            return self._access_token

        url = f"{config.api_base}{config.token_path}"
        # 키움 REST 토큰(JSON, secretkey)
        data = {
            "grant_type": "client_credentials",
            "appkey": config.app_key,
            "secretkey": config.app_secret,
        }
        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "api-id": "au10001",
        }
        resp = requests.post(url, json=data, headers=headers, timeout=10)
        try:
            resp.raise_for_status()
        except Exception:
            try:
                payload = resp.json()
            except Exception:
                payload = {"status_code": resp.status_code, "text": resp.text[:200]}
            raise RuntimeError(f"Token HTTP error: {payload}")
        payload = resp.json()

        # 키움 응답 예: {"return_code":0, "token":"..."}
        rc = payload.get("return_code")
        if rc not in (0, "0"):
            raise RuntimeError(f"Token error: {payload}")
        token = payload.get("token") or payload.get("access_token")
        if not token:
            raise RuntimeError(f"Token error: {payload}")
        self._access_token = token
        self._expires_at = now + 3600
        return token

    def auth_headers(self, api_id: str) -> dict:
        # 키움 REST 헤더 규격
        return {
            "api-id": api_id,
            "authorization": f"Bearer {self.get_access_token()}",
            "Content-Type": "application/json;charset=UTF-8",
        }



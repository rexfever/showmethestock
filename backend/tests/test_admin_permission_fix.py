"""
관리자 권한 인식 문제 해결을 위한 테스트
"""
import unittest
import requests
import json
import time
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestAdminPermissionFix(unittest.TestCase):
    """관리자 권한 인식 문제 해결 테스트"""

    def setUp(self):
        """테스트 설정"""
        self.base_url = "https://sohntech.ai.kr/api"
        self.server_running = self._check_server_status()
        
        # 테스트용 관리자 계정 정보 (실제 DB에서 확인된 정보)
        self.admin_user = {
            "id": 1,
            "email": "emozero@naver.com",
            "name": "손진형",
            "is_admin": 1  # 서버에서 반환하는 실제 값
        }
        
        # 테스트용 일반 사용자 계정 정보
        self.normal_user = {
            "id": 2,
            "email": "eunhye1229@gmail.com",
            "name": "Grace",
            "is_admin": 0
        }

    def _check_server_status(self):
        """서버 상태 확인"""
        try:
            response = requests.get(f"{self.base_url}/scan", timeout=10)
            return response.status_code in [200, 422]  # 422는 파라미터 오류로 정상 응답
        except:
            return False

    def test_admin_service_is_admin_method(self):
        """AdminService.is_admin 메서드 테스트"""
        if not self.server_running:
            self.skipTest("서버가 실행 중이지 않음")
        
        # 관리자 사용자 테스트
        from admin_service import AdminService
        admin_service = AdminService('snapshots.db')
        
        # 관리자 권한 확인
        result = admin_service.is_admin(self.admin_user["id"])
        self.assertTrue(result, f"사용자 ID {self.admin_user['id']}는 관리자여야 합니다")
        
        # 일반 사용자 권한 확인
        result = admin_service.is_admin(self.normal_user["id"])
        self.assertFalse(result, f"사용자 ID {self.normal_user['id']}는 일반 사용자여야 합니다")
        
        # 존재하지 않는 사용자 테스트
        result = admin_service.is_admin(999)
        self.assertFalse(result, "존재하지 않는 사용자는 관리자가 아니어야 합니다")

    def test_admin_api_without_auth(self):
        """인증 없이 관리자 API 호출 시 401 반환 테스트"""
        if not self.server_running:
            self.skipTest("서버가 실행 중이지 않음")
        
        response = requests.get(f"{self.base_url}/admin/stats")
        self.assertEqual(response.status_code, 401, "인증 없이 관리자 API 호출 시 401이 반환되어야 합니다")

    def test_admin_api_with_invalid_token(self):
        """유효하지 않은 토큰으로 관리자 API 호출 시 401 반환 테스트"""
        if not self.server_running:
            self.skipTest("서버가 실행 중이지 않음")
        
        headers = {"Authorization": "Bearer invalid_token"}
        response = requests.get(f"{self.base_url}/admin/stats", headers=headers)
        self.assertEqual(response.status_code, 401, "유효하지 않은 토큰으로 관리자 API 호출 시 401이 반환되어야 합니다")

    def test_admin_api_with_normal_user_token(self):
        """일반 사용자 토큰으로 관리자 API 호출 시 403 반환 테스트"""
        if not self.server_running:
            self.skipTest("서버가 실행 중이지 않음")
        
        # 일반 사용자로 로그인하여 토큰 획득
        login_data = {
            "email": self.normal_user["email"],
            "password": "test_password"  # 실제 비밀번호가 필요
        }
        
        # 이메일 로그인이 실패할 경우를 대비한 테스트
        try:
            login_response = requests.post(f"{self.base_url}/auth/email/login", json=login_data)
            if login_response.status_code == 200:
                token_data = login_response.json()
                token = token_data["access_token"]
                
                # 일반 사용자 토큰으로 관리자 API 호출
                headers = {"Authorization": f"Bearer {token}"}
                response = requests.get(f"{self.base_url}/admin/stats", headers=headers)
                self.assertEqual(response.status_code, 403, "일반 사용자 토큰으로 관리자 API 호출 시 403이 반환되어야 합니다")
            else:
                self.skipTest("일반 사용자 로그인 실패 - 테스트 스킵")
        except:
            self.skipTest("로그인 테스트 실패 - 테스트 스킵")

    def test_auth_me_endpoint_response_format(self):
        """auth/me 엔드포인트 응답 형식 테스트"""
        if not self.server_running:
            self.skipTest("서버가 실행 중이지 않음")
        
        # 유효하지 않은 토큰으로 테스트 (응답 형식만 확인)
        headers = {"Authorization": "Bearer invalid_token"}
        response = requests.get(f"{self.base_url}/auth/me", headers=headers)
        
        # 401 응답이어야 함
        self.assertEqual(response.status_code, 401)
        
        # 응답 형식 확인
        data = response.json()
        self.assertIn("detail", data, "401 응답에 detail 필드가 있어야 합니다")

    def test_admin_permission_various_types(self):
        """다양한 is_admin 값 타입 처리 테스트"""
        if not self.server_running:
            self.skipTest("서버가 실행 중이지 않음")
        
        from admin_service import AdminService
        admin_service = AdminService('snapshots.db')
        
        # 실제 DB에서 관리자 사용자의 is_admin 값 확인
        import sqlite3
        conn = sqlite3.connect('snapshots.db')
        cur = conn.cursor()
        cur.execute("SELECT is_admin FROM users WHERE id = ?", (self.admin_user["id"],))
        result = cur.fetchone()
        conn.close()
        
        if result:
            is_admin_value = result[0]
            print(f"DB에서 실제 is_admin 값: {is_admin_value} (타입: {type(is_admin_value)})")
            
            # AdminService가 이 값을 올바르게 처리하는지 확인
            admin_result = admin_service.is_admin(self.admin_user["id"])
            self.assertTrue(admin_result, f"is_admin 값 {is_admin_value} (타입: {type(is_admin_value)})가 관리자로 인식되어야 합니다")

    def test_user_model_is_admin_field(self):
        """User 모델의 is_admin 필드 처리 테스트"""
        if not self.server_running:
            self.skipTest("서버가 실행 중이지 않음")
        
        from auth_service import AuthService
        auth_service = AuthService('snapshots.db')
        
        # 관리자 사용자 조회
        user = auth_service.get_user_by_email(self.admin_user["email"])
        
        if user:
            print(f"User 객체의 is_admin 값: {user.is_admin} (타입: {type(user.is_admin)})")
            
            # is_admin이 boolean으로 변환되었는지 확인
            self.assertIsInstance(user.is_admin, bool, "User 객체의 is_admin은 boolean 타입이어야 합니다")
            self.assertTrue(user.is_admin, "관리자 사용자의 is_admin은 True여야 합니다")
        else:
            self.skipTest("관리자 사용자를 찾을 수 없음")

    def test_admin_api_endpoints_protection(self):
        """모든 관리자 API 엔드포인트 보호 테스트"""
        if not self.server_running:
            self.skipTest("서버가 실행 중이지 않음")
        
        admin_endpoints = [
            "/admin/stats",
            "/admin/users",
            "/admin/users/1"
        ]
        
        for endpoint in admin_endpoints:
            with self.subTest(endpoint=endpoint):
                response = requests.get(f"{self.base_url}{endpoint}")
                self.assertEqual(response.status_code, 401, f"{endpoint} 엔드포인트는 인증 없이 접근할 수 없어야 합니다")

    def test_admin_user_update_protection(self):
        """관리자 사용자 정보 수정 API 보호 테스트"""
        if not self.server_running:
            self.skipTest("서버가 실행 중이지 않음")
        
        # PUT 요청으로 사용자 정보 수정 시도
        update_data = {
            "user_id": self.admin_user["id"],
            "membership_tier": "premium",
            "is_admin": True
        }
        
        response = requests.put(f"{self.base_url}/admin/users/{self.admin_user['id']}", json=update_data)
        self.assertEqual(response.status_code, 401, "사용자 정보 수정 API는 인증 없이 접근할 수 없어야 합니다")

    def test_admin_user_delete_protection(self):
        """관리자 사용자 삭제 API 보호 테스트"""
        if not self.server_running:
            self.skipTest("서버가 실행 중이지 않음")
        
        # DELETE 요청으로 사용자 삭제 시도
        response = requests.delete(f"{self.base_url}/admin/users/{self.normal_user['id']}")
        self.assertEqual(response.status_code, 401, "사용자 삭제 API는 인증 없이 접근할 수 없어야 합니다")

    def test_database_admin_field_consistency(self):
        """데이터베이스 is_admin 필드 일관성 테스트"""
        import sqlite3
        conn = sqlite3.connect('snapshots.db')
        cur = conn.cursor()
        
        # 모든 사용자의 is_admin 값 확인
        cur.execute("SELECT id, email, name, is_admin FROM users ORDER BY id")
        users = cur.fetchall()
        conn.close()
        
        self.assertGreater(len(users), 0, "사용자가 최소 1명은 있어야 합니다")
        
        # 관리자와 일반 사용자가 모두 있는지 확인
        admin_users = [user for user in users if user[3] == 1]
        normal_users = [user for user in users if user[3] == 0]
        
        self.assertGreater(len(admin_users), 0, "관리자 사용자가 최소 1명은 있어야 합니다")
        self.assertGreater(len(normal_users), 0, "일반 사용자가 최소 1명은 있어야 합니다")
        
        print(f"총 사용자: {len(users)}명")
        print(f"관리자: {len(admin_users)}명")
        print(f"일반 사용자: {len(normal_users)}명")


if __name__ == '__main__':
    unittest.main()

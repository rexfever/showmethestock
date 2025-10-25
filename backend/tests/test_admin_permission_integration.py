"""
관리자 권한 인식 문제 해결 통합 테스트
"""
import unittest
import requests
import json
import time
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestAdminPermissionIntegration(unittest.TestCase):
    """관리자 권한 인식 문제 해결 통합 테스트"""

    def setUp(self):
        """테스트 설정"""
        self.base_url = "https://sohntech.ai.kr/api"
        self.server_running = self._check_server_status()
        
        # 실제 DB에서 확인된 사용자 정보
        self.test_users = {
            "admin": {
                "id": 1,
                "email": "emozero@naver.com",
                "name": "손진형",
                "is_admin": 1
            },
            "normal": {
                "id": 2,
                "email": "eunhye1229@gmail.com",
                "name": "Grace",
                "is_admin": 0
            }
        }

    def _check_server_status(self):
        """서버 상태 확인"""
        try:
            response = requests.get(f"{self.base_url}/scan", timeout=10)
            return response.status_code in [200, 422]
        except:
            return False

    def test_admin_service_and_api_consistency(self):
        """AdminService와 API 응답 일관성 테스트"""
        if not self.server_running:
            self.skipTest("서버가 실행 중이지 않음")
        
        from admin_service import AdminService
        admin_service = AdminService('snapshots.db')
        
        # AdminService로 관리자 권한 확인
        admin_service_result = admin_service.is_admin(self.test_users["admin"]["id"])
        self.assertTrue(admin_service_result, "AdminService가 관리자를 올바르게 인식해야 합니다")
        
        # AdminService로 일반 사용자 권한 확인
        normal_service_result = admin_service.is_admin(self.test_users["normal"]["id"])
        self.assertFalse(normal_service_result, "AdminService가 일반 사용자를 올바르게 인식해야 합니다")

    def test_auth_service_user_model_consistency(self):
        """AuthService User 모델과 DB 일관성 테스트"""
        if not self.server_running:
            self.skipTest("서버가 실행 중이지 않음")
        
        from auth_service import AuthService
        auth_service = AuthService('snapshots.db')
        
        # 관리자 사용자 조회
        admin_user = auth_service.get_user_by_email(self.test_users["admin"]["email"])
        self.assertIsNotNone(admin_user, "관리자 사용자를 찾을 수 있어야 합니다")
        self.assertTrue(admin_user.is_admin, "AuthService가 관리자의 is_admin을 True로 반환해야 합니다")
        self.assertIsInstance(admin_user.is_admin, bool, "is_admin은 boolean 타입이어야 합니다")
        
        # 일반 사용자 조회
        normal_user = auth_service.get_user_by_email(self.test_users["normal"]["email"])
        self.assertIsNotNone(normal_user, "일반 사용자를 찾을 수 있어야 합니다")
        self.assertFalse(normal_user.is_admin, "AuthService가 일반 사용자의 is_admin을 False로 반환해야 합니다")
        self.assertIsInstance(normal_user.is_admin, bool, "is_admin은 boolean 타입이어야 합니다")

    def test_database_admin_field_types(self):
        """데이터베이스 is_admin 필드 타입 테스트"""
        import sqlite3
        conn = sqlite3.connect('snapshots.db')
        cur = conn.cursor()
        
        # 관리자 사용자의 is_admin 값 확인
        cur.execute("SELECT is_admin FROM users WHERE id = ?", (self.test_users["admin"]["id"],))
        admin_result = cur.fetchone()
        
        # 일반 사용자의 is_admin 값 확인
        cur.execute("SELECT is_admin FROM users WHERE id = ?", (self.test_users["normal"]["id"],))
        normal_result = cur.fetchone()
        
        conn.close()
        
        self.assertIsNotNone(admin_result, "관리자 사용자의 is_admin 값을 찾을 수 있어야 합니다")
        self.assertIsNotNone(normal_result, "일반 사용자의 is_admin 값을 찾을 수 있어야 합니다")
        
        admin_value = admin_result[0]
        normal_value = normal_result[0]
        
        print(f"DB 관리자 is_admin 값: {admin_value} (타입: {type(admin_value)})")
        print(f"DB 일반 사용자 is_admin 값: {normal_value} (타입: {type(normal_value)})")
        
        # 값이 예상대로인지 확인
        self.assertEqual(admin_value, 1, "관리자의 is_admin은 1이어야 합니다")
        self.assertEqual(normal_value, 0, "일반 사용자의 is_admin은 0이어야 합니다")

    def test_frontend_permission_logic_with_real_data(self):
        """실제 데이터로 프론트엔드 권한 체크 로직 테스트"""
        # 실제 서버에서 반환하는 데이터 시뮬레이션
        real_admin_data = {
            "id": self.test_users["admin"]["id"],
            "email": self.test_users["admin"]["email"],
            "name": self.test_users["admin"]["name"],
            "is_admin": 1  # 서버에서 실제로 반환하는 값
        }
        
        real_normal_data = {
            "id": self.test_users["normal"]["id"],
            "email": self.test_users["normal"]["email"],
            "name": self.test_users["normal"]["name"],
            "is_admin": 0  # 서버에서 실제로 반환하는 값
        }
        
        # 개선된 프론트엔드 권한 체크 로직
        def check_admin_permission(user):
            return user and (
                user.get("is_admin") == True or 
                user.get("is_admin") == 1 or 
                user.get("is_admin") == "1" or
                user.get("is_admin") == "true"
            )
        
        # 관리자 권한 체크
        admin_result = check_admin_permission(real_admin_data)
        self.assertTrue(admin_result, "실제 관리자 데이터로 권한 체크가 성공해야 합니다")
        
        # 일반 사용자 권한 체크
        normal_result = check_admin_permission(real_normal_data)
        self.assertFalse(normal_result, "실제 일반 사용자 데이터로 권한 체크가 실패해야 합니다")

    def test_admin_api_endpoints_protection_integration(self):
        """관리자 API 엔드포인트 보호 통합 테스트"""
        if not self.server_running:
            self.skipTest("서버가 실행 중이지 않음")
        
        admin_endpoints = [
            ("GET", "/admin/stats"),
            ("GET", "/admin/users"),
            ("GET", f"/admin/users/{self.test_users['admin']['id']}"),
            ("PUT", f"/admin/users/{self.test_users['normal']['id']}"),
            ("DELETE", f"/admin/users/{self.test_users['normal']['id']}")
        ]
        
        for method, endpoint in admin_endpoints:
            with self.subTest(endpoint=f"{method} {endpoint}"):
                if method == "GET":
                    response = requests.get(f"{self.base_url}{endpoint}")
                elif method == "PUT":
                    response = requests.put(f"{self.base_url}{endpoint}", json={"test": "data"})
                elif method == "DELETE":
                    response = requests.delete(f"{self.base_url}{endpoint}")
                
                self.assertEqual(response.status_code, 401, f"{method} {endpoint}는 인증 없이 접근할 수 없어야 합니다")

    def test_admin_permission_edge_cases_integration(self):
        """관리자 권한 경계값 통합 테스트"""
        if not self.server_running:
            self.skipTest("서버가 실행 중이지 않음")
        
        from admin_service import AdminService
        admin_service = AdminService('snapshots.db')
        
        # 존재하지 않는 사용자 ID 테스트
        result = admin_service.is_admin(99999)
        self.assertFalse(result, "존재하지 않는 사용자 ID는 관리자가 아니어야 합니다")
        
        # 음수 사용자 ID 테스트
        result = admin_service.is_admin(-1)
        self.assertFalse(result, "음수 사용자 ID는 관리자가 아니어야 합니다")
        
        # 0 사용자 ID 테스트
        result = admin_service.is_admin(0)
        self.assertFalse(result, "0 사용자 ID는 관리자가 아니어야 합니다")

    def test_admin_permission_performance_integration(self):
        """관리자 권한 체크 성능 통합 테스트"""
        if not self.server_running:
            self.skipTest("서버가 실행 중이지 않음")
        
        from admin_service import AdminService
        admin_service = AdminService('snapshots.db')
        
        iterations = 1000
        admin_id = self.test_users["admin"]["id"]
        
        # AdminService 성능 테스트
        start_time = time.time()
        for _ in range(iterations):
            result = admin_service.is_admin(admin_id)
        end_time = time.time()
        
        execution_time = end_time - start_time
        print(f"AdminService.is_admin {iterations}회 실행 시간: {execution_time:.4f}초")
        
        # 성능이 합리적인 범위 내에 있는지 확인
        self.assertLess(execution_time, 5.0, "AdminService 권한 체크가 너무 느립니다")
        self.assertTrue(result, "성능 테스트 중에도 올바른 결과를 반환해야 합니다")

    def test_admin_permission_data_consistency(self):
        """관리자 권한 데이터 일관성 테스트"""
        if not self.server_running:
            self.skipTest("서버가 실행 중이지 않음")
        
        import sqlite3
        from admin_service import AdminService
        from auth_service import AuthService
        
        admin_service = AdminService('snapshots.db')
        auth_service = AuthService('snapshots.db')
        
        # DB 직접 조회
        conn = sqlite3.connect('snapshots.db')
        cur = conn.cursor()
        cur.execute("SELECT id, email, is_admin FROM users ORDER BY id")
        db_users = cur.fetchall()
        conn.close()
        
        # 각 사용자에 대해 일관성 확인
        for user_id, email, db_is_admin in db_users:
            with self.subTest(user_id=user_id, email=email):
                # AdminService로 확인
                admin_service_result = admin_service.is_admin(user_id)
                
                # AuthService로 확인
                auth_user = auth_service.get_user_by_email(email)
                auth_service_result = auth_user.is_admin if auth_user else False
                
                # DB 값과 서비스 결과 일치 확인
                expected_admin = db_is_admin == 1
                
                self.assertEqual(admin_service_result, expected_admin, 
                    f"사용자 {user_id}({email}): AdminService 결과가 DB와 일치해야 합니다")
                
                self.assertEqual(auth_service_result, expected_admin, 
                    f"사용자 {user_id}({email}): AuthService 결과가 DB와 일치해야 합니다")
                
                self.assertEqual(admin_service_result, auth_service_result, 
                    f"사용자 {user_id}({email}): AdminService와 AuthService 결과가 일치해야 합니다")

    def test_admin_permission_error_handling(self):
        """관리자 권한 체크 오류 처리 테스트"""
        if not self.server_running:
            self.skipTest("서버가 실행 중이지 않음")
        
        from admin_service import AdminService
        admin_service = AdminService('snapshots.db')
        
        # 잘못된 DB 경로로 AdminService 생성
        invalid_admin_service = AdminService('invalid_db_path.db')
        
        # 잘못된 DB로 권한 체크 시도
        result = invalid_admin_service.is_admin(1)
        self.assertFalse(result, "잘못된 DB 경로로 권한 체크 시 False를 반환해야 합니다")
        
        # None 값으로 권한 체크 시도
        result = admin_service.is_admin(None)
        self.assertFalse(result, "None 값으로 권한 체크 시 False를 반환해야 합니다")


if __name__ == '__main__':
    unittest.main()

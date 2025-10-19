#!/usr/bin/env python3
"""
포트폴리오 확장 기능 통합 테스트
- 백엔드 API 테스트
- 프론트엔드 테스트
- 전체 시스템 통합 테스트
"""

import subprocess
import sys
import time
import requests
import json
from datetime import datetime


class PortfolioIntegrationTest:
    """포트폴리오 통합 테스트"""
    
    def __init__(self):
        self.backend_url = "http://localhost:8010"
        self.frontend_url = "http://localhost:3000"
        self.test_token = None
        
    def run_command(self, command, cwd=None):
        """명령어 실행"""
        try:
            result = subprocess.run(
                command, 
                shell=True, 
                cwd=cwd, 
                capture_output=True, 
                text=True, 
                timeout=30
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", "Command timed out"
    
    def wait_for_service(self, url, timeout=30):
        """서비스 시작 대기"""
        print(f"⏳ {url} 서비스 시작 대기 중...")
        
        for i in range(timeout):
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    print(f"✅ {url} 서비스 준비 완료")
                    return True
            except requests.exceptions.RequestException:
                pass
            
            time.sleep(1)
            print(f"   대기 중... ({i+1}/{timeout})")
        
        print(f"❌ {url} 서비스 시작 실패")
        return False
    
    def test_backend_health(self):
        """백엔드 헬스 체크"""
        print("🧪 백엔드 헬스 체크 테스트")
        
        try:
            response = requests.get(f"{self.backend_url}/health", timeout=10)
            if response.status_code == 200:
                print("✅ 백엔드 헬스 체크 통과")
                return True
            else:
                print(f"❌ 백엔드 헬스 체크 실패: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ 백엔드 연결 실패: {e}")
            return False
    
    def test_portfolio_api(self):
        """포트폴리오 API 테스트"""
        print("🧪 포트폴리오 API 테스트")
        
        try:
            # 포트폴리오 조회 (인증 없이)
            response = requests.get(f"{self.backend_url}/portfolio", timeout=10)
            
            if response.status_code in [200, 401]:  # 401은 인증 필요 (정상)
                print("✅ 포트폴리오 API 엔드포인트 정상")
                return True
            else:
                print(f"❌ 포트폴리오 API 실패: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ 포트폴리오 API 연결 실패: {e}")
            return False
    
    def test_personal_stock_api(self):
        """개인 종목 추가 API 테스트"""
        print("🧪 개인 종목 추가 API 테스트")
        
        try:
            # 개인 종목 추가 API (인증 없이)
            test_data = {
                "ticker": "035720",
                "name": "카카오",
                "entry_price": 50000,
                "quantity": 20,
                "entry_date": "2025-10-12"
            }
            
            response = requests.post(
                f"{self.backend_url}/portfolio/add-personal",
                json=test_data,
                timeout=10
            )
            
            if response.status_code in [200, 401]:  # 401은 인증 필요 (정상)
                print("✅ 개인 종목 추가 API 엔드포인트 정상")
                return True
            else:
                print(f"❌ 개인 종목 추가 API 실패: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ 개인 종목 추가 API 연결 실패: {e}")
            return False
    
    def test_frontend_access(self):
        """프론트엔드 접근 테스트"""
        print("🧪 프론트엔드 접근 테스트")
        
        try:
            response = requests.get(f"{self.frontend_url}", timeout=10)
            if response.status_code == 200:
                print("✅ 프론트엔드 접근 정상")
                return True
            else:
                print(f"❌ 프론트엔드 접근 실패: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ 프론트엔드 연결 실패: {e}")
            return False
    
    def test_portfolio_page(self):
        """포트폴리오 페이지 테스트"""
        print("🧪 포트폴리오 페이지 테스트")
        
        try:
            response = requests.get(f"{self.frontend_url}/portfolio", timeout=10)
            if response.status_code == 200:
                print("✅ 포트폴리오 페이지 접근 정상")
                return True
            else:
                print(f"❌ 포트폴리오 페이지 접근 실패: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ 포트폴리오 페이지 연결 실패: {e}")
            return False
    
    def run_backend_tests(self):
        """백엔드 단위 테스트 실행"""
        print("🧪 백엔드 단위 테스트 실행")
        
        success, stdout, stderr = self.run_command(
            "python3 test_portfolio_enhancement.py",
            cwd="backend"
        )
        
        if success:
            print("✅ 백엔드 단위 테스트 통과")
            print(stdout)
            return True
        else:
            print("❌ 백엔드 단위 테스트 실패")
            print(stderr)
            return False
    
    def run_frontend_tests(self):
        """프론트엔드 테스트 실행"""
        print("🧪 프론트엔드 테스트 실행")
        
        success, stdout, stderr = self.run_command(
            "npm test -- --testPathPattern=portfolio.test.js --watchAll=false",
            cwd="frontend"
        )
        
        if success:
            print("✅ 프론트엔드 테스트 통과")
            return True
        else:
            print("❌ 프론트엔드 테스트 실패")
            print(stderr)
            return False
    
    def run_integration_test(self):
        """통합 테스트 실행"""
        print("🚀 포트폴리오 확장 기능 통합 테스트 시작")
        print("=" * 60)
        
        test_results = []
        
        # 1. 백엔드 단위 테스트
        print("\n📦 백엔드 테스트")
        print("-" * 30)
        backend_test_result = self.run_backend_tests()
        test_results.append(("백엔드 단위 테스트", backend_test_result))
        
        # 2. 백엔드 서비스 시작 확인
        print("\n🔧 백엔드 서비스 확인")
        print("-" * 30)
        backend_health = self.test_backend_health()
        test_results.append(("백엔드 헬스 체크", backend_health))
        
        if backend_health:
            # 3. 백엔드 API 테스트
            portfolio_api = self.test_portfolio_api()
            test_results.append(("포트폴리오 API", portfolio_api))
            
            personal_api = self.test_personal_stock_api()
            test_results.append(("개인 종목 API", personal_api))
        
        # 4. 프론트엔드 서비스 시작 확인
        print("\n🎨 프론트엔드 서비스 확인")
        print("-" * 30)
        frontend_access = self.test_frontend_access()
        test_results.append(("프론트엔드 접근", frontend_access))
        
        if frontend_access:
            portfolio_page = self.test_portfolio_page()
            test_results.append(("포트폴리오 페이지", portfolio_page))
        
        # 5. 프론트엔드 테스트
        print("\n🧪 프론트엔드 테스트")
        print("-" * 30)
        frontend_test_result = self.run_frontend_tests()
        test_results.append(("프론트엔드 단위 테스트", frontend_test_result))
        
        # 결과 요약
        print("\n📊 테스트 결과 요약")
        print("=" * 60)
        
        passed = 0
        total = len(test_results)
        
        for test_name, result in test_results:
            status = "✅ 통과" if result else "❌ 실패"
            print(f"{test_name:<25} {status}")
            if result:
                passed += 1
        
        print(f"\n📈 전체 결과: {passed}/{total} 통과 ({passed/total*100:.1f}%)")
        
        if passed == total:
            print("🎉 모든 테스트 통과! 포트폴리오 확장 기능이 정상 작동합니다.")
            return True
        else:
            print("⚠️ 일부 테스트 실패. 문제를 확인하고 수정해주세요.")
            return False


def main():
    """메인 함수"""
    tester = PortfolioIntegrationTest()
    
    print("🚀 포트폴리오 확장 기능 통합 테스트")
    print(f"⏰ 테스트 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 서비스 시작 확인
    print("🔍 서비스 상태 확인 중...")
    
    backend_ready = tester.wait_for_service(tester.backend_url)
    frontend_ready = tester.wait_for_service(tester.frontend_url)
    
    if not backend_ready:
        print("❌ 백엔드 서비스가 실행되지 않았습니다.")
        print("다음 명령어로 백엔드를 시작해주세요:")
        print("  ./scripts/deploy-backend.sh")
        return False
    
    if not frontend_ready:
        print("❌ 프론트엔드 서비스가 실행되지 않았습니다.")
        print("다음 명령어로 프론트엔드를 시작해주세요:")
        print("  ./scripts/deploy-frontend.sh")
        return False
    
    # 통합 테스트 실행
    success = tester.run_integration_test()
    
    print(f"\n⏰ 테스트 완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)







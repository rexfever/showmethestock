# 서버 작업 메뉴얼

## 1. 서버 정보

### 기본 정보
- **호스트명**: ip-172-31-12-241
- **IP 주소**: 52.79.145.238
- **사용자**: ubuntu
- **홈 디렉토리**: /home/ubuntu

### SSH 접속
```bash
# SSH 설정 사용
ssh stock-finder

# 직접 접속
ssh -i ~/.ssh/id_rsa ubuntu@52.79.145.238
```

### 주요 디렉토리
```bash
/home/ubuntu/showmethestock/backend/    # 백엔드 코드
/home/ubuntu/showmethestock/frontend/   # 프론트엔드 코드
/home/ubuntu/showmethestock/backend/snapshots.db    # 메인 DB
/home/ubuntu/showmethestock/backend/portfolio.db    # 포트폴리오 DB
/home/ubuntu/showmethestock/backend/email_verifications.db  # 이메일 인증 DB
```

## 2. 작업 순서 (로컬 → 서버)

### 기본 원칙
**⚠️ 항상 로컬에서 먼저 작업하고 테스트한 후 서버에 반영**

### 작업 절차
1. **로컬 개발**
   ```bash
   # 로컬에서 코드 수정
   cd /Users/a201808029/sandbox/showmethestock
   # 코드 수정 및 테스트
   ```

2. **로컬 테스트**
   ```bash
   # 백엔드 테스트
   cd backend
   python main.py
   
   # 프론트엔드 테스트
   cd frontend
   npm run dev
   ```

3. **서버 반영**
   ```bash
   # 파일 업로드 (scp 사용)
   scp -r backend/ stock-finder:/home/ubuntu/showmethestock/
   scp -r frontend/ stock-finder:/home/ubuntu/showmethestock/
   
   # 또는 git 사용
   ssh stock-finder "cd /home/ubuntu/showmethestock && git pull"
   ```

4. **서버 재시작 (프로세스 완전 종료 후)**
   ```bash
   # 기존 프로세스 완전 종료
   ssh stock-finder "sudo pkill -f 'python.*main.py' && sudo pkill -f 'next'"
   
   # 포트 사용 프로세스 강제 종료
   ssh stock-finder "sudo lsof -ti :8010 | xargs -r sudo kill -9"
   ssh stock-finder "sudo lsof -ti :3000 | xargs -r sudo kill -9"
   
   # 서비스 재시작
   ssh stock-finder "sudo systemctl restart backend"
   ssh stock-finder "sudo systemctl restart frontend"
   
   # 상태 확인
   ssh stock-finder "systemctl is-active backend frontend"
   ```

## 3. DB 백업 (작업 전 필수)

### 자동 백업 스크립트
```bash
# 서버에서 실행
ssh stock-finder "cd /home/ubuntu/showmethestock && ./scripts/backup-database.sh"
```

### 수동 백업
```bash
# 서버 접속
ssh stock-finder

# 백업 디렉토리 생성
mkdir -p /home/ubuntu/backups/$(date +%Y%m%d_%H%M%S)

# DB 파일 백업
cd /home/ubuntu/showmethestock/backend
cp snapshots.db /home/ubuntu/backups/$(date +%Y%m%d_%H%M%S)/
cp portfolio.db /home/ubuntu/backups/$(date +%Y%m%d_%H%M%S)/
cp email_verifications.db /home/ubuntu/backups/$(date +%Y%m%d_%H%M%S)/

# 백업 확인
ls -la /home/ubuntu/backups/$(date +%Y%m%d_%H%M%S)/
```

### 로컬로 백업 다운로드
```bash
# 로컬에서 실행
scp stock-finder:/home/ubuntu/showmethestock/backend/*.db ./backup/
```

## 4. 주요 명령어

### 서버 상태 확인
```bash
ssh stock-finder "systemctl status backend"
ssh stock-finder "systemctl status frontend"
ssh stock-finder "ps aux | grep python"
ssh stock-finder "lsof -i :8010"  # 백엔드 포트
ssh stock-finder "lsof -i :3000"  # 프론트엔드 포트
```

### 로그 확인
```bash
ssh stock-finder "tail -f /home/ubuntu/showmethestock/backend/backend.log"
ssh stock-finder "journalctl -u backend -f"
```

### DB 데이터 현황 확인
```bash
# 전체 데이터 수
ssh stock-finder "cd /home/ubuntu/showmethestock/backend && sqlite3 snapshots.db 'SELECT COUNT(*) FROM scan_rank;'"

# 날짜별 데이터 수
ssh stock-finder "cd /home/ubuntu/showmethestock/backend && sqlite3 snapshots.db 'SELECT date, COUNT(*) FROM scan_rank GROUP BY date ORDER BY date DESC LIMIT 10;'"

# 최신 스캔 데이터
ssh stock-finder "cd /home/ubuntu/showmethestock/backend && sqlite3 snapshots.db 'SELECT date, code, name, score FROM scan_rank WHERE date = (SELECT MAX(date) FROM scan_rank) ORDER BY score DESC LIMIT 5;'"

# 사용자 수
ssh stock-finder "cd /home/ubuntu/showmethestock/backend && sqlite3 snapshots.db 'SELECT COUNT(*) FROM users;'"

# 포트폴리오 수
ssh stock-finder "cd /home/ubuntu/showmethestock/backend && sqlite3 portfolio.db 'SELECT COUNT(*) FROM portfolio;'"
```

### 스캔 실행
```bash
# API를 통한 스캔
curl "https://sohntech.ai.kr/api/scan?save_snapshot=true"

# 서버에서 직접 실행
ssh stock-finder "cd /home/ubuntu/showmethestock/backend && python -c 'import requests; print(requests.get(\"http://localhost:8010/scan?save_snapshot=true\").json())'"
```

## 5. 비상 복구

### DB 복구
```bash
# 백업에서 복구
ssh stock-finder "cd /home/ubuntu/showmethestock/backend"
ssh stock-finder "cp /home/ubuntu/backups/YYYYMMDD_HHMMSS/snapshots.db ."
```

### 서비스 재시작 (완전 종료 후)
```bash
# 1단계: 기존 프로세스 완전 종료
ssh stock-finder "sudo pkill -f 'python.*main.py'"
ssh stock-finder "sudo pkill -f 'next'"

# 2단계: 포트 점유 프로세스 강제 종료
ssh stock-finder "sudo lsof -ti :8010 | xargs -r sudo kill -9"
ssh stock-finder "sudo lsof -ti :3000 | xargs -r sudo kill -9"

# 3단계: 서비스 재시작
ssh stock-finder "sudo systemctl restart backend frontend"

# 4단계: 상태 확인
ssh stock-finder "systemctl is-active backend frontend"
ssh stock-finder "curl -I http://localhost:8010"
ssh stock-finder "curl -I http://localhost:3000"
```

### 롤백
```bash
ssh stock-finder "cd /home/ubuntu/showmethestock && git reset --hard HEAD~1"
```

## 6. 주의사항

- ⚠️ **DB 작업 전 반드시 백업**
- ⚠️ **로컬 테스트 후 서버 반영**
- ⚠️ **서버 직접 수정 금지**
- ⚠️ **스케줄러 실행 시간 고려 (15:36 KST)**
- ⚠️ **백업 파일 정기 정리**

## 7. 환경 설정 및 의존성 관리

### Python 가상환경 관리
```bash
# 가상환경 활성화
ssh stock-finder "cd /home/ubuntu/showmethestock/backend && source venv_new/bin/activate"

# Python 패키지 설치
ssh stock-finder "cd /home/ubuntu/showmethestock/backend && pip install -r requirements.txt"

# Python 버전 확인
ssh stock-finder "python3 --version"
```

### Node.js 의존성 관리
```bash
# Node.js 패키지 설치
ssh stock-finder "cd /home/ubuntu/showmethestock/frontend && npm install"

# Node.js 버전 확인
ssh stock-finder "node --version && npm --version"
```

## 8. SSL 인증서 관리

### SSL 상태 확인 및 갱신
```bash
# SSL 인증서 상태 확인
ssh stock-finder "sudo certbot certificates"

# SSL 인증서 갱신 테스트
ssh stock-finder "sudo certbot renew --dry-run"

# SSL 인증서 실제 갱신
ssh stock-finder "sudo certbot renew"
```

## 9. 로그 관리 및 모니터링

### 로그 파일 관리
```bash
# 로그 파일 크기 확인
ssh stock-finder "du -h /home/ubuntu/showmethestock/backend/*.log"

# 로그 로테이션 설정 확인
ssh stock-finder "sudo logrotate -d /etc/logrotate.d/stock-finder"

# 시스템 로그 확인
ssh stock-finder "sudo tail -f /var/log/syslog"
```

### 시스템 모니터링
```bash
# 디스크 사용량 확인
ssh stock-finder "df -h"

# 메모리 사용량 확인
ssh stock-finder "free -h"

# CPU 사용량 확인
ssh stock-finder "top -bn1 | head -20"
```

## 10. 보안 및 방화벽

### 보안 상태 확인
```bash
# 방화벽 상태 확인
ssh stock-finder "sudo ufw status"

# SSH 접속 로그 확인
ssh stock-finder "sudo tail -f /var/log/auth.log"

# 포트 사용 현황 확인
ssh stock-finder "sudo netstat -tlnp"
```

## 11. 데이터베이스 고급 관리

### DB 무결성 및 최적화
```bash
# DB 무결성 검사
ssh stock-finder "cd /home/ubuntu/showmethestock/backend && sqlite3 snapshots.db 'PRAGMA integrity_check;'"

# DB 최적화 (VACUUM)
ssh stock-finder "cd /home/ubuntu/showmethestock/backend && sqlite3 snapshots.db 'VACUUM;'"

# 테이블 스키마 확인
ssh stock-finder "cd /home/ubuntu/showmethestock/backend && sqlite3 snapshots.db '.schema'"

# 인덱스 상태 확인
ssh stock-finder "cd /home/ubuntu/showmethestock/backend && sqlite3 snapshots.db '.indices'"
```

## 12. 배포 자동화

### 자동 배포 스크립트
```bash
# 백엔드 자동 배포
ssh stock-finder "cd /home/ubuntu/showmethestock && ./scripts/deploy-backend.sh"

# 프론트엔드 자동 배포
ssh stock-finder "cd /home/ubuntu/showmethestock && ./scripts/deploy-frontend.sh"

# 전체 시스템 배포
ssh stock-finder "cd /home/ubuntu/showmethestock && ./scripts/deploy-backend.sh && ./scripts/deploy-frontend.sh"
```

## 13. 알림 및 모니터링

### 알림 서비스 테스트
```bash
# 카카오 알림톡 테스트
ssh stock-finder "cd /home/ubuntu/showmethestock/backend && python -c 'from notification_service import send_kakao_message; send_kakao_message(\"테스트 메시지\")'"

# 이메일 발송 테스트
ssh stock-finder "cd /home/ubuntu/showmethestock/backend && python -c 'from email_service import send_email; send_email(\"test@example.com\", \"테스트\", \"테스트 내용\")'"
```

## 14. 백업 및 복구 고급

### 전체 시스템 백업
```bash
# 전체 프로젝트 백업
ssh stock-finder "cd /home/ubuntu && tar -czf backup_$(date +%Y%m%d_%H%M%S).tar.gz showmethestock/"

# 특정 날짜 데이터 복구
ssh stock-finder "cd /home/ubuntu/showmethestock/backend && sqlite3 snapshots.db 'SELECT * FROM scan_rank WHERE date = \"20251023\";'"

# 백업 파일 압축 해제
ssh stock-finder "cd /home/ubuntu && tar -xzf backup_YYYYMMDD_HHMMSS.tar.gz"
```

## 15. 트러블슈팅 가이드

### 서비스 문제 해결
```bash
# 서비스 시작 실패 시 로그 확인
ssh stock-finder "sudo journalctl -u stock-finder-backend --no-pager -l"
ssh stock-finder "sudo journalctl -u stock-finder-frontend --no-pager -l"

# 포트 충돌 해결
ssh stock-finder "sudo lsof -i :8010 && sudo kill -9 PID"
ssh stock-finder "sudo lsof -i :3000 && sudo kill -9 PID"

# 권한 문제 해결
ssh stock-finder "sudo chown -R ubuntu:ubuntu /home/ubuntu/showmethestock/"

# 프로세스 강제 종료
ssh stock-finder "sudo pkill -f 'python.*main.py'"
ssh stock-finder "sudo pkill -f 'next'"
```

## 16. 신규 기능 개발 가이드

### 개발 원칙
**⚠️ 모든 신규 기능은 반드시 테스트 코드를 작성하고 테스트를 통과한 후 배포**

### 테스트 코드 작성 규칙
1. **단위 테스트 (Unit Test)**
   ```bash
   # 백엔드 테스트
   cd backend
   python -m pytest tests/test_new_feature.py -v
   
   # 프론트엔드 테스트
   cd frontend
   npm test -- --testPathPattern=newFeature.test.js
   ```

2. **통합 테스트 (Integration Test)**
   ```bash
   # API 엔드포인트 테스트
   python -m pytest tests/integration/test_api_endpoints.py -v
   
   # 데이터베이스 연동 테스트
   python -m pytest tests/integration/test_database.py -v
   ```

3. **테스트 실행 절차**
   ```bash
   # 로컬에서 전체 테스트 실행
   cd backend && python -m pytest tests/ -v --cov=.
   cd frontend && npm test -- --coverage
   
   # 서버에서 테스트 실행
   ssh stock-finder "cd /home/ubuntu/showmethestock/backend && python -m pytest tests/ -v"
   ```

### 신규 기능 배포 절차
1. **로컬 개발 및 테스트**
   ```bash
   # 기능 개발
   # 테스트 코드 작성
   python -m pytest tests/test_new_feature.py -v
   ```

2. **로컬 통합 테스트**
   ```bash
   # 전체 테스트 실행
   python -m pytest tests/ -v
   npm test
   ```

3. **서버 배포 전 테스트**
   ```bash
   # 서버에서 테스트 실행
   ssh stock-finder "cd /home/ubuntu/showmethestock/backend && python -m pytest tests/ -v"
   ```

4. **배포 및 검증**
   ```bash
   # 배포
   git push origin main
   ssh stock-finder "cd /home/ubuntu/showmethestock && git pull"
   
   # 배포 후 테스트
   curl "https://sohntech.ai.kr/api/new-endpoint"
   ```

### 테스트 코드 템플릿

#### 백엔드 테스트 예시
```python
# tests/test_new_feature.py
import pytest
from unittest.mock import patch, MagicMock
from backend.new_feature import NewFeatureClass

class TestNewFeature:
    def setup_method(self):
        self.feature = NewFeatureClass()
    
    def test_feature_initialization(self):
        assert self.feature is not None
    
    @patch('backend.new_feature.external_api_call')
    def test_feature_with_mock(self, mock_api):
        mock_api.return_value = {"status": "success"}
        result = self.feature.process()
        assert result["status"] == "success"
    
    def test_feature_error_handling(self):
        with pytest.raises(ValueError):
            self.feature.process_invalid_input()
```

#### 프론트엔드 테스트 예시
```javascript
// __tests__/components/NewFeature.test.js
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import NewFeature from '../components/NewFeature';

describe('NewFeature Component', () => {
  test('renders correctly', () => {
    render(<NewFeature />);
    expect(screen.getByText('New Feature')).toBeInTheDocument();
  });
  
  test('handles user interaction', () => {
    render(<NewFeature />);
    const button = screen.getByRole('button');
    fireEvent.click(button);
    expect(screen.getByText('Clicked!')).toBeInTheDocument();
  });
});
```

## 17. 연락처 및 문서

- **서버 관리**: AWS EC2 콘솔
- **도메인**: sohntech.ai.kr
- **SSL**: Let's Encrypt (자동 갱신)
- **모니터링**: 서버 로그 및 API 응답 확인
- **테스트 커버리지**: 최소 80% 이상 유지
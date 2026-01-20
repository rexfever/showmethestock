# 배포 가이드 - 2025년 12월 5일

**배포 버전**: v1.5.0  
**배포 일시**: 2025-12-05  
**커밋**: ace298e2a

---

## 📋 변경 사항 요약

### 1. 더보기 페이지 초기화면 설정 조건부 표시
- 미국주식 메뉴 활성화 시에만 초기화면 설정 표시
- API 연동 및 조건부 렌더링 구현
- 에러 처리 개선 및 URL 중앙화

### 2. 코드 품질 개선
- HTTP 상태 체크 추가
- JSON 파싱 에러 처리
- getConfig 함수로 URL 중앙화
- menuLoading 상태 추가

### 3. 테스트 추가
- 단위 테스트 13개 작성
- 브라우저 테스트 스크립트 작성

---

## 🚀 배포 절차

### Step 1: 서버 접속 및 백업

```bash
# 서버 접속
ssh ubuntu@sohntech.ai.kr

# 현재 디렉토리로 이동
cd /home/ubuntu/showmethestock

# 데이터베이스 백업
sudo -u postgres pg_dump stockfinder > ~/backups/postgres/backup_before_20251205_$(date +%H%M%S).sql

# 백업 확인
ls -lh ~/backups/postgres/backup_before_20251205_*.sql
```

### Step 2: 코드 업데이트

```bash
# 현재 상태 확인
git status
git log --oneline -1

# 최신 코드 가져오기
git fetch origin
git pull origin main

# 업데이트 확인
git log --oneline -3
```

### Step 3: 프론트엔드 빌드 및 재시작

```bash
cd /home/ubuntu/showmethestock/frontend

# 의존성 확인 (변경사항 없으면 생략 가능)
npm ci --production=false

# 빌드
npm run build

# 서비스 재시작
sudo systemctl restart stock-finder-frontend

# 상태 확인
sleep 5
sudo systemctl status stock-finder-frontend
```

### Step 4: 기능 테스트

#### 4.1 API 테스트
```bash
# 바텀메뉴 설정 API
curl http://localhost:8010/bottom-nav-menu-items | jq '.'

# 예상 응답:
# {
#   "korean_stocks": true,
#   "us_stocks": true,
#   "stock_analysis": true,
#   "portfolio": true,
#   "more": true
# }
```

#### 4.2 브라우저 테스트
1. **더보기 페이지 접속**
   ```
   https://sohntech.ai.kr/more
   ```

2. **미국주식 메뉴 활성화 시 확인**
   - ✅ "초기화면 설정" 섹션 표시
   - ✅ "한국주식추천" 옵션 표시
   - ✅ "미국주식추천" 옵션 표시

3. **기능 테스트**
   - "한국주식추천" 클릭 → 파란색 강조
   - "미국주식추천" 클릭 → 파란색 강조
   - 페이지 새로고침 → 설정 유지 확인

4. **미국주식 메뉴 비활성화 테스트**
   - 관리자 페이지에서 미국주식 메뉴 비활성화
   - 더보기 페이지에서 초기화면 설정 숨김 확인

### Step 5: 로그 확인

```bash
# 프론트엔드 로그
sudo journalctl -u stock-finder-frontend -n 50 --no-pager

# 에러 확인
sudo journalctl -u stock-finder-frontend -n 100 --no-pager | grep -i error
```

---

## ✅ 배포 체크리스트

### 배포 전
- [ ] 로컬 테스트 완료
- [ ] 단위 테스트 통과 (13/13)
- [ ] 브라우저 테스트 완료
- [ ] 데이터베이스 백업 완료
- [ ] 배포 시간 공지 (필요시)

### 배포 중
- [ ] 코드 업데이트 완료
- [ ] 프론트엔드 빌드 성공
- [ ] 서비스 재시작 완료
- [ ] 서비스 상태 정상

### 배포 후
- [ ] API 응답 정상
- [ ] 더보기 페이지 로드 정상
- [ ] 초기화면 설정 표시/숨김 정상
- [ ] 기능 동작 정상
- [ ] 에러 로그 없음
- [ ] 성능 이슈 없음

---

## 🔄 이전 버전 대비 작업 내용

### 신규 기능
1. **초기화면 설정 조건부 표시**
   - 미국주식 메뉴 상태에 따라 동적 표시/숨김
   - API 연동으로 실시간 반영

### 개선 사항
1. **에러 처리 강화**
   - HTTP 상태 코드 체크
   - JSON 파싱 에러 처리
   - API 실패 시 안전한 기본값 설정

2. **코드 구조 개선**
   - URL 중앙화 (getConfig 함수)
   - 상태 관리 개선 (menuLoading)
   - 초기값 수정 (us_stocks: false)

3. **테스트 추가**
   - 단위 테스트 13개
   - 브라우저 테스트 스크립트

### 수정된 파일
- `frontend/pages/more.js` - 주요 로직 수정
- `frontend/__tests__/pages/more.test.js` - 테스트 추가 (신규)
- `test_more_page.sh` - 브라우저 테스트 스크립트 (신규)

---

## 🐛 알려진 이슈 및 제한사항

### 제한사항
1. **클라이언트 사이드 렌더링**
   - Next.js CSR로 인해 초기 HTML에는 동적 콘텐츠 없음
   - JavaScript 실행 후 콘텐츠 표시

2. **localStorage 의존성**
   - 초기화면 설정이 localStorage에 저장됨
   - 브라우저 쿠키/로컬 스토리지 차단 시 동작 안 함

### 알려진 이슈
- 없음

---

## 🔙 롤백 절차

문제 발생 시 이전 버전으로 롤백:

```bash
# 서버 접속
ssh ubuntu@sohntech.ai.kr
cd /home/ubuntu/showmethestock

# 이전 커밋으로 롤백
git log --oneline -5  # 이전 커밋 확인
git reset --hard 48e3f95f5  # 이전 커밋 해시

# 프론트엔드 재빌드
cd frontend
npm run build
sudo systemctl restart stock-finder-frontend

# 상태 확인
sudo systemctl status stock-finder-frontend
```

---

## 📊 성능 영향

### 예상 영향
- **API 호출**: +1회 (페이지 로드 시)
- **페이지 로드 시간**: 변화 없음 (< 100ms 추가)
- **메모리 사용**: 변화 없음

### 모니터링 항목
- API 응답 시간
- 페이지 로드 시간
- 에러 발생률

---

## 📝 배포 후 작업

### 즉시
1. 더보기 페이지 기능 테스트
2. 에러 로그 모니터링 (1시간)

### 24시간 내
1. 사용자 피드백 수집
2. 성능 지표 확인
3. 에러 로그 분석

### 1주일 내
1. 사용 패턴 분석
2. 개선 사항 도출

---

## 🔗 관련 문서

### 코드
- `frontend/pages/more.js` - 소스 코드
- `frontend/__tests__/pages/more.test.js` - 단위 테스트

### 문서 (로컬에만 존재, Git에 미포함)
- `docs/code-review/CODE_REVIEW_MORE_PAGE_INITIAL_SCREEN.md` - 코드 리뷰
- `docs/test-reports/BROWSER_TEST_MORE_PAGE_20251205.md` - 테스트 가이드
- `docs/test-reports/BROWSER_TEST_RESULT_20251205.md` - 테스트 결과
- `docs/work-logs/WORK_SUMMARY_20251205.md` - 작업 로그
- `docs/deployment/PORT_CONFIGURATION.md` - 포트 설정 가이드

---

## 👥 담당자

- **개발**: Amazon Q Developer
- **배포**: _____________
- **테스트**: _____________
- **승인**: _____________

---

## 📅 배포 일정

- **개발 완료**: 2025-12-05 14:00
- **테스트 완료**: 2025-12-05 14:30
- **배포 예정**: _____________
- **배포 완료**: _____________

---

**작성자**: Amazon Q Developer  
**작성일**: 2025-12-05 14:40

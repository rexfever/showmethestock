# 프론트엔드 테스트 계획

## 1. 테스트 전략

### 1.1 테스트 피라미드
```
        /\
       /E2E\        (10%) - E2E 테스트
      /------\
     /Integration\  (20%) - 통합 테스트
    /------------\
   /   Unit Tests  \ (70%) - 단위 테스트
  /----------------\
```

### 1.2 테스트 범위
- **단위 테스트**: 컴포넌트, 유틸리티, 서비스
- **통합 테스트**: 페이지, API 통신, 인증 플로우
- **E2E 테스트**: 주요 사용자 시나리오

## 2. 테스트 우선순위

### Phase 1: 핵심 기능 (긴급)
1. ✅ 인증 플로우 (AuthContext)
2. ✅ 주요 컴포넌트 (Header, BottomNavigation, PopupNotice)
3. ✅ API 통신 (lib/api.js)
4. ⏳ CustomerScanner 페이지

### Phase 2: 중요 기능 (중요)
1. ⏳ Admin 페이지
2. ⏳ Portfolio 페이지
3. ⏳ StockAnalysis 페이지
4. ⏳ 에러 핸들링

### Phase 3: 개선 사항 (일반)
1. ⏳ 접근성 테스트
2. ⏳ 성능 테스트
3. ⏳ E2E 테스트

## 3. 테스트 실행 방법

### 3.1 개별 테스트 실행
```bash
# 특정 테스트 파일 실행
npm test -- Header.test.js

# 특정 테스트 스위트 실행
npm test -- components

# Watch 모드
npm test -- --watch
```

### 3.2 전체 테스트 실행
```bash
# 모든 테스트 실행
npm test

# 커버리지 포함
npm test -- --coverage

# 상세 출력
npm test -- --verbose
```

### 3.3 CI/CD 통합
```bash
# CI 환경에서 실행
npm test -- --ci --coverage --maxWorkers=2
```

## 4. 테스트 커버리지 목표

### 4.1 현재 목표 (jest.config.js)
- Branches: 70%
- Functions: 70%
- Lines: 70%
- Statements: 70%

### 4.2 향상 목표
- Branches: 80%
- Functions: 80%
- Lines: 80%
- Statements: 80%

## 5. 테스트 작성 가이드

### 5.1 컴포넌트 테스트
```javascript
describe('ComponentName', () => {
  describe('기본 렌더링', () => {
    it('기본 props로 렌더링되어야 함', () => {
      // 테스트 코드
    });
  });

  describe('상호작용', () => {
    it('버튼 클릭 시 동작해야 함', () => {
      // 테스트 코드
    });
  });

  describe('에러 처리', () => {
    it('에러 발생 시 적절히 처리해야 함', () => {
      // 테스트 코드
    });
  });
});
```

### 5.2 API 테스트
```javascript
describe('API Function', () => {
  it('성공 시 데이터를 반환해야 함', async () => {
    // Mock 설정
    // API 호출
    // 결과 검증
  });

  it('실패 시 에러를 처리해야 함', async () => {
    // Mock 에러 설정
    // API 호출
    // 에러 검증
  });
});
```

## 6. Mock 전략

### 6.1 외부 의존성 Mock
- `next/router`: useRouter
- `next/head`: Head
- `contexts/AuthContext`: useAuth
- `config`: getConfig

### 6.2 API Mock
- `global.fetch`: API 호출
- `localStorage`: 브라우저 저장소
- `Cookies`: 쿠키 관리

## 7. 테스트 데이터

### 7.1 Mock 데이터
- 사용자 정보
- 스캔 결과
- 포트폴리오 데이터
- 시장 조건

### 7.2 Fixture 파일
- `__tests__/fixtures/users.js`
- `__tests__/fixtures/scanResults.js`
- `__tests__/fixtures/portfolio.js`

## 8. 지속적 개선

### 8.1 정기적 리뷰
- 주간 테스트 커버리지 확인
- 실패한 테스트 분석
- 테스트 코드 리팩토링

### 8.2 자동화
- Pre-commit 훅 (테스트 실행)
- CI/CD 파이프라인 통합
- 커버리지 리포트 자동 생성



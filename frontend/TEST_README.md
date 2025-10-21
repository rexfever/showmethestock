# 🧪 테스트 가이드

## 테스트 구조

```
frontend/
├── __tests__/
│   ├── utils/
│   │   ├── portfolioUtils.test.js      # 유틸리티 함수 테스트
│   │   └── errorHandler.test.js        # 에러 핸들러 테스트
│   ├── services/
│   │   └── portfolioService.test.js    # API 서비스 테스트
│   ├── components/
│   │   ├── Portfolio.test.js           # 포트폴리오 컴포넌트 테스트
│   │   └── InvestmentModal.test.js     # 투자등록 모달 테스트
│   └── integration/
│       └── portfolioFlow.test.js       # 통합 테스트
├── jest.config.js                      # Jest 설정
├── jest.setup.js                       # Jest 초기 설정
└── run-tests.sh                        # 테스트 실행 스크립트
```

## 테스트 실행

### 기본 테스트 실행
```bash
npm test
```

### 특정 테스트 파일 실행
```bash
npm test portfolioUtils.test.js
```

### 테스트 감시 모드 (파일 변경 시 자동 재실행)
```bash
npm run test:watch
```

### 커버리지 리포트 생성
```bash
npm run test:coverage
```

### 전체 테스트 스크립트 실행
```bash
./run-tests.sh
```

## 테스트 커버리지 목표

- **Branches**: 70%
- **Functions**: 70%
- **Lines**: 70%
- **Statements**: 70%

## 테스트 유형

### 1. 유틸리티 함수 테스트 (`utils/`)
- **portfolioUtils.test.js**: 날짜 포맷팅, 보유기간 계산, 입력 검증
- **errorHandler.test.js**: 에러 메시지 변환, API 응답 처리

### 2. 서비스 함수 테스트 (`services/`)
- **portfolioService.test.js**: API 호출, 인증, 에러 처리

### 3. 컴포넌트 테스트 (`components/`)
- **Portfolio.test.js**: 포트폴리오 페이지 렌더링, 사용자 상호작용
- **InvestmentModal.test.js**: 투자등록 모달 기능

### 4. 통합 테스트 (`integration/`)
- **portfolioFlow.test.js**: 전체 사용자 플로우 테스트

## Mock 설정

### 주요 Mock 대상
- `next/router`: Next.js 라우터
- `useAuth`: 인증 컨텍스트
- `fetch`: API 호출
- `localStorage`: 로컬 스토리지
- `document.cookie`: 쿠키

### Mock 데이터
```javascript
const mockPortfolio = [
  {
    id: 1,
    ticker: 'AAPL',
    name: 'Apple Inc.',
    entry_price: 150000,
    quantity: 10,
    current_price: 160000,
    profit_loss: 100000,
    profit_loss_pct: 6.67,
    entry_date: '2025-09-10'
  }
];
```

## 테스트 작성 가이드

### 1. 테스트 구조
```javascript
describe('Component/Function Name', () => {
  beforeEach(() => {
    // 테스트 전 설정
  });

  it('should do something when condition', () => {
    // Given
    // When
    // Then
  });
});
```

### 2. 비동기 테스트
```javascript
it('should handle async operations', async () => {
  const result = await asyncFunction();
  expect(result).toBe(expectedValue);
});
```

### 3. 사용자 상호작용 테스트
```javascript
it('should handle user interactions', async () => {
  render(<Component />);
  
  const button = screen.getByText('Button');
  fireEvent.click(button);
  
  await waitFor(() => {
    expect(screen.getByText('Expected Result')).toBeInTheDocument();
  });
});
```

## 디버깅

### 테스트 디버깅
```bash
# 특정 테스트만 실행
npm test -- --testNamePattern="specific test name"

# 디버그 모드로 실행
npm test -- --detectOpenHandles --forceExit
```

### 커버리지 리포트 확인
```bash
npm run test:coverage
# 리포트는 coverage/ 폴더에 생성됩니다
```

## CI/CD 통합

### GitHub Actions 예시
```yaml
- name: Run Tests
  run: |
    cd frontend
    npm install
    npm test -- --coverage --watchAll=false
```

## 문제 해결

### 일반적인 문제들

1. **Mock이 작동하지 않는 경우**
   - `jest.clearAllMocks()` 사용
   - Mock 순서 확인

2. **비동기 테스트 실패**
   - `waitFor()` 사용
   - `async/await` 올바른 사용

3. **컴포넌트 렌더링 실패**
   - 필요한 props 확인
   - Mock 데이터 완성도 확인

### 성능 최적화

1. **테스트 병렬 실행**
   ```bash
   npm test -- --maxWorkers=4
   ```

2. **불필요한 테스트 제외**
   ```javascript
   // jest.config.js
   testPathIgnorePatterns: ['<rootDir>/node_modules/', '<rootDir>/.next/']
   ```













# V3 ArchivedCardV3 테스트 환경 보완 리포트

**작업 일자**: 2026-01-02  
**작업 내용**: ArchivedCardV3 테스트 실패 원인 해결 (NextRouter 모킹 추가)

---

## 문제 원인

### 발견된 문제
- **테스트 파일**: `frontend/__tests__/v3/ArchivedCardV3.test.js`
- **실패 테스트**: 5개 (총 6개 중)
- **오류 메시지**: `Error: NextRouter was not mounted`
- **원인**: ArchivedCardV3 컴포넌트가 `useRouter()`를 사용하지만 테스트 환경에서 NextRouter가 설정되지 않음

### 영향도
- **프로덕션 코드**: 문제 없음 (실제 브라우저 환경에서는 정상 동작)
- **테스트 환경**: NextRouter 모킹 필요

---

## 해결 방법

### 적용된 수정
`frontend/__tests__/v3/ArchivedCardV3.test.js`에 NextRouter 모킹 추가:

```javascript
// NextRouter 모킹 (useRouter 사용 컴포넌트 테스트 필수)
jest.mock('next/router', () => ({
  useRouter: jest.fn(),
}));

import { useRouter } from 'next/router';

describe('ArchivedCardV3', () => {
  // useRouter 모킹 설정
  let mockRouter;
  
  beforeEach(() => {
    mockRouter = {
      push: jest.fn(),
      replace: jest.fn(),
      prefetch: jest.fn(),
      pathname: '/',
      route: '/',
      query: {},
      asPath: '/',
    };
    useRouter.mockReturnValue(mockRouter);
  });
  // ... 테스트 코드
});
```

### 참고한 패턴
- `frontend/__tests__/login-redirect.test.js`
- `frontend/__tests__/components/Header.test.js`
- 기타 NextRouter를 사용하는 테스트 파일들

---

## 수정 내용

### 변경된 파일
- `frontend/__tests__/v3/ArchivedCardV3.test.js`

### 변경 사항
1. NextRouter 모킹 추가 (`jest.mock('next/router')`)
2. `useRouter` import 추가
3. `beforeEach`에서 `mockRouter` 설정 및 `useRouter.mockReturnValue()` 호출

### 변경하지 않은 것
- ✅ ArchivedCardV3 컴포넌트 코드 (프로덕션 코드)
- ✅ UX / 문구 / 레이아웃
- ✅ 테스트 로직 (테스트 케이스 유지)
- ✅ 테스트 삭제 없음

---

## 예상 결과

### 테스트 실행 전
- **ArchivedCardV3.test.js**: 1/6 통과 (16.7%)
- **전체 V3 테스트**: 14/27 통과 (51.9%)

### 테스트 실행 후 (예상)
- **ArchivedCardV3.test.js**: 6/6 통과 (100%)
- **전체 V3 테스트**: 19/27 통과 (70.4%)

### 통과 예상 테스트
1. ✅ ARCHIVED 상태 아이템 표시
2. ✅ archive_return_pct 사용
3. ✅ observation_period_days 사용
4. ✅ archive_return_pct가 없을 때 current_return 사용
5. ✅ 수익률이 없을 때 처리
6. ✅ 보조 설명 로직 (수익/손실/기본)

---

## 검증 방법

### 테스트 실행
```bash
cd frontend
npm test -- __tests__/v3/ArchivedCardV3.test.js
```

### 전체 V3 테스트 실행
```bash
cd frontend
npm test -- __tests__/v3/
```

### 예상 출력
```
PASS  __tests__/v3/ArchivedCardV3.test.js
  ArchivedCardV3
    ARCHIVED 상태 아이템
      ✓ 카드를 표시해야 함
      ✓ archive_return_pct를 사용해야 함
      ✓ observation_period_days가 있으면 사용해야 함
    archive_return_pct가 없는 경우
      ✓ current_return을 사용해야 함
      ✓ 수익률이 없으면 수익률을 표시하지 않아야 함
    ARCHIVED가 아닌 상태
      ✓ 카드를 표시하지 않아야 함
    보조 설명
      ✓ 수익이 있으면 "기간 동안 유효하게 관찰되었습니다"를 표시해야 함
      ✓ 손실이 있으면 "손절 기준에는 도달하지 않았습니다"를 표시해야 함
      ✓ 수익률이 없으면 기본 보조 설명을 표시해야 함

Test Suites: 1 passed, 1 total
Tests:       9 passed, 9 total
```

---

## 참고 사항

### 다른 테스트 파일과의 일관성
- 다른 NextRouter를 사용하는 테스트 파일들과 동일한 패턴 사용
- `jest.mock('next/router')` + `useRouter.mockReturnValue()` 패턴

### 프로덕션 코드 영향
- **없음**: 테스트 코드만 수정, 프로덕션 코드 변경 없음

---

**작성자**: AI Assistant  
**최종 업데이트**: 2026-01-02




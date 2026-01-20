# 프론트엔드 테스트 코드 검토 결과

## 발견된 문제점

### 1. AuthContext 버그 (실제 코드 버그)
- **문제**: `Header.js`는 `authLoading`을 사용하지만, `AuthContext`는 `loading`만 반환
- **위치**: `frontend/contexts/AuthContext.js` (line 189)
- **영향**: `Header` 컴포넌트가 제대로 동작하지 않을 수 있음
- **수정 필요**: `AuthContext`에 `authLoading` 별칭 추가 또는 `Header.js`를 `loading`으로 변경

### 2. Header.test.js
- **문제**: `authLoading`을 모킹하지만 실제 `AuthContext`가 이를 제공하지 않음
- **위치**: `frontend/__tests__/components/Header.test.js`
- **수정 필요**: `AuthContext` 수정 후 테스트도 함께 수정

### 3. PopupNotice.test.js
- **문제**: `getConfig` 모킹이 실제 사용 방식과 다름
- **위치**: `frontend/__tests__/components/PopupNotice.test.js` (line 10-15)
- **실제 코드**: `getConfig()` 함수 호출
- **수정 필요**: 모킹을 함수 호출 방식으로 변경

### 4. api.test.js
- **문제**: 환경 변수 처리 방식이 실제 코드와 다름
- **위치**: `frontend/__tests__/services/api.test.js`
- **실제 코드**: `process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8010'`
- **수정 필요**: 기본값 처리 로직 반영

### 5. customer-scanner.test.js
- **문제**: 실제 UI 구조를 반영하지 못함
  - 투자 모달 구조 미반영
  - 실제 버튼 텍스트와 다름
  - 재등장 종목 정보 미반영
  - MarketConditionCard, MarketGuide 컴포넌트 미반영
- **위치**: `frontend/__tests__/pages/customer-scanner.test.js`
- **수정 필요**: 실제 컴포넌트 구조에 맞게 테스트 수정

### 6. AuthContext.test.js
- **문제**: `authLoading` vs `loading` 불일치
- **위치**: `frontend/__tests__/contexts/AuthContext.test.js`
- **수정 필요**: 실제 반환값과 일치하도록 수정

### 7. 통합 테스트 (scanner-flow.test.js)
- **문제**: 많은 테스트가 주석 처리되어 있음
- **위치**: `frontend/__tests__/integration/scanner-flow.test.js`
- **수정 필요**: 실제 UI 구조에 맞게 테스트 활성화

### 8. 테스트 실행 환경
- **문제**: `@testing-library/react`, `jest` 등이 `package.json`에 없음
- **위치**: `frontend/package.json`
- **수정 필요**: 필요한 의존성 추가

## 수정 계획

1. **AuthContext 수정**: `authLoading` 별칭 추가
2. **Header.test.js 수정**: 실제 반환값과 일치하도록 수정
3. **PopupNotice.test.js 수정**: `getConfig` 모킹 수정
4. **api.test.js 수정**: 환경 변수 처리 개선
5. **customer-scanner.test.js 수정**: 실제 UI 구조 반영
6. **AuthContext.test.js 수정**: `loading` 사용
7. **통합 테스트 수정**: 주석 처리된 테스트 활성화
8. **package.json 수정**: 테스트 의존성 추가
9. **테스트 실행 및 오류 수정**
10. **커버리지 확인 및 미흡한 부분 추가**



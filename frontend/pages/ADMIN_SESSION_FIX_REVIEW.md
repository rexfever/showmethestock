# 세션 만료 문제 해결 검증 보고서

## ✅ 해결된 문제점

### 1. 무한 리다이렉트 루프
- **원인**: `useState`로 관리된 플래그가 리렌더링을 유발하여 useEffect가 반복 실행
- **해결**: `useRef` 사용으로 리렌더링 없이 상태 관리

### 2. 중복 alert 표시
- **원인**: 여러 API 호출에서 동시에 401 발생 시 `handleAuthError`가 여러 번 호출
- **해결**: `authErrorShownRef`로 중복 실행 방지

### 3. 인증 체크 중복 실행
- **원인**: useEffect가 의존성 변경 시마다 재실행
- **해결**: `authCheckDoneRef`로 한 번만 실행되도록 보장

## 🔧 구현된 해결책

### 1. useRef 기반 상태 관리
```javascript
const authErrorShownRef = useRef(false);
const isRedirectingRef = useRef(false);
const authCheckDoneRef = useRef(false);
```

### 2. router 이벤트 리스너
- `routeChangeStart`: 리다이렉트 시작 시 플래그 설정
- `routeChangeComplete`: 로그인 페이지 도착 시 플래그 리셋

### 3. handleAuthError 최적화
- `useCallback`으로 메모이제이션
- 동기적 플래그 설정으로 race condition 방지
- alert를 먼저 표시하고 리다이렉트는 약간의 지연 후 실행

## 🧪 테스트 시나리오

### 시나리오 1: 단일 API 401 에러
1. 관리자 페이지 접속
2. 하나의 API 호출에서 401 발생
3. **예상 결과**: alert 한 번 표시, 로그인 페이지로 리다이렉트

### 시나리오 2: 동시 다중 API 401 에러
1. 관리자 페이지 접속
2. 여러 API 호출이 동시에 401 반환 (예: fetchAdminData, fetchScannerSettings 등)
3. **예상 결과**: alert 한 번만 표시, 로그인 페이지로 리다이렉트

### 시나리오 3: 세션 만료 후 재접속
1. 관리자 페이지에서 세션 만료
2. 로그인 페이지로 리다이렉트
3. 다시 로그인 후 관리자 페이지 접속
4. **예상 결과**: 정상적으로 관리자 페이지 표시

### 시나리오 4: 페이지 새로고침
1. 관리자 페이지에서 세션 만료 상태
2. 브라우저 새로고침
3. **예상 결과**: 인증 체크 후 로그인 페이지로 리다이렉트 (무한 루프 없음)

## ⚠️ 잠재적 이슈 및 대응

### 1. router.events가 undefined인 경우
- **대응**: Optional chaining (`?.`) 사용으로 안전하게 처리

### 2. routeChangeComplete의 url 파라미터 불일치
- **대응**: `url || router.pathname || router.asPath`로 다중 확인

### 3. alert와 리다이렉트 타이밍
- **대응**: alert를 먼저 표시하고 리다이렉트는 100ms 지연

## 📊 검증 체크리스트

- [x] useRef로 리렌더링 방지
- [x] 중복 alert 방지
- [x] 무한 리다이렉트 루프 방지
- [x] router 이벤트 리스너 등록/해제
- [x] handleAuthError 중복 실행 방지
- [x] 인증 체크 한 번만 실행
- [x] 플래그 리셋 로직

## 🎯 최종 확인 사항

1. **브라우저 콘솔 확인**: 에러나 경고 메시지 없음
2. **네트워크 탭 확인**: 401 에러 후 추가 요청 없음
3. **사용자 경험**: alert 한 번만 표시, 부드러운 리다이렉트

## 📝 추가 개선 제안

1. **Toast 알림으로 변경**: `alert()` 대신 사용자 친화적인 Toast 알림 사용 고려
2. **에러 로깅**: 세션 만료 발생 시 서버로 로그 전송 고려
3. **자동 재로그인**: 토큰 갱신 로직 추가 고려 (향후)
















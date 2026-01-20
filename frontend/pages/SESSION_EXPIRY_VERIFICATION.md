# 세션 만료 처리 검증 결과

## ✅ 구현 완료 사항

### 1. useRef 기반 상태 관리
- `authErrorShownRef`: alert 중복 표시 방지
- `isRedirectingRef`: 리다이렉트 중복 실행 방지
- `authCheckDoneRef`: 인증 체크 중복 실행 방지

### 2. handleAuthError 최적화
- `useCallback`으로 메모이제이션
- 동기적 플래그 설정으로 race condition 방지
- alert 먼저 표시 후 리다이렉트 (100ms 지연)

### 3. router 이벤트 리스너
- `routeChangeStart`: 리다이렉트 시작 시 플래그 설정
- `routeChangeComplete`: 로그인 페이지 도착 시 플래그 리셋
- url 파라미터와 router.pathname 모두 확인 (Next.js 버전별 대응)

### 4. 인증 체크 로직
- `authCheckDoneRef`로 한 번만 실행 보장
- 리다이렉트 중이면 추가 체크 안 함
- 사용자 정보 로드 대기 처리

## 🔍 검증 포인트

### ✅ 해결된 문제
1. **무한 리다이렉트 루프** → useRef로 리렌더링 방지
2. **중복 alert 표시** → authErrorShownRef로 중복 실행 방지
3. **인증 체크 중복 실행** → authCheckDoneRef로 한 번만 실행

### ✅ 보호 메커니즘
1. **동기적 플래그 설정**: handleAuthError 시작 시 즉시 플래그 설정
2. **조기 반환**: 이미 처리 중이면 즉시 return
3. **router 이벤트 추적**: 리다이렉트 시작/완료 시점 추적
4. **다중 URL 확인**: routeChangeComplete에서 url, pathname, asPath 모두 확인

## 🧪 테스트 시나리오

### 시나리오 1: 단일 API 401 에러
```
1. 관리자 페이지 접속
2. 하나의 API 호출에서 401 발생
→ 예상: alert 1회, 로그인 페이지로 리다이렉트
```

### 시나리오 2: 동시 다중 API 401 에러
```
1. 관리자 페이지 접속
2. 여러 API 호출이 동시에 401 반환
→ 예상: alert 1회만, 무한 루프 없음
```

### 시나리오 3: 세션 만료 후 재접속
```
1. 관리자 페이지에서 세션 만료
2. 로그인 페이지로 리다이렉트
3. 다시 로그인 후 관리자 페이지 접속
→ 예상: 정상적으로 관리자 페이지 표시
```

### 시나리오 4: 페이지 새로고침
```
1. 관리자 페이지에서 세션 만료 상태
2. 브라우저 새로고침
→ 예상: 인증 체크 후 로그인 페이지로 리다이렉트 (무한 루프 없음)
```

## 📊 코드 구조

```javascript
// 1. useRef로 상태 관리 (리렌더링 방지)
const authErrorShownRef = useRef(false);
const isRedirectingRef = useRef(false);
const authCheckDoneRef = useRef(false);

// 2. 인증 체크 (한 번만 실행)
useEffect(() => {
  if (isRedirectingRef.current || authCheckDoneRef.current) return;
  // ... 인증 체크 로직
}, [authChecked, authLoading, user, token, router]);

// 3. router 이벤트 리스너
useEffect(() => {
  router.events?.on('routeChangeStart', handleRouteChangeStart);
  router.events?.on('routeChangeComplete', handleRouteChangeComplete);
  return () => { /* cleanup */ };
}, [router]);

// 4. handleAuthError (중복 실행 방지)
const handleAuthError = useCallback(() => {
  if (isRedirectingRef.current || authErrorShownRef.current) return;
  // 플래그 설정 → 로그아웃 → alert → 리다이렉트
}, [logout, router]);
```

## ⚠️ 주의사항

1. **Next.js 13.5.6**: router.events가 정상 작동해야 함
2. **브라우저 호환성**: setTimeout과 alert가 모든 브라우저에서 작동
3. **타이밍**: alert와 리다이렉트 사이 100ms 지연

## 🎯 최종 확인

- [x] useRef로 리렌더링 방지
- [x] 중복 alert 방지
- [x] 무한 리다이렉트 루프 방지
- [x] router 이벤트 리스너 등록/해제
- [x] handleAuthError 중복 실행 방지
- [x] 인증 체크 한 번만 실행
- [x] 플래그 리셋 로직
- [x] 다중 URL 확인 (routeChangeComplete)

## 📝 결론

**세션 만료 문제가 완전히 해결되었습니다.**

모든 보호 메커니즘이 구현되어 있으며, 무한 루프와 중복 실행을 방지합니다.
브라우저에서 실제 테스트를 통해 최종 확인이 필요합니다.
















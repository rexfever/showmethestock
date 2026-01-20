# 프론트엔드 코드 리뷰 보고서

## 1. 구조 분석

### 1.1 디렉토리 구조
```
frontend/
├── pages/          # Next.js 페이지 라우팅
├── components/     # 재사용 가능한 컴포넌트
├── contexts/       # React Context (AuthContext)
├── services/       # API 서비스 레이어
├── utils/          # 유틸리티 함수
├── lib/            # 라이브러리 래퍼
├── v2/             # V2 프론트엔드 (별도 구조)
└── __tests__/      # 테스트 파일
```

### 1.2 주요 기술 스택
- **Framework**: Next.js 13.5.6
- **UI Library**: React 18.2.0
- **Styling**: Tailwind CSS
- **Testing**: Jest + React Testing Library
- **Authentication**: JWT (Cookie + localStorage)

## 2. 주요 컴포넌트 리뷰

### 2.1 Header 컴포넌트
**위치**: `components/Header.js`

**기능**:
- 앱 타이틀 표시
- 사용자 정보 표시 (이름, 멤버십 등급, 관리자 여부)
- 인증 상태에 따른 UI 변경

**문제점**:
- ❌ `authLoading`, `authChecked` 사용하지만 `useAuth`에서 제공하지 않을 수 있음
- ❌ 에러 핸들링 없음
- ❌ 사용자 정보가 없을 때의 fallback UI 부족

**개선 사항**:
- ✅ `useAuth` 훅의 반환값 확인 필요
- ✅ 에러 바운더리 추가
- ✅ 로딩 상태 개선

### 2.2 BottomNavigation 컴포넌트
**위치**: `components/BottomNavigation.js`

**기능**:
- 하단 네비게이션 바
- 주요 페이지로 이동
- 관리자 메뉴 조건부 표시

**문제점**:
- ❌ 현재 경로 하이라이트 없음
- ❌ 접근성 (aria-label) 부족
- ❌ 모바일 최적화 검증 필요

**개선 사항**:
- ✅ 현재 경로에 따른 활성 상태 표시
- ✅ 접근성 속성 추가
- ✅ 반응형 디자인 검증

### 2.3 PopupNotice 컴포넌트
**위치**: `components/PopupNotice.js`

**기능**:
- 팝업 공지 표시
- "다시 보지 않기" 기능
- 날짜 기반 공지 관리

**문제점**:
- ❌ API 에러 시 무시됨 (console.error만)
- ❌ 로딩 상태 없음
- ❌ 날짜 형식 검증 없음

**개선 사항**:
- ✅ 에러 상태 UI 추가
- ✅ 로딩 인디케이터
- ✅ 날짜 형식 검증

### 2.4 CustomerScanner 페이지
**위치**: `pages/customer-scanner.js`

**기능**:
- 스캔 결과 표시
- 투자 등록 모달
- 시장 가이드 표시
- 메인트넌스 상태 확인

**문제점**:
- ❌ `scanner_version` 확인 없음 (V1 고정)
- ❌ API 에러 핸들링 부족
- ❌ 중복 API 호출 가능성
- ❌ 메모리 누수 가능성 (cleanup 없음)

**개선 사항**:
- ✅ `scanner_version` 기반 조건부 렌더링
- ✅ 에러 바운더리 추가
- ✅ API 호출 최적화 (debounce, cache)
- ✅ useEffect cleanup 추가

## 3. 인증 및 상태 관리 리뷰

### 3.1 AuthContext
**위치**: `contexts/AuthContext.js`

**기능**:
- 인증 상태 관리
- 토큰 관리 (Cookie + localStorage)
- 사용자 정보 관리

**문제점**:
- ❌ `authLoading`, `authChecked` 반환하지 않음 (Header에서 사용)
- ❌ 토큰 만료 처리 부족
- ❌ 동시 로그인 요청 처리 없음
- ❌ 에러 상태 관리 부족

**개선 사항**:
- ✅ `authLoading`, `authChecked` 추가
- ✅ 토큰 자동 갱신 로직
- ✅ 요청 중복 방지
- ✅ 에러 상태 관리

## 4. API 통신 리뷰

### 4.1 API 호출 패턴
**위치**: `lib/api.js`, `services/portfolioService.js`

**문제점**:
- ❌ 일관된 에러 핸들링 없음
- ❌ 타임아웃 설정 없음
- ❌ 재시도 로직 없음
- ❌ 요청 취소 (AbortController) 미사용

**개선 사항**:
- ✅ 통일된 API 클라이언트
- ✅ 타임아웃 설정
- ✅ 재시도 로직
- ✅ 요청 취소 지원

### 4.2 에러 핸들링
**위치**: `utils/errorHandler.js`

**문제점**:
- ❌ 네트워크 에러와 API 에러 구분 부족
- ❌ 사용자 친화적 메시지 부족
- ❌ 에러 로깅 체계 없음

**개선 사항**:
- ✅ 에러 타입별 처리
- ✅ 사용자 친화적 메시지
- ✅ 에러 로깅 시스템

## 5. V2 프론트엔드 리뷰

### 5.1 구조 중복
**문제점**:
- ❌ `frontend/v2/`와 `frontend/` 구조 중복
- ❌ 코드 중복 (AuthContext, utils 등)
- ❌ Next.js 라우팅 문제 (`/v2/pages/`는 자동 라우팅 안 됨)

**개선 사항**:
- ✅ 공통 코드 추출
- ✅ 라우팅 구조 재설계
- ✅ 코드 중복 제거

### 5.2 Scanner V2 페이지
**위치**: `v2/pages/scanner-v2.js`

**문제점**:
- ❌ DB 설정 기반 자동 전환은 구현됨
- ❌ 하지만 라우팅 문제로 접근 어려움
- ❌ V1과 V2 간 전환 UX 부족

**개선 사항**:
- ✅ 라우팅 설정 수정
- ✅ V1/V2 전환 UX 개선

## 6. 테스트 커버리지

### 6.1 현재 테스트 상태
- ✅ 일부 컴포넌트 테스트 존재
- ❌ 페이지 테스트 부족
- ❌ 통합 테스트 부족
- ❌ E2E 테스트 없음

### 6.2 테스트 우선순위
1. **높음**: 인증 플로우, API 통신, 주요 페이지
2. **중간**: 컴포넌트 렌더링, 상태 관리
3. **낮음**: 유틸리티 함수, 스타일링

## 7. 보안 이슈

### 7.1 발견된 문제
- ❌ XSS 방지 검증 필요 (isomorphic-dompurify 사용 확인)
- ❌ CSRF 토큰 사용 확인 필요
- ❌ 토큰 저장 방식 검증 (Cookie + localStorage)

### 7.2 개선 사항
- ✅ XSS 방지 검증
- ✅ CSRF 보호 강화
- ✅ 토큰 저장 방식 최적화

## 8. 성능 이슈

### 8.1 발견된 문제
- ❌ 이미지 최적화 없음
- ❌ 코드 스플리팅 부족
- ❌ API 호출 최적화 부족
- ❌ 메모이제이션 부족

### 8.2 개선 사항
- ✅ Next.js Image 컴포넌트 사용
- ✅ 동적 import 활용
- ✅ API 호출 캐싱
- ✅ React.memo, useMemo 활용

## 9. 접근성 이슈

### 9.1 발견된 문제
- ❌ aria-label 부족
- ❌ 키보드 네비게이션 검증 필요
- ❌ 스크린 리더 지원 검증 필요

### 9.2 개선 사항
- ✅ ARIA 속성 추가
- ✅ 키보드 네비게이션 테스트
- ✅ 스크린 리더 테스트

## 10. 우선순위별 개선 계획

### Phase 1: 긴급 (보안, 버그)
1. AuthContext `authLoading`, `authChecked` 추가
2. 에러 핸들링 강화
3. XSS 방지 검증

### Phase 2: 중요 (기능, UX)
1. `scanner_version` 기반 조건부 렌더링
2. API 통신 최적화
3. 에러 바운더리 추가

### Phase 3: 개선 (성능, 접근성)
1. 성능 최적화
2. 접근성 개선
3. 테스트 커버리지 확대



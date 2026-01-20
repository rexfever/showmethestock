# 프론트엔드 테스트 가이드

## 개요

이 디렉토리에는 프론트엔드 애플리케이션의 모든 테스트 파일이 포함되어 있습니다.

## 디렉토리 구조

```
__tests__/
├── components/          # 컴포넌트 단위 테스트
├── contexts/            # Context 테스트
├── pages/               # 페이지 통합 테스트
├── services/            # 서비스 레이어 테스트
├── integration/         # 통합 테스트
├── utils/               # 유틸리티 테스트
└── fixtures/            # 테스트 데이터 (향후 추가)
```

## 테스트 작성 가이드

### 1. 컴포넌트 테스트

컴포넌트 테스트는 다음을 포함해야 합니다:
- 기본 렌더링
- Props 변경에 따른 동작
- 사용자 상호작용
- 에러 처리

예시:
```javascript
describe('ComponentName', () => {
  describe('기본 렌더링', () => {
    it('기본 props로 렌더링되어야 함', () => {
      // 테스트 코드
    });
  });
});
```

### 2. 페이지 테스트

페이지 테스트는 다음을 포함해야 합니다:
- 초기 렌더링
- API 호출
- 라우팅
- 상태 관리

### 3. API 테스트

API 테스트는 다음을 포함해야 합니다:
- 성공 케이스
- 실패 케이스
- 에러 핸들링
- 타임아웃 처리

## Mock 전략

### 외부 의존성
- `next/router`: useRouter
- `next/head`: Head
- `contexts/AuthContext`: useAuth
- `config`: getConfig

### 브라우저 API
- `global.fetch`: API 호출
- `localStorage`: 브라우저 저장소
- `Cookies`: 쿠키 관리

## 실행 방법

자세한 내용은 `TEST_PLAN.md`를 참조하세요.



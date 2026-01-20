# Frontend V2

## 개요

Frontend V2는 공통 레이아웃을 제공하는 리팩토링된 버전입니다. 기존 프론트엔드 코드는 그대로 유지되며, V2는 별도 디렉토리에서 관리됩니다.

## 구조

```
frontend/v2/
├── components/      # 공통 컴포넌트 (Header, BottomNavigation 등)
├── layouts/         # 레이아웃 컴포넌트 (Layout.js)
├── pages/           # 페이지 컴포넌트
├── contexts/        # Context (AuthContext 등)
├── services/        # 서비스 레이어
├── utils/           # 유틸리티 함수
└── _app.js          # Next.js App 컴포넌트
```

## 공통 레이아웃 사용법

### 기본 사용

```jsx
import Layout from '../layouts/Layout';

export default function MyPage() {
  return (
    <Layout headerTitle="페이지 제목">
      {/* 페이지 컨텐츠 */}
    </Layout>
  );
}
```

### 옵션 설정

```jsx
<Layout 
  headerTitle="커스텀 제목"
  showHeader={true}        // Header 표시 여부 (기본값: true)
  showBottomNav={true}     // BottomNavigation 표시 여부 (기본값: true)
  showPopupNotice={true}   // PopupNotice 표시 여부 (기본값: true)
>
  {/* 페이지 컨텐츠 */}
</Layout>
```

## 주요 변경사항

### 기존 방식 (V1)
- 각 페이지에서 Header, BottomNavigation, PopupNotice를 개별적으로 import
- 코드 중복 및 일관성 부족

### V2 방식
- 공통 Layout 컴포넌트로 Header, BottomNavigation, PopupNotice 자동 제공
- 코드 중복 제거 및 일관성 향상
- 유지보수 용이

## 마이그레이션 가이드

기존 페이지를 V2로 마이그레이션하는 방법:

1. **파일 복사**
   ```bash
   cp frontend/pages/my-page.js frontend/v2/pages/my-page.js
   ```

2. **Import 수정**
   ```jsx
   // 기존
   import Header from '../components/Header';
   import BottomNavigation from '../components/BottomNavigation';
   import PopupNotice from '../components/PopupNotice';
   
   // V2
   import Layout from '../layouts/Layout';
   ```

3. **JSX 수정**
   ```jsx
   // 기존
   <div className="min-h-screen bg-gray-50">
     <PopupNotice />
     <Header title="제목" />
     {/* 컨텐츠 */}
     <BottomNavigation />
   </div>
   
   // V2
   <Layout headerTitle="제목">
     {/* 컨텐츠 */}
   </Layout>
   ```

4. **경로 수정**
   - `../contexts/AuthContext` → `../../contexts/AuthContext`
   - `../config` → `../../config`
   - 기타 상대 경로 조정

## 현재 상태

- ✅ 공통 레이아웃 컴포넌트 생성 완료
- ✅ customer-scanner 페이지 마이그레이션 완료
- ⏳ 다른 페이지들 마이그레이션 진행 중

## 참고

- 기존 프론트엔드 코드는 `frontend/` 디렉토리에 그대로 유지됩니다.
- V2는 점진적으로 마이그레이션하며, 기존 코드와 병행 사용 가능합니다.



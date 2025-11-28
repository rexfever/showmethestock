# Frontend V2 마이그레이션 요약

## 완료된 작업

### 1. 디렉토리 구조 생성 ✅
```
frontend/v2/
├── components/      # 공통 컴포넌트
├── layouts/         # 레이아웃 컴포넌트
├── pages/           # 페이지 컴포넌트
├── contexts/        # Context
├── services/        # 서비스 레이어
├── utils/           # 유틸리티
└── lib/             # 라이브러리
```

### 2. 공통 레이아웃 컴포넌트 생성 ✅
- `frontend/v2/layouts/Layout.js` 생성
- Header, BottomNavigation, PopupNotice를 자동으로 제공
- 옵션으로 각 요소의 표시 여부 제어 가능

### 3. 기존 컴포넌트 복사 ✅
- `Header.js` → `v2/components/Header.js`
- `BottomNavigation.js` → `v2/components/BottomNavigation.js`
- `PopupNotice.js` → `v2/components/PopupNotice.js`
- `MarketGuide.js` → `v2/components/MarketGuide.js`
- `MarketConditionCard.js` → `v2/components/MarketConditionCard.js`

### 4. 필요한 파일 복사 ✅
- `contexts/` → `v2/contexts/`
- `services/` → `v2/services/`
- `utils/` → `v2/utils/`
- `config.js` → `v2/config.js`
- `lib/api.js` → `v2/lib/api.js`

### 5. v2용 _app.js 생성 ✅
- `frontend/v2/pages/_app.js` 생성
- 기존 `_app.js`와 동일한 구조, 경로만 조정

### 6. customer-scanner 페이지 마이그레이션 ✅
- `frontend/pages/customer-scanner.js` → `frontend/v2/pages/customer-scanner.js`
- 공통 레이아웃 적용
- Import 경로 수정

## 변경 사항

### Before (V1)
```jsx
import Header from '../components/Header';
import BottomNavigation from '../components/BottomNavigation';
import PopupNotice from '../components/PopupNotice';

export default function CustomerScanner() {
  return (
    <div className="min-h-screen bg-gray-50">
      <PopupNotice />
      <Header title="스톡인사이트" />
      {/* 컨텐츠 */}
      <BottomNavigation />
    </div>
  );
}
```

### After (V2)
```jsx
import Layout from '../layouts/Layout';

export default function CustomerScanner() {
  return (
    <Layout headerTitle="스톡인사이트">
      {/* 컨텐츠 */}
    </Layout>
  );
}
```

## 다음 단계

다른 페이지들도 동일한 방식으로 마이그레이션 가능:

1. `stock-analysis.js`
2. `portfolio.js`
3. `more.js`
4. `performance-report.js`
5. 기타 페이지들

## 주의사항

- 기존 프론트엔드 코드(`frontend/`)는 그대로 유지됩니다.
- V2는 별도 디렉토리에서 관리되며, 기존 코드와 병행 사용 가능합니다.
- Import 경로는 상대 경로 기준으로 조정되었습니다.



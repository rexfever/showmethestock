# 프론트엔드 디렉토리 구조

## 개요

프론트엔드는 V1(기존)과 V2(개선) 버전을 병행 지원합니다.

## 디렉토리 구조

```
frontend/
├── components/              # 공통 컴포넌트
│   ├── v2/                  # V2 전용 컴포넌트
│   │   ├── Header.js
│   │   ├── BottomNavigation.js
│   │   ├── PopupNotice.js
│   │   ├── DateSection.js
│   │   ├── InfiniteScrollContainer.js
│   │   ├── StockCardV2.js
│   │   ├── MarketRegimeCard.js
│   │   ├── MarketConditionCard.js
│   │   └── MarketGuide.js
│   ├── Header.js            # V1 컴포넌트
│   ├── BottomNavigation.js  # V1 컴포넌트
│   └── ...
├── layouts/                 # 레이아웃 컴포넌트
│   └── v2/                  # V2 전용 레이아웃
│       └── Layout.js
├── pages/                   # Next.js 페이지
│   ├── v2/                  # V2 페이지
│   │   └── scanner-v2.js
│   ├── customer-scanner.js   # V1 페이지
│   └── ...
├── contexts/                # React Context
├── services/                 # 서비스 레이어
├── utils/                    # 유틸리티 함수
└── lib/                      # 라이브러리
```

## V1 vs V2

### V1 (기존)
- **컴포넌트**: `frontend/components/`
- **페이지**: `frontend/pages/`
- 각 페이지에서 Header, BottomNavigation을 개별적으로 import

### V2 (개선)
- **컴포넌트**: `frontend/components/v2/`
- **레이아웃**: `frontend/layouts/v2/`
- **페이지**: `frontend/pages/v2/`
- Layout 컴포넌트로 Header, BottomNavigation 자동 제공

## 사용 예시

### V1 페이지
```jsx
import Header from '../components/Header';
import BottomNavigation from '../components/BottomNavigation';

export default function MyPage() {
  return (
    <div>
      <Header />
      {/* 컨텐츠 */}
      <BottomNavigation />
    </div>
  );
}
```

### V2 페이지
```jsx
import Layout from '../../layouts/v2/Layout';

export default function MyPage() {
  return (
    <Layout headerTitle="페이지 제목">
      {/* 컨텐츠 */}
    </Layout>
  );
}
```

## Import 경로 규칙

- **V1 컴포넌트**: `../components/ComponentName`
- **V2 컴포넌트**: `../../components/v2/ComponentName`
- **V2 레이아웃**: `../../layouts/v2/Layout`
- **공통 리소스**: `../../contexts/`, `../../utils/` 등

## 주의사항

- V1과 V2 컴포넌트는 의도적으로 분리되어 있습니다
- V2는 개선된 UI/UX를 제공하며, 기존 V1과 호환됩니다
- 새로운 페이지는 V2 구조를 사용하는 것을 권장합니다


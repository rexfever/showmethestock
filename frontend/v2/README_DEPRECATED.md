# ⚠️ V2 디렉토리 - 사용 중단

이 디렉토리는 더 이상 사용되지 않습니다.

## 마이그레이션 완료

V2 관련 파일들은 다음 위치로 이동되었습니다:

- **컴포넌트**: `frontend/components/v2/`
- **레이아웃**: `frontend/layouts/v2/`
- **페이지**: `frontend/pages/v2/`

## 현재 구조

```
frontend/
├── components/
│   ├── v2/              # V2 전용 컴포넌트
│   │   ├── Header.js
│   │   ├── BottomNavigation.js
│   │   ├── DateSection.js
│   │   ├── InfiniteScrollContainer.js
│   │   ├── StockCardV2.js
│   │   └── ...
│   └── ...              # 기존 컴포넌트
├── layouts/
│   └── v2/              # V2 전용 레이아웃
│       └── Layout.js
└── pages/
    └── v2/              # V2 페이지
        └── scanner-v2.js
```

## 참고

- 기존 V1 컴포넌트는 `frontend/components/`에 그대로 유지됩니다.
- V2 전용 컴포넌트는 `frontend/components/v2/`에 있습니다.
- 모든 import 경로는 새로운 구조에 맞게 업데이트되었습니다.


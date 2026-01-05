# Status 필드 마이그레이션 완료

## 변경 사항

### 백엔드
- `get_latest_scan_from_db` 함수에서 `item["status"]` 필드 추가
- 도메인 상태: `ACTIVE`, `BROKEN`, `ARCHIVED`
  - `ACTIVE`: 유효한 추천 (가정 붕괴 없음)
  - `BROKEN`: 관리 필요 종목 (가정 붕괴)
  - `ARCHIVED`: 아카이브됨 (홈에서 노출하지 않음)

### 프론트엔드
- `StockCardV3.js`에서 `determineStockStatus` 함수 사용 중단
- 서버에서 내려주는 `item.status` 필드만 사용
- `mapDomainStatusToUIStatus` 함수로 도메인 상태 → UI 상태 매핑
- `status` 필드 누락 시 명시적 오류 처리

## 검증 방법

### 1. determineStockStatus 호출 확인
```bash
# 브라우저 콘솔에서 확인
# determineStockStatus가 호출되면 에러 로그가 출력됨
```

### 2. 서버 응답 확인
```bash
# API 응답에 status 필드가 포함되는지 확인
curl 'http://localhost:8010/latest-scan?scanner_version=v3' | jq '.data.items[0].status'
```

### 3. 동일 데이터 연속 렌더링 테스트
- 같은 홈 데이터를 연속으로 렌더링
- status가 변하지 않아야 함 (서버 status는 고정값)

## 회귀 방지

- `determineStockStatus` 함수가 호출되면 콘솔에 에러 로그 출력
- `status` 필드가 없으면 개발 환경에서 예외 발생
- 프로덕션에서는 기본 상태로 fallback하되 경고 로그 출력


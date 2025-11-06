# 서버와 로컬 코드 차이 요약

## 공통 변경사항 (양쪽 모두)

### 1. `backend/services/report_generator.py`
- **변경량**: 247줄 추가/수정
- **주요 개선사항**:
  - 절대 경로 사용으로 경로 문제 해결
  - 병렬 처리로 수익률 계산 성능 개선
  - 로깅 추가 (print → logger)
  - 날짜 형식 통일 (YYYY-MM-DD → YYYYMMDD)
  - 가격이 0인 경우에도 수익률 계산 시도
  - 데이터 검증 강화

### 2. `backend/models.py`
- **변경량**: 2줄 추가
- **변경내용**: `ScanResponse`에 `market_guide` 필드 추가

## 서버에만 있는 변경사항

### 1. `backend/main.py`
- **변경량**: 95줄 추가
- **주요 변경사항**:
  - `market_guide` import 추가
  - `/scan` API에 `market_guide` 생성 및 반환 추가
  - `/test-scenario/{scenario}` API에 `items_with_guide` 로직 추가
  - 보고서 API 경로 수정 (절대 경로 사용)

## 로컬에만 있는 변경사항

### 1. `backend/main.py`
- **상태**: git status에는 modified로 표시되나, git diff에는 나타나지 않음
- **추정**: 서버와 동일한 변경사항이 있거나, 아직 스테이징되지 않은 상태

### 2. 프론트엔드 변경사항
- `frontend/pages/customer-scanner.js`: 변경됨
- `frontend/components/MarketGuide.js`: 새 파일 (untracked)

### 3. 기타 파일
- `REPORT_IMPROVEMENT_PLAN.md`: 새 문서 (untracked)
- `backend/market_guide.py`: 새 파일 (untracked)
- 로그 파일들: 변경됨 (무시 가능)

## 주요 차이점

### 1. `market_guide` 관련 코드
- **서버**: `market_guide`가 `/scan`과 `/test-scenario/{scenario}` 모두에 적용됨
- **로컬**: 동일한 코드가 있는 것으로 보임 (grep 결과 동일)

### 2. 파일 상태
- **서버**: `backend/main.py`, `backend/models.py`, `backend/services/report_generator.py` 모두 변경됨
- **로컬**: `backend/main.py`는 git status에만 표시되고 git diff에는 없음

### 3. Untracked 파일
- **서버**: `backend/market_guide.py`, 보고서 파일들, `.env` 백업 파일들
- **로컬**: `REPORT_IMPROVEMENT_PLAN.md`, `backend/market_guide.py`, 프론트엔드 컴포넌트들

## 결론

1. **보고서 관련 개선**: 로컬과 서버 모두 동일하게 적용됨 ✅
2. **market_guide 기능**: 양쪽 모두 동일한 코드가 있는 것으로 보임 ✅
3. **프론트엔드**: 로컬에만 변경사항 있음 (MarketGuide 컴포넌트 등)
4. **서버에는 배포된 상태**: 보고서 생성 기능이 정상 작동 중

## 권장사항

1. 로컬의 변경사항을 커밋하고 서버에 배포
2. 프론트엔드 변경사항도 함께 배포
3. `market_guide.py` 파일이 서버에 있는지 확인


## 2025-08-10

### Backend
- CORS 추가 (`backend/main.py`)
- 모의(mock) 데이터 폴백 추가 및 강화 (`backend/kiwoom_api.py`)
  - 유니버스/시세 모의 생성, 최근 구간 랠리/거래량 스파이크로 테스트 용이화
  - `FORCE_MOCK` 환경변수로 강제 목모드 지원
  - `UNIVERSE_CODES` 환경변수로 고정 유니버스 지원
- 스캐너 조건 보정 (`backend/scanner.py`)
  - 골든크로스 최근 교차 탐지 및 임계치 완화(`MACD_OSC_MIN`, `VOL_MA5_MULT`)
- 설정 로딩 보강 (`backend/config.py`)
  - 루트 `.env` 후 `backend/.env`를 override 로드
  - `API_BASE`, `TOKEN_PATH`, `UNIVERSE_CODES` 지원
- 인증 로직 분기/정비 (`backend/auth.py`)
  - 키움 REST 토큰 스펙(JSON, secretkey) 및 에러 리포팅 강화
  - 토큰 요청 시 `api-id: au10001` 헤더 추가
- 절대 임포트로 통일 및 `backend/__init__.py` 추가

### Frontend
- API 호출 URL 구성 버그 수정 (`frontend/lib/api.js`)
  - `fetchScan()`/`fetchAnalyze()`가 base + path(`/scan`, `/analyze`)로 호출하도록 변경
  - 기본 백엔드 포트 8010으로 통일
- `.env.local`의 `NEXT_PUBLIC_BACKEND_URL` 8010으로 갱신

### Ops
- dev 실행 스크립트: 백엔드(8010), 프론트(3000)
- GitHub 원격 `origin/main`에 초기 푸시 수행 및 이후 변경사항 커밋 준비

### Known
- 키움 REST 토큰 발급: 현재 `return_code=3`(App Key/Secret 검증 실패)로 응답. 올바른 키/권한 필요

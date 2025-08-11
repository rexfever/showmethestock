## 2025-08-11

### Backend
- ka10032 경로 문서 반영: `/api/dostk/krinfo` → `/api/dostk/rkinfo` 수정, 유니버스 정상화 (`backend/config.py`, `backend/kiwoom_api.py`).
- `/_debug/topvalue`, `/_debug/stockinfo` 디버그 엔드포인트 추가로 TR 원시 응답 확인 가능 (`backend/main.py`, `backend/kiwoom_api.py`).
- OHLCV 파서 보강: 문서 샘플 필드명(`cur_prc`, `trde_qty`, `open_prc` 등) 추가 지원, 접두사 제거(6자리 코드 기본) 및 영업일 재시도 유지 (`backend/kiwoom_api.py`).
- `/analyze` 입력 정규화: `KRX:005930` → `005930` 자동 정규화 (`backend/utils.py`, `backend/main.py`).
- `/universe` 필터 옵션 추가: `apply_scan=true` 시 스캔 조건 적용된 종목만 반환 (`backend/main.py`).
- 심볼 프리로드 기본 시장코드 `KIWOOM_SYMBOL_MARKETS`를 `0,10`으로 교정.

### Frontend
- 전략 설명 섹션을 스캔 결과 상단에 추가(전략/임계치 안내) (`frontend/pages/index.js`).

### 결과
- `/universe` 정상 리스트 반환, `/scan` 기준 `universe_count=100`, `matched_count≈80+` 동작 확인.

### 기타
- 개발 서버 재시작 스크립트 정리(백엔드 8010, 프론트 3000).

---

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

---

### 추가 작업 (키움 REST 전환 고도화)
- 키움 REST 전용으로 유니버스/일봉/종목정보 TR 연결 (`ka10032` `/api/dostk/krinfo`, `ka10081` `/api/dostk/chart`, `ka10099` `/api/dostk/stkinfo`).
- `/universe` 엔드포인트 추가 및 프론트 표시.
- 유니버스 페이지네이션(cont-yn/next-key) 처리, limit까지 누적.
- 종목리스트 프리로드(기동 시 ka10099 전체 조회) 및 코드↔이름 캐시.
- 단일분석 OHLCV 보완: base_dt 미지정→전영업일 재시도, 0 값 필터.
- 스캔 매칭 로직: `MIN_SIGNALS`(기본 2) 도입.

### 다음 작업 계획
- TR 파라미터/응답 필드 최종 확정 및 에러케이스 로깅 강화(페이지네이션 키 바디/헤더 동시 탐색 보완).
- 휴장 연속 구간 자동 감지(최근 N 영업일 후퇴) 옵션 추가.
- `/scan` 결과에 조건별 실패 요인(신호 플래그) 반환하여 디버깅/튜닝 지원.
- 심볼 캐시 스냅샷(JSON) 저장/로드 도입(재시작 속도 향상), TTL 기반 리프레시.
- 프론트: 매칭 필터/정렬, 단일분석 차트 시각화(추세선/거래량) 추가.

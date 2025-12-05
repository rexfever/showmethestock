# 프로젝트 개요

**최종 업데이트**: 2025-12-05

## 프로젝트 소개

**스톡인사이트 (Stock Insight)**는 AI 기반 주식 스캐너 서비스로, 키움증권 API를 활용하여 실시간 주식 데이터를 분석하고 투자 기회를 발견합니다.

## 주요 기능

### 1. 주식 스캐닝 (국내 + 미국)

#### 국내 주식 (한국)
- **데이터 소스**: 키움증권 API (KIS API)
- **유니버스**: KOSPI/KOSDAQ 상위 종목
- **스캐너**: Scanner V1, Scanner V2

#### 미국 주식
- **데이터 소스**: Yahoo Finance Chart API
- **유니버스**: S&P 500 (500개), NASDAQ 100 (100개), 통합 (약 600개)
- **스캐너**: USScanner (Scanner V2 기반)
- **전용 모듈**: 
  - `us_stocks_universe`: 종목 리스트 관리 (Wikipedia 크롤링, 7일 캐시)
  - `us_stocks_data`: OHLCV 데이터 수집 (Chart API, 디스크 캐시)
  - `us_regime_analyzer`: 미국 시장 레짐 분석 (SPY, QQQ, VIX, DXY)
- **USD 기준 필터**: 거래대금 $1M 이상, 가격 $5 이상
- **조건 완화**: 추세 조건 4개 중 2개 (한국은 3개)

#### 공통 기능
- **지표 분석**: RSI, MACD, OBV, TEMA, DEMA 등
- **필터링**: 하드 필터(ETF 제외 등) 및 소프트 필터(신호 충족 여부)
- **점수 계산**: 종합 점수 기반 종목 랭킹 (10점 만점)
- **전략 분류**: 스윙/포지션/장기

### 2. Scanner V2 (국내/미국 통합)
- **모듈화된 구조**: 지표 계산, 필터링, 점수 계산 분리
- **DB 기반 설정**: 관리자 화면에서 스캐너 버전 선택
- **버전별 분리 저장**: v1(한국 V1), v2(한국 V2), us_v2(미국 V2)
- **국내/미국 독립 운영**: 각각 독립적인 데이터 소스 및 스캐너

### 3. 시장 분석 (국내 + 미국)

#### 한국 시장
- **장세 분석**: KOSPI 수익률 기반
- **레짐 분석**: Global Regime Analyzer v1/v3/v4
- **지표**: KOSPI, KOSPI200, VIX

#### 미국 시장
- **레짐 분석**: 미국 전용 레짐 분석기 (USRegimeAnalyzer)
- **지표**: SPY, QQQ, VIX, DXY(달러 인덱스)
- **선물 데이터**: ES=F, NQ=F 선물
- **점수 계산**: 주식(50%) + 선물(30%) + 변동성(20%)
- **레짐 분류**: bull/neutral_bull/neutral/neutral_bear/bear
- **동적 필터**: RSI 임계값(55~62), 최소 신호(2~4개), 거래량 배수(2.0~3.0)

#### 공통 기능
- **버전 선택**: DB에서 레짐 분석 버전 선택 가능 (v1, v3, v4)
- **동적 조건**: 시장 상황에 따른 필터 조건 자동 조정
- **Fallback 로직**: 결과가 부족할 때 단계적으로 조건 완화

### 4. OHLCV 캐싱 (국내/미국 분리)
- **메모리 캐시**: 빠른 접근을 위한 인메모리 캐싱
- **디스크 캐시**: 백테스트를 위한 영구 캐싱
- **동적 TTL**: 데이터 특성에 따른 캐시 유효기간 자동 조정
- **캐시 구조**: cache/ohlcv/(한국), cache/us_stocks/(미국), cache/us_futures/(선물)

## 기술 스택

### 백엔드
- **Python 3.11**: 메인 언어
- **FastAPI**: REST API 프레임워크
- **PostgreSQL 16**: 데이터베이스
- **Uvicorn**: ASGI 서버
- **Pandas/NumPy**: 데이터 분석

### 프론트엔드
- **Next.js**: React 프레임워크
- **Tailwind CSS**: 스타일링

### 인프라
- **AWS EC2**: 서버 호스팅
- **Nginx**: 리버스 프록시
- **Systemd**: 서비스 관리

## 시스템 아키텍처

```
┌─────────────┐
│   Client    │
│  (Browser)  │
└──────┬──────┘
       │
       │ HTTP/HTTPS
       │
┌──────▼─────────────────┐
│      Nginx             │
│  (Reverse Proxy)        │
└──────┬──────────────────┘
       │
       ├──────────────┬──────────────┐
       │              │              │
┌──────▼──────┐ ┌─────▼──────┐ ┌────▼─────┐
│  Frontend   │ │  Backend   │ │  DB      │
│  (Next.js)  │ │  (FastAPI) │ │(Postgres)│
│  :3000      │ │  :8010     │ │  :5432   │
└─────────────┘ └─────┬──────┘ └──────────┘
                       │
                       │ API
                       │
                ┌──────▼──────┬──────────────┐
                │  Kiwoom API │ Yahoo Finance│
                │  (한국 주식) │  (미국 주식)  │
                └─────────────┴──────────────┘
```

## 주요 디렉토리 구조

```
showmethestock/
├── backend/              # 백엔드 소스
│   ├── main.py          # FastAPI 앱
│   ├── scanner.py       # Scanner V1 (한국)
│   ├── scanner_v2/      # Scanner V2 (한국)
│   │   └── us_scanner.py # 미국 주식 스캐너
│   ├── services/        # 서비스 모듈
│   │   ├── us_stocks_universe.py  # 미국 유니버스
│   │   ├── us_stocks_data.py      # 미국 데이터
│   │   ├── us_market_data.py      # 미국 시장
│   │   └── us_regime_analyzer.py  # 미국 레짐
│   ├── cache/           # 캐시 디렉토리
│   │   ├── ohlcv/       # 한국 주식
│   │   ├── us_stocks/   # 미국 주식
│   │   └── us_futures/  # 미국 선물
│   ├── sql/             # DB 스키마
│   └── tests/           # 테스트
├── frontend/            # 프론트엔드 소스
│   ├── pages/           # Next.js 페이지
│   │   ├── customer-scanner.js    # 한국 V1
│   │   └── v2/
│   │       ├── scanner-v2.js      # 한국 V2
│   │       └── us-stocks-scanner.js # 미국
│   └── components/      # React 컴포넌트
├── docs/                # 문서
│   ├── deployment/      # 배포 메뉴얼
│   ├── scanner-v2/      # Scanner V2 문서
│   └── database/        # DB 스키마 문서
└── backend/archive/     # 아카이브 파일
```

## 데이터 흐름

### 스캔 프로세스

1. **유니버스 조회**
   - 키움 API로 KOSPI/KOSDAQ 상위 종목 조회
   - 거래대금 기준 상위 N개 선택

2. **OHLCV 데이터 수집**
   - 각 종목의 OHLCV 데이터 조회
   - 캐시 확인 → 없으면 API 호출 → 캐시 저장

3. **지표 계산**
   - RSI, MACD, OBV 등 기술적 지표 계산
   - 추세 분석 (TEMA, DEMA)

4. **필터링**
   - 하드 필터: ETF 제외, 가격 필터 등
   - 소프트 필터: 신호 충족 여부 확인

5. **점수 계산**
   - 종합 점수 산정
   - 전략 분류 (스윙/포지션/장기)

6. **결과 저장**
   - DB에 스캔 결과 저장
   - 버전별 분리 저장 (V1/V2)

## 주요 설정

### 환경 변수
- `DATABASE_URL`: PostgreSQL 연결 문자열
- `APP_KEY`, `APP_SECRET`: 키움 API 인증 정보
- `SCANNER_VERSION`: 스캐너 버전 (v1/v2)
- `SCANNER_V2_ENABLED`: V2 활성화 여부

### DB 설정
- `scanner_settings` 테이블에서 스캐너 버전 및 레짐 분석 버전 관리
  - `scanner_version`: v1 또는 v2
  - `scanner_v2_enabled`: true 또는 false
  - `regime_version`: v1, v3, 또는 v4
- `.env` 파일은 fallback으로 사용

## 빠른 시작

### 로컬 개발 환경 구성
1. [로컬 개발 환경 구성 메뉴얼](./deployment/LOCAL_DEVELOPMENT_SETUP.md) 참조
2. PostgreSQL 설치 및 데이터베이스 생성
3. 환경 변수 설정
4. 백엔드/프론트엔드 실행

### 서버 배포
1. [서버 운영 메뉴얼](./deployment/SERVER_OPERATION_MANUAL.md) 참조
2. 코드 업데이트
3. DB 마이그레이션 (필요시)
4. 서비스 재시작

## 관련 문서

### 필수 메뉴얼
- [로컬 개발 환경 구성](./deployment/LOCAL_DEVELOPMENT_SETUP.md)
- [서버 운영 메뉴얼](./deployment/SERVER_OPERATION_MANUAL.md)
- [포트 설정 중앙화 가이드](./deployment/PORT_CONFIGURATION.md)
- [API 엔드포인트](./API_ENDPOINTS.md)

### 기능별 문서
- [Scanner V2 사용 가이드](./scanner-v2/SCANNER_V2_USAGE.md)
- [Scanner V2 설계](./scanner-v2/SCANNER_V2_DESIGN.md)
- [V1 vs V2 비교](./scanner-v2/V1_VS_V2_COMPARISON.md)
- [미국 주식 스캐너 기술 가이드](./scanner-v2/US_SCANNER_TECHNICAL_GUIDE.md)
- [레짐 분석 가이드](./strategy/REGIME_ANALYSIS.md)

### 데이터베이스
- [스캐너 설정 테이블](./database/SCANNER_SETTINGS_TABLE.md)
- [스캔 결과 테이블](./database/SCAN_RANK_TABLE.md)
- [팝업 공지 테이블](./database/POPUP_NOTICE_TABLE.md)

### 기술 문서
- [OHLCV 디스크 캐시 구현](./code-review/OHLCV_DISK_CACHE_IMPLEMENTATION.md)
- [날짜 처리 개선](./code-review/DATE_FORMAT_HANDLING.md)
- [스캐닝 프로세스 검증](./code-review/SCANNING_PROCESS_VERIFICATION.md)
- [미국 주식 스캐너 최종 요약](./US_STOCK_SCANNER_FINAL_SUMMARY.md)

## 개발 워크플로우

1. **로컬 개발**
   - 코드 수정
   - 로컬 테스트
   - Git 커밋

2. **GitHub 푸시**
   - `git push origin main`

3. **서버 배포**
   - 서버에서 `git pull`
   - DB 마이그레이션 (필요시)
   - 서비스 재시작

## 문제 해결

### 종합 가이드
- [문제 해결 가이드](./TROUBLESHOOTING_GUIDE.md) - 모든 문제 해결 방법 통합

### 세부 가이드
- [로컬 개발 메뉴얼 - 문제 해결](./deployment/LOCAL_DEVELOPMENT_SETUP.md#문제-해결)
- [서버 운영 메뉴얼 - 문제 해결](./deployment/SERVER_OPERATION_MANUAL.md#문제-해결)
- [DB 접속 및 작업 방법](./deployment/LOCAL_DEVELOPMENT_SETUP.md#데이터베이스-접속-및-작업)

## 참고

- **GitHub**: https://github.com/rexfever/showmethestock
- **프로덕션 URL**: https://sohntech.ai.kr
- **문서 업데이트**: 2025-12-05


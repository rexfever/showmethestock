# API 엔드포인트 문서

## 개요

Stock Scanner API의 주요 엔드포인트 목록입니다.

## 공개 엔드포인트

### 헬스 체크

```http
GET /health
```

서비스 상태 확인

### 환경 정보

```http
GET /environment
```

현재 환경 정보 반환

### 스캔 (한국 주식)

```http
GET /scan?date=YYYYMMDD&kospi_limit=25&kosdaq_limit=25&save_snapshot=true&sort_by=score
```

한국 주식 스캔 실행 및 결과 반환

**파라미터:**
- `date`: 스캔 날짜 (YYYYMMDD 형식, 선택사항, 기본값: 오늘)
- `kospi_limit`: KOSPI 종목 수 제한 (선택사항)
- `kosdaq_limit`: KOSDAQ 종목 수 제한 (선택사항)
- `save_snapshot`: 스냅샷 저장 여부 (기본값: true)
- `sort_by`: 정렬 기준 (기본값: score)

**레짐 분석:**
- `market_analysis_enable` 설정이 활성화된 경우 자동으로 레짐 분석 실행
- Global Regime v4 사용 (한국+미국 통합 분석)
- 레짐 분석 결과는 필터링 조건 조정 및 cutoff 적용에 사용

**응답:**
```json
{
  "as_of": "20251124",
  "universe_count": 50,
  "matched_count": 5,
  "items": [
    {
      "ticker": "005930",
      "name": "삼성전자",
      "score": 9.2,
      "current_price": 70400,
      "change_rate": 1.59,
      "indicators": {...},
      "strategy": "Swing"
    }
  ]
}
```

### 스캔 (미국 주식)

```http
GET /scan/us-stocks?universe_type=combined&limit=500&date=YYYYMMDD&save_snapshot=true
```

미국 주식 스캔 실행 및 결과 반환

**파라미터:**
- `universe_type`: 유니버스 타입 ('sp500', 'nasdaq100', 'combined', 기본값: 'sp500')
- `limit`: 최대 종목 수 (기본값: 500)
- `date`: 스캔 날짜 (YYYYMMDD 형식, 선택사항, 기본값: 오늘)
- `save_snapshot`: 스캔 결과를 DB에 저장할지 여부 (기본값: true)

**레짐 분석:**
- `market_analysis_enable` 설정이 활성화된 경우 자동으로 레짐 분석 실행
- Global Regime v4 사용 (한국+미국 통합 분석)
- 레짐 분석 결과는 필터링 조건 조정 및 cutoff 적용에 사용
- 레짐 기반 cutoff: 레짐별 전략별 점수 기준 적용
  - bull: swing 6.0, position 4.3 (완화)
  - neutral: swing 6.0, position 4.5
  - bear: swing 999.0, position 5.5 (강화)
  - crash: swing 999.0, position 999.0 (비활성화)

**응답:**
```json
{
  "as_of": "20251205",
  "universe_count": 600,
  "matched_count": 15,
  "items": [
    {
      "ticker": "AAPL",
      "name": "Apple Inc.",
      "score": 8.5,
      "current_price": 150.0,
      "change_rate": 1.5,
      "indicators": {...},
      "strategy": "Swing"
    }
  ]
}
```

### 최신 스캔 결과

```http
GET /latest-scan
```

DB에서 최신 스캔 결과 조회

### 특정 날짜 스캔 결과

```http
GET /scan-by-date/{date}
```

특정 날짜의 스캔 결과 조회 (YYYYMMDD 형식)

### 팝업 공지 상태

```http
GET /popup-notice/status
```

현재 활성화된 팝업 공지 조회 (인증 불필요)

**응답:**
```json
{
  "is_enabled": true,
  "title": "공지 제목",
  "message": "공지 내용",
  "start_date": "20251124",
  "end_date": "20251130"
}
```

### 종목 분석

```http
GET /analyze?name_or_code=삼성전자
GET /analyze-friendly?name_or_code=005930
```

종목 분석 결과 반환

### 유니버스

```http
GET /universe
```

스캔 대상 유니버스 종목 목록

---

## 인증 필요 엔드포인트

### 인증

```http
POST /auth/social-login
POST /auth/email/signup
POST /auth/email/login
POST /auth/email/verify
GET /auth/me
POST /auth/logout
```

### 포트폴리오

```http
GET /portfolio
POST /portfolio/add
PUT /portfolio/{ticker}
DELETE /portfolio/{ticker}
GET /portfolio/summary
```

### 매매 내역

```http
POST /trading-history
GET /trading-history
DELETE /trading-history/{trading_id}
```

### 구독 및 결제

```http
GET /subscription/plans
GET /subscription/status
POST /payment/create
POST /payment/approve
POST /subscription/cancel
GET /subscription/history
```

---

## 관리자 전용 엔드포인트

### 사용자 관리

```http
GET /admin/users
GET /admin/users/{user_id}
PUT /admin/users/{user_id}
DELETE /admin/users/{user_id}
GET /admin/stats
```

### 스캐너 설정

```http
GET /admin/scanner-settings
POST /admin/scanner-settings
```

**요청 예시:**
```json
{
  "scanner_version": "v2",
  "scanner_v2_enabled": true
}
```

### 팝업 공지 관리

```http
GET /admin/popup-notice
POST /admin/popup-notice
```

**요청 예시:**
```json
{
  "is_enabled": true,
  "title": "공지 제목",
  "message": "공지 내용",
  "start_date": "20251124",
  "end_date": "20251130"
}
```

### 메인트넌스 설정

```http
GET /admin/maintenance
POST /admin/maintenance
GET /maintenance/status
```

### 트렌드 분석

```http
GET /admin/trend-analysis
POST /admin/trend-apply
```

### 시장 검증

```http
GET /admin/market-validation
```

---

## 응답 모델

### ScanItem

```typescript
{
  ticker: string;
  name: string;
  score: number;
  current_price: number;      // 현재가
  change_rate: number;        // 등락률 (퍼센트, 예: 1.59 = 1.59%)
  indicators: {
    TEMA: number;
    DEMA: number;
    RSI_TEMA: number;
    close: number;
    change_rate: number;
    // ...
  };
  strategy: string;           // Swing, Position, Long-term
  returns?: {
    current_return: number;
    max_return: number;
    min_return: number;
    days_elapsed: number;
  };
}
```

### ScanResponse

```typescript
{
  as_of: string;              // YYYYMMDD 형식
  universe_count: number;
  matched_count: number;
  items: ScanItem[];
  fallback_step?: number;     // Fallback 단계 (있는 경우)
  scanner_version?: string;    // 사용된 스캐너 버전
  market_guide?: object;       // 시장 가이드
}
```

---

## 주요 변경사항

### 2025-12-06

1. **미국 주식 스캔 레짐 분석 적용**
   - Global Regime v4 사용 (한국+미국 통합 분석)
   - 레짐 기반 cutoff 적용 (레짐별 전략별 점수 기준)
   - 레짐 기반 필터링 조건 조정 (RSI 임계값, 최소 신호 개수, 거래량 배수)
   - 강세장 조건 완화: bull market에서 필터링 완화

2. **미국 주식 스캔 API 엔드포인트**
   - `/scan/us-stocks` 엔드포인트 추가
   - 레짐 분석 자동 실행 (설정 활성화 시)
   - 레짐 기반 cutoff 및 필터링 조건 조정

### 2025-11-24

1. **ScanItem 모델 확장**
   - `current_price` 필드 추가
   - `change_rate` 필드 추가 (최상위 레벨)

2. **등락률 형식 통일**
   - `change_rate`는 퍼센트로 저장 및 반환 (예: `1.59` = 1.59%)
   - 기존 소수 형식 데이터는 자동 변환

3. **스캐너 버전 관리**
   - DB 기반 설정 관리 (`scanner_settings` 테이블)
   - 관리자 UI에서 버전 선택 가능
   - V1과 V2 스캔 결과 별도 저장 (`scan_rank` 테이블의 `scanner_version` 컬럼)

4. **팝업 공지 기능**
   - 관리자 UI에서 팝업 공지 설정 가능
   - 날짜 범위 기반 자동 활성화/비활성화

---

## 에러 응답

```json
{
  "detail": "에러 메시지"
}
```

**주요 HTTP 상태 코드:**
- `200`: 성공
- `400`: 잘못된 요청
- `401`: 인증 필요
- `403`: 권한 없음
- `404`: 리소스 없음
- `500`: 서버 오류

---

## 참고사항

- 모든 날짜는 `YYYYMMDD` 형식 사용
- 인증이 필요한 엔드포인트는 `Authorization: Bearer <token>` 헤더 필요
- 관리자 엔드포인트는 관리자 권한 필요


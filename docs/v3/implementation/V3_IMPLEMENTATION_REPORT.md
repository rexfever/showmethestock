# V3 스캐너 구현 리포트

**작성일**: 2025-12-28  
**버전**: Scanner V3  
**목적**: 중기(midterm) + 단기(v2-lite) 조합 알고리즘 기반 추천 종목 서비스

---

## 📋 목차

1. [프론트엔드 구현](#프론트엔드-구현)
2. [백엔드 구현](#백엔드-구현)
3. [주요 기능](#주요-기능)
4. [데이터 흐름](#데이터-흐름)
5. [주요 개선 사항](#주요-개선-사항)

---

## 🎨 프론트엔드 구현

### 1. 페이지 컴포넌트

#### `frontend/pages/v3/scanner-v3.js`
- **역할**: V3 스캐너 메인 페이지
- **주요 기능**:
  - 인피니티 스크롤 기반 날짜별 스캔 결과 표시
  - SSR(Server-Side Rendering) 데이터 활용
  - 날짜별 섹션 자동 로드
  - 타임아웃 최적화 (SSR: 3초, 클라이언트: 5초)
- **API 호출**:
  - `/latest-scan?scanner_version=v3` - 최신 스캔 결과
  - `/scan-by-date/{date}?scanner_version=v3` - 특정 날짜 스캔 결과
- **상태 관리**:
  - `dateSections`: 날짜별 스캔 결과 저장
  - `loading`, `loadingMore`: 로딩 상태
  - `hasMore`: 추가 데이터 존재 여부

### 2. 종목 카드 컴포넌트

#### `frontend/components/v3/StockCardV3.js`
- **역할**: V3 전용 종목 카드 (사용자 행동 안내 중심 UX)
- **주요 특징**:
  - 숫자/점수/엔진명 기본 카드에서 숨김
  - 상태 중심 UI (5가지 상태)
  - 상세 정보는 드로어에서만 표시
- **상태 판별 로직**:
  ```javascript
  - BEFORE_ENTRY: 추천일 없음
  - OBSERVING: 추천 후 관찰 중 (목표 30% 이상)
  - RECOMMENDED_PROGRESS: 목표 수익률 달성
  - WEAK_WARNING: 목표 30% 미만 또는 음수 (2일 이후)
  - STRONG_WARNING: 손절 기준 도달 (2일 이후)
  ```
- **상태별 문구**:
  - 진입 전: "아직 진입할 타이밍은 아닙니다"
  - 관찰: "움직임을 관찰 중입니다"
  - 추천/목표 진행: "추천 이후 흐름이 유지되고 있습니다"
  - 약한 경고: "흐름이 다소 약해지고 있습니다"
  - 강한 경고: "손실이 커지고 있습니다"
- **데이터 안전성 처리**:
  - `flags`, `returns` JSON 파싱 (문자열일 수 있음)
  - `current_return` 다중 경로 확인
  - `recommended_date` 형식 변환 (숫자/문자열)
  - `days_elapsed` 계산 (추천 직후 경고 방지)
- **손절 기준 계산**:
  - `stop_loss: 0.02` → `-2.0%`로 변환하여 비교
  - 추천 후 1일 이내에는 손절 경고 표시 안 함

### 3. 날짜별 섹션 컴포넌트

#### `frontend/components/v3/V3DateSection.js`
- **역할**: 날짜별 스캔 결과 섹션 표시
- **주요 기능**:
  - V3 케이스별 UI 분기 (A/B/C/D)
  - 추천 없는 날(케이스 D) 단일 안내 카드 표시
  - 장세 카드(V3MarketRegimeCard) 통합
  - StockCardV3 컴포넌트 사용
- **케이스별 처리**:
  - 케이스 A/B/C: 추천 종목 리스트 표시
  - 케이스 D: "오늘은 무리해서 들어갈 장이 아닙니다" 안내 카드

### 4. 장세 카드 컴포넌트

#### `frontend/components/v3/V3MarketRegimeCard.js`
- **역할**: V3 장세 정보 표시
- **표시 내용**:
  - 활성 엔진 정보 (v2lite, midterm)
  - 엔진별 라벨 (단기 반응형, 중기 추세형)
  - 스캔 날짜

---

## ⚙️ 백엔드 구현

### 1. API 엔드포인트

#### `/latest-scan?scanner_version=v3`
- **위치**: `backend/main.py` - `get_latest_scan_from_db()`
- **기능**: 최신 V3 스캔 결과 조회
- **반환 데이터**:
  ```json
  {
    "ok": true,
    "data": {
      "as_of": "YYYYMMDD",
      "items": [...],
      "market_condition": {...},
      "v3_case_info": {
        "has_recommendations": true,
        "active_engines": ["v2lite", "midterm"],
        "scan_date": "YYYY-MM-DD",
        "engine_labels": {
          "v2lite": "단기 반응형",
          "midterm": "중기 추세형"
        }
      }
    }
  }
  ```
- **v3_case_info 생성 로직**:
  - `strategy` 필드로 v2lite/midterm 분류
  - `has_recommendations`: 실제 추천 종목 존재 여부
  - `active_engines`: 활성 엔진 리스트

#### `/scan-by-date/{date}?scanner_version=v3`
- **위치**: `backend/main.py` - `get_scan_by_date()`
- **기능**: 특정 날짜의 V3 스캔 결과 조회
- **쿼리 로직**:
  ```sql
  SELECT ... FROM scan_rank
  WHERE date = %s AND scanner_version = 'v3'
  ORDER BY 
    CASE WHEN code = 'NORESULT' THEN 0 ELSE 1 END,
    CASE strategy
      WHEN 'v2_lite' THEN 1
      WHEN 'midterm' THEN 2
      ELSE 3
    END,
    CASE WHEN code = 'NORESULT' THEN 0 ELSE score END DESC
  ```
- **데이터 처리**:
  - `strategy` 필드로 엔진 구분
  - `flags`에 매매 가이드 정보 포함
  - `returns`에 수익률 정보 포함
  - `recurrence`에 재등장 정보 포함

### 2. V3 엔진 코어

#### `backend/scanner_v3/core/engine.py`
- **클래스**: `ScannerV3`
- **주요 기능**:
  - 중기(midterm) + 단기(v2-lite) 엔진 조합
  - 두 엔진 결과 병합하지 않음 (독립적)
  - 레짐 분석 기반 v2-lite 실행 여부 결정
- **운영 원칙**:
  1. midterm은 항상 실행
  2. v2-lite는 neutral/normal 레짐에서만 실행
  3. 두 엔진의 결과는 절대 병합하지 않음
  4. 두 엔진은 서로의 fallback, ranking, score, filter에 영향을 주지 않음

### 3. 데이터베이스 스키마

#### `scan_rank` 테이블
- **V3 관련 필드**:
  - `scanner_version`: 'v3'
  - `strategy`: 'v2_lite' 또는 'midterm'
  - `flags`: JSON (target_profit, stop_loss, holding_period)
  - `returns`: JSON (current_return, max_return, min_return, days_elapsed)
  - `recurrence`: JSON (재등장 정보)

### 4. 데이터 처리 로직

#### 수익률 계산
- **위치**: `backend/main.py` - `get_scan_by_date()`, `get_latest_scan_from_db()`
- **로직**:
  - `recommended_price`: 스캔일 종가 또는 최초 추천가(재등장 종목)
  - `recommended_date`: 스캔일 또는 최초 추천일(재등장 종목)
  - `current_return`: `((현재가 - 추천가) / 추천가) * 100`
  - `days_elapsed`: 추천일로부터 경과 일수

#### 매매 가이드 기본값
- **v2_lite 전략**:
  - `target_profit`: 5% (0.05)
  - `stop_loss`: 2% (0.02)
  - `holding_period`: 14일
- **midterm 전략**:
  - `target_profit`: 10% (0.10)
  - `stop_loss`: 7% (0.07)
  - `holding_period`: 15일

---

## 🎯 주요 기능

### 1. 상태 기반 UX
- 숫자/점수/엔진명 숨김
- 상태 중심 문구 표시
- 행동 가이드 제공
- 상세 정보는 드로어에서만 표시

### 2. 추천 없는 날 처리
- 케이스 D: 단일 안내 카드만 표시
- "오늘은 무리해서 들어갈 장이 아닙니다" 문구
- 종목 카드 리스트 숨김

### 3. 인피니티 스크롤
- 날짜별 섹션 자동 로드
- 이전 거래일 자동 조회
- 빈 데이터 건너뛰기 로직

### 4. 성능 최적화
- SSR 데이터 활용
- 타임아웃 단축 (SSR: 3초, 클라이언트: 5초)
- 중복 API 호출 방지

---

## 📊 데이터 흐름

```
1. 사용자 접속
   ↓
2. SSR: /latest-scan?scanner_version=v3
   ↓
3. 백엔드: scan_rank 테이블 조회 (scanner_version='v3')
   ↓
4. v3_case_info 생성 (strategy 기반)
   ↓
5. 프론트엔드: V3DateSection 렌더링
   ↓
6. StockCardV3: 상태 판별 및 표시
   ↓
7. 사용자 스크롤 → /scan-by-date/{date}?scanner_version=v3
   ↓
8. 이전 날짜 데이터 자동 로드
```

---

## 🔧 주요 개선 사항

### 프론트엔드

1. **데이터 안전성 강화**
   - JSON 파싱 처리 (flags, returns)
   - 타입 변환 (recommended_date, recommended_price)
   - null/undefined 체크

2. **상태 판별 로직 개선**
   - 추천 직후(1일 이내) 손절 경고 방지
   - days_elapsed 계산 추가
   - 손절 기준 음수 변환 (-2%)

3. **UX 개선**
   - 상태 중심 문구
   - 행동 가이드 제공
   - 상세 정보 드로어

### 백엔드

1. **v3_case_info 추가**
   - strategy 기반 엔진 분류
   - has_recommendations 플래그
   - active_engines 리스트

2. **데이터 일관성**
   - recommended_date/recommended_price 처리
   - current_return 계산
   - days_elapsed 포함

---

## 📝 파일 목록

### 프론트엔드
- `frontend/pages/v3/scanner-v3.js` - V3 메인 페이지
- `frontend/components/v3/StockCardV3.js` - V3 종목 카드
- `frontend/components/v3/V3DateSection.js` - 날짜별 섹션
- `frontend/components/v3/V3MarketRegimeCard.js` - 장세 카드

### 백엔드
- `backend/main.py` - API 엔드포인트 (`/latest-scan`, `/scan-by-date`)
- `backend/scanner_v3/core/engine.py` - V3 엔진 코어
- `backend/services/scan_service.py` - 스캔 서비스

---

## 🚀 향후 개선 방향

1. **A/B 테스트 지원**
   - STATUS_MESSAGES 상수 분리 완료
   - 문구 변경 용이

2. **성능 최적화**
   - 캐싱 전략 개선
   - 배치 로딩 최적화

3. **에러 처리 강화**
   - 네트워크 에러 처리
   - 데이터 불일치 처리

---

**작성자**: AI Assistant  
**최종 수정일**: 2025-12-28


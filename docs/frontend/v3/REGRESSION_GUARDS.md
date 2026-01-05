# v3 회귀 방지 가드레일

## 개요
v3 홈 화면의 핵심 기능이 회귀되지 않도록 하는 가드레일 모음

---

## 백엔드 가드레일

### 1. v3 홈 API 재계산 차단 강제
**위치**: `backend/main.py`

**구현**:
- `disable_recalculate_returns=True` 강제 주입
- `calculate_returns` 호출 시도 시 경고 로그 + 메트릭 증가
- 개발/테스트 환경에서는 예외 throw

**로그 패턴**:
```
⚠️ [V3_HOME_GUARD] calculate_returns 호출 시도 차단: code=..., scanner_version=..., formatted_date=...
```

**메트릭**:
- `v3_home_request`: v3 홈 API 호출 카운트
- `v3_home_recalc_attempt`: 재계산 시도 카운트 (0이어야 함)

---

### 2. API 계약 체크 (status 필수)
**위치**: `backend/main.py` - `get_latest_scan` 엔드포인트

**구현**:
- v3 홈 응답의 모든 아이템에 `status` 필드 확인
- 누락 시 경고 로그 + "UNKNOWN"으로 대체

**로그 패턴**:
```
[V3_HOME_GUARD] status 필드 누락: ticker=..., name=...
[V3_HOME_GUARD] status 누락 레코드 N개 발견
```

---

## 프론트엔드 가드레일

### 3. 숫자 금지 테스트
**위치**: `frontend/__tests__/v3/cardNoNumbers.test.js`

**구현**:
- `ActiveStockCardV3`, `BrokenStockCardV3` 렌더 결과 검증
- 금지 패턴: `원`, `%`, `KRW`, `USD`, 천단위 구분 숫자, 소수점 숫자

**실행**:
```bash
cd frontend
npm test -- __tests__/v3/cardNoNumbers.test.js
```

---

### 4. status 계산 로직 재도입 방지
**위치**: `frontend/scripts/check-status-calculation.sh`

**구현**:
- v3 파일에서 금지된 함수명 검색
- 금지 패턴: `determineStockStatus`, `calculateStockStatus`, `getStockStatus`, `computeStatus`

**실행**:
```bash
./frontend/scripts/check-status-calculation.sh
```

**CI 통합**:
```yaml
# .github/workflows/ci.yml (예시)
- name: Check status calculation logic
  run: ./frontend/scripts/check-status-calculation.sh
```

---

### 5. 섹션 혼입 방지 (런타임 assert)
**위치**: `frontend/pages/v3/scanner-v3.js`

**구현**:
- 개발 모드에서 섹션 혼입 감지 시 `console.error`
- BROKEN 섹션에 ACTIVE가 들어가면 경고
- ACTIVE 섹션에 BROKEN이 들어가면 경고

**로그 패턴**:
```
[ScannerV3] 섹션 혼입 감지: BROKEN 섹션에 ACTIVE 아이템 발견
[ScannerV3] 섹션 혼입 감지: ACTIVE 섹션에 BROKEN 아이템 발견
```

---

## 자동화된 테스트

### 백엔드
**파일**: `backend/tests/test_v3_status_immutability.py`

**테스트 항목**:
1. 동일 요청에서 상태 동일성
2. 시간 간격을 둔 요청에서 상태 동일성
3. status 필드 필수 확인
4. calculate_returns 호출 여부 확인

**실행**:
```bash
cd backend
python3 -m pytest tests/test_v3_status_immutability.py -v
```

---

### 프론트엔드
**파일**: `frontend/__tests__/v3/cardNoNumbers.test.js`

**테스트 항목**:
1. ActiveStockCardV3 숫자 노출 금지
2. BrokenStockCardV3 숫자 노출 금지
3. 숫자가 포함된 종목명도 정상 렌더링

**실행**:
```bash
cd frontend
npm test -- __tests__/v3/cardNoNumbers.test.js
```

---

## QA 시나리오

**문서**: `frontend/pages/v3/QA_REGRESSION_TEST.md`

**최소 시나리오**:
- 케이스 A: ACTIVE만 존재
- 케이스 B: BROKEN만 존재
- 케이스 C: ACTIVE + BROKEN 동시 존재
- 케이스 D: ACTIVE 개수에 따른 접힘 기본 동작
- 케이스 E: 신규 발생 당일 1회 자동 펼침
- 케이스 F: 동일 인스턴스 오전/오후 조회 시 상태 동일

---

## CI/CD 통합

### 권장 CI 단계
1. **백엔드 테스트**:
   ```bash
   python3 -m pytest backend/tests/test_v3_status_immutability.py
   ```

2. **프론트엔드 테스트**:
   ```bash
   npm test -- __tests__/v3/cardNoNumbers.test.js
   ```

3. **status 계산 로직 체크**:
   ```bash
   ./frontend/scripts/check-status-calculation.sh
   ```

4. **린트 체크** (v3 파일):
   ```bash
   npm run lint -- frontend/components/v3 frontend/pages/v3
   ```

---

## 모니터링

### 백엔드 로그 모니터링
- `[V3_HOME_GUARD]` 패턴 검색
- `v3_home_recalc_attempt` 메트릭 모니터링 (0이어야 함)

### 프론트엔드 콘솔 모니터링
- 개발 모드에서 `[ScannerV3] 섹션 혼입 감지` 경고 확인

---

## 문제 발견 시 조치

1. **재계산 시도 감지**:
   - 백엔드 로그 확인
   - `disable_recalculate_returns` 파라미터 확인
   - `calculate_returns` 호출 경로 추적

2. **카드 숫자 노출**:
   - `ActiveStockCardV3`, `BrokenStockCardV3` 컴포넌트 확인
   - 금지 패턴 검색

3. **섹션 혼입**:
   - 개발 모드 console.error 확인
   - 분류 로직 확인

4. **status 계산 로직 재도입**:
   - `check-status-calculation.sh` 실행
   - 금지된 함수명 사용 여부 확인

---

## 참고

- 모든 가드레일은 최소한의 오버헤드로 동작
- 개발/테스트 환경에서는 더 엄격하게 동작
- 운영 환경에서는 로깅/메트릭으로 모니터링


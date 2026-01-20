# v3 홈 화면 회귀 테스트 시나리오

## 목적
v3 홈 화면의 핵심 기능이 회귀되지 않았는지 확인하기 위한 최소 테스트 시나리오

---

## 필수 검증 항목

### 1. 상태 불변성 (가장 중요)
**목적**: GET 요청만으로 상태가 바뀌지 않음을 확인

**시나리오**:
1. 동일한 추천 인스턴스(rec_instance_id)에 대해 홈 API를 오전/오후에 연속 호출
2. 각 호출에서 반환된 `status` 값이 동일한지 확인
3. `current_return` 값이 변하지 않는지 확인 (v3 홈에서는 재계산 금지)

**기대 결과**:
- `status` 값이 동일해야 함 (ACTIVE → ACTIVE, BROKEN → BROKEN)
- `current_return` 값이 동일해야 함 (재계산 없음)

**자동화 가능**: ✅ (스크립트로 구현 가능)

---

### 2. 카드 숫자 노출 금지
**목적**: 홈 카드에 가격/수익률 등 숫자가 노출되지 않음을 확인

**시나리오**:
1. ACTIVE 카드 렌더링
2. BROKEN 카드 렌더링
3. 각 카드의 HTML/텍스트에서 금지 패턴 검색:
   - '원', '%', 'KRW', 'USD'
   - 천단위 구분 숫자 (예: 1,000)
   - 소수점 숫자 (예: 12.34)

**기대 결과**:
- 금지 패턴이 0개여야 함

**자동화 가능**: ✅ (Jest 테스트로 구현됨)

---

### 3. 섹션 혼입 방지
**목적**: BROKEN 섹션에 ACTIVE가, ACTIVE 섹션에 BROKEN이 들어가지 않음을 확인

**시나리오**:
1. ACTIVE만 존재하는 경우
2. BROKEN만 존재하는 경우
3. ACTIVE + BROKEN 동시 존재하는 경우
4. 각 섹션의 아이템 `status` 값 확인

**기대 결과**:
- BROKEN 섹션의 모든 아이템은 `status === 'BROKEN'`
- ACTIVE 섹션의 모든 아이템은 `status === 'ACTIVE'`

**자동화 가능**: ✅ (개발 모드에서 console.error로 감지)

---

## 케이스별 테스트 시나리오

### 케이스 A: ACTIVE만 존재
**조건**: ACTIVE 아이템만 있고 BROKEN이 없는 경우

**검증 항목**:
1. ACTIVE 섹션만 표시됨
2. BROKEN 섹션이 숨김 처리됨
3. ACTIVE 카드에 숫자 노출 없음
4. 신규 ACTIVE가 있으면 상단에 표시됨

**신규 0개인 경우**:
- ACTIVE 섹션 헤더에 "유효한 추천 X개" 표시
- "신규" 배지 없음

**신규 >0개인 경우**:
- ACTIVE 섹션 헤더에 "유효한 추천 X개 (신규 Y)" 표시
- 신규 ACTIVE에 "신규" 배지 표시
- 당일 1회 자동 펼침 동작 (localStorage 확인)

---

### 케이스 B: BROKEN만 존재
**조건**: BROKEN 아이템만 있고 ACTIVE가 없는 경우

**검증 항목**:
1. BROKEN 섹션만 표시됨
2. ACTIVE 섹션이 숨김 처리됨
3. BROKEN 카드에 숫자 노출 없음
4. BROKEN 카드 클릭 시 상세 화면으로 이동
5. 상세 화면 진입 시 자동 ack 호출 (네트워크 탭 확인)
6. ack 후 홈으로 돌아오면 해당 BROKEN이 사라짐

**ack 전**:
- BROKEN 섹션에 해당 아이템 표시
- 헤더에 개수 배지 표시

**ack 후**:
- BROKEN 섹션에서 해당 아이템 제거
- 다른 사용자에게는 여전히 표시됨 (사용자별 숨김)

---

### 케이스 C: ACTIVE + BROKEN 동시 존재
**조건**: ACTIVE와 BROKEN이 모두 있는 경우

**검증 항목**:
1. BROKEN 섹션이 ACTIVE 섹션 위에 표시됨
2. 각 섹션에 올바른 아이템만 포함됨 (혼입 없음)
3. 각 섹션의 접힘/펼침이 독립적으로 동작
4. 각 섹션의 헤더 정보가 정확함:
   - BROKEN: 개수 배지
   - ACTIVE: "X개 (신규 Y)" 요약

---

### 케이스 D: ACTIVE 개수에 따른 접힘 기본 동작
**조건**: ACTIVE 개수가 6개 미만/이상인 경우

**ACTIVE < 6개**:
- 기본 상태: 펼침 (collapsed=false)
- localStorage에 값이 없으면 펼침

**ACTIVE >= 6개**:
- 기본 상태: 접힘 (collapsed=true)
- localStorage에 값이 없으면 접힘

**검증 항목**:
1. ACTIVE_COLLAPSE_THRESHOLD = 6 기준으로 동작
2. localStorage 값이 있으면 그 값 우선
3. 사용자 토글 시 localStorage에 저장

---

### 케이스 E: 신규 발생 당일 1회 자동 펼침
**조건**: 오늘 새 BROKEN/ACTIVE가 발생한 경우

**검증 항목**:
1. 새 BROKEN 발생 시:
   - 당일 1회만 자동 펼침
   - localStorage에 `v3.autoExpand.broken.lastDate` 저장
   - 다음 날에는 자동 펼침 안 됨

2. 새 ACTIVE 발생 시:
   - 당일 1회만 자동 펼침
   - localStorage에 `v3.autoExpand.active.lastDate` 저장
   - 다음 날에는 자동 펼침 안 됨

3. 사용자 토글 후에는 자동 펼침 무시

---

### 케이스 F: 동일 인스턴스 오전/오후 조회 시 상태 동일
**목적**: GET 요청만으로 상태가 바뀌지 않음을 확인

**시나리오**:
1. 오전에 홈 API 호출 → 특정 아이템의 `status` 기록
2. 오후에 동일한 홈 API 호출 → 동일한 아이템의 `status` 확인
3. 백엔드 로그에서 `calculate_returns` 호출 여부 확인

**기대 결과**:
- `status` 값이 동일해야 함
- 백엔드 로그에 `[V3_HOME_GUARD]` 경고가 없어야 함
- `v3_home_recalc_attempt` 메트릭이 증가하지 않아야 함

**자동화 가능**: ✅ (스크립트로 구현 가능)

---

## 자동화된 테스트

### 1. 카드 숫자 노출 테스트
```bash
cd frontend
npm test -- __tests__/v3/cardNoNumbers.test.js
```

### 2. status 계산 로직 재도입 체크
```bash
./frontend/scripts/check-status-calculation.sh
```

### 3. 상태 불변성 테스트 (구현 필요)
```bash
# TODO: backend/tests/test_v3_status_immutability.py
```

---

## 수동 테스트 체크리스트

### 배포 전 필수 확인
- [ ] 케이스 A: ACTIVE만 존재 (신규 0, 신규 >0)
- [ ] 케이스 B: BROKEN만 존재 (ack 전/ack 후)
- [ ] 케이스 C: ACTIVE + BROKEN 동시 존재
- [ ] 케이스 D: ACTIVE 6개 미만/이상 (접힘 기본 동작)
- [ ] 케이스 E: 신규 발생 당일 1회 자동 펼침
- [ ] 케이스 F: 동일 인스턴스 오전/오후 조회 시 상태 동일

### 회귀 방지 확인
- [ ] 카드에 숫자 노출 없음 (자동 테스트 통과)
- [ ] 섹션 혼입 없음 (개발 모드 console 확인)
- [ ] status 계산 로직 재도입 없음 (CI 체크 통과)
- [ ] 백엔드 로그에 `[V3_HOME_GUARD]` 경고 없음

---

## 문제 발견 시 조치

1. **상태 불변성 위반**:
   - 백엔드 로그 확인 (`[V3_HOME_GUARD]` 경고)
   - `disable_recalculate_returns` 파라미터 확인
   - `calculate_returns` 호출 경로 추적

2. **카드 숫자 노출**:
   - `ActiveStockCardV3`, `BrokenStockCardV3` 컴포넌트 확인
   - 금지 패턴 검색 (`원`, `%`, `KRW`, `USD`)

3. **섹션 혼입**:
   - 개발 모드 console.error 확인
   - `useMemo`의 분류 로직 확인
   - 서버 응답의 `status` 값 확인

4. **status 계산 로직 재도입**:
   - `check-status-calculation.sh` 실행
   - `determineStockStatus` 사용 여부 확인

---

## 참고

- 자동 테스트는 CI에서 실행되어야 함
- 수동 테스트는 배포 전에 반드시 수행
- 문제 발견 시 즉시 회귀 원인 파악 및 수정


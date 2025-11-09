# YYYY-MM-DD 형식 사용 상세 분석

## 📋 분석 일시
2025-10-31

## 🔍 분석 범위
- 백엔드 코드 (backend/)
- 프론트엔드 코드 (frontend/)
- 테스트 코드

---

## 🔴 백엔드 코드에서 YYYY-MM-DD 형식 사용 위치

### 1. `backend/main.py`

#### 1.1 `is_trading_day()` 함수 (라인 299-330)
**용도**: 거래일 확인 함수에서 날짜 파싱
```python
if len(check_date) == 8 and check_date.isdigit():  # YYYYMMDD 형식
    date_str = f"{check_date[:4]}-{check_date[4:6]}-{check_date[6:8]}"
    check_dt = datetime.strptime(date_str, '%Y-%m-%d').date()
elif len(check_date) == 10 and check_date.count('-') == 2:  # YYYY-MM-DD 형식
    check_dt = datetime.strptime(check_date, '%Y-%m-%d').date()
```
**상태**: ✅ 수정 필요 - YYYYMMDD로 통일해야 함
**영향도**: 중간 (거래일 체크만 사용)

#### 1.2 `scan()` 엔드포인트 - 날짜 입력 처리 (라인 347-360)
**용도**: 스캔 엔드포인트에서 날짜 파라미터 처리
```python
elif len(date) == 10 and date.count('-') == 2:  # YYYY-MM-DD 형식 -> YYYYMMDD로 변환
    today_as_of = date.replace('-', '')
```
**상태**: ✅ 이미 수정됨 - YYYYMMDD로 변환
**영향도**: 높음 (스캔 데이터 저장 형식 결정)

#### 1.3 `delete_scan()` 함수 (라인 598-607)
**용도**: 특정 날짜 스캔 결과 삭제
```python
if len(date) == 8:  # YYYYMMDD 형식
    formatted_date = f"{date[:4]}-{date[4:6]}-{date[6:8]}"  # YYYY-MM-DD로 변환
    compact_date = date
else:  # YYYY-MM-DD 형식
    formatted_date = date  # 그대로 사용
    compact_date = date
```
**상태**: ❌ 수정 필요 - 두 형식 모두 지원하지만, YYYYMMDD로 통일해야 함
**영향도**: 중간 (삭제 기능)

#### 1.4 `validate_from_snapshot()` 함수 (라인 739-750)
**용도**: 스냅샷 검증 (주석에 YYYY-MM-DD 형식 언급)
```python
"""스냅샷(as_of=YYYY-MM-DD) 상위 목록 기준으로 현재 수익률 검증"""
# YYYY-MM-DD 형식 우선 시도
for row in cur.execute("SELECT code, score, score_label FROM scan_rank WHERE date=? ...", (as_of, int(top_k))):
```
**상태**: ❌ 수정 필요 - 주석과 코드 모두 YYYYMMDD로 통일해야 함
**영향도**: 낮음 (검증 기능)

#### 1.5 `get_available_scan_dates()` 함수 (라인 1340-1348)
**용도**: 사용 가능한 스캔 날짜 목록 조회
```python
elif len(date_str) == 10 and date_str.count('-') == 2:  # YYYY-MM-DD -> YYYYMMDD
    formatted_date = date_str.replace('-', '')
```
**상태**: ✅ 이미 수정됨 - YYYYMMDD로 변환
**영향도**: 중간 (날짜 목록 조회)

#### 1.6 `get_scan_by_date()` 엔드포인트 (라인 1363-1390)
**용도**: 특정 날짜 스캔 결과 조회
```python
"""특정 날짜의 스캔 결과를 가져옵니다. (YYYY-MM-DD 형식)"""
# 날짜 형식 검증
if len(date) != 10 or date.count('-') != 2:
    return {"ok": False, "error": "날짜 형식이 올바르지 않습니다. YYYY-MM-DD 형식을 사용해주세요."}
# YYYY-MM-DD 형식 그대로 사용
formatted_date = date
compact_date = date
```
**상태**: ❌ 수정 필요 - API 엔드포인트에서 YYYY-MM-DD 형식을 강제함
**영향도**: 높음 (프론트엔드에서 사용 가능)

#### 1.7 `get_latest_scan_from_db()` 함수 (라인 1478-1479)
**용도**: 최신 스캔 데이터 조회
```python
elif len(date_str) == 10 and date_str.count('-') == 2:  # YYYY-MM-DD
    dt = datetime.strptime(date_str, '%Y%m%d')  # ⚠️ 버그: 형식 불일치!
```
**상태**: ❌ 수정 필요 - 버그 있음 (strptime 형식 불일치)
**영향도**: 높음 (버그로 인한 오류 가능)

#### 1.8 메인트넌스 설정 - 날짜 범위 체크 (라인 2567-2568)
**용도**: 메인트넌스 종료 날짜 범위 확인
```python
start_dt = datetime.strptime(start_date, "%Y-%m-%d")
end_dt = datetime.strptime(end_date, "%Y-%m-%d")
```
**상태**: ⚠️ 유지 필요 - 프론트엔드에서 YYYY-MM-DD 형식으로 전송하므로 일시 유지
**영향도**: 낮음 (메인트넌스 설정만)

#### 1.9 메인트넌스 설정 - 자동 비활성화 (라인 2660)
**용도**: 메인트넌스 종료 날짜 확인
```python
end_datetime = datetime.strptime(end_date, "%Y%m%d")
```
**상태**: ✅ YYYYMMDD 형식 사용 (정상)
**영향도**: 낮음

### 2. `backend/scan_service_refactored.py`

#### 2.1 `_parse_date()` 함수 (라인 31-32)
**용도**: 날짜 문자열을 YYYYMMDD 형식으로 변환
```python
elif len(date_str) == 10 and date_str.count('-') == 2:  # YYYY-MM-DD 형식
    return date_str.replace('-', '')  # YYYYMMDD로 변환
```
**상태**: ✅ 이미 수정됨 - YYYYMMDD로 변환
**영향도**: 중간

### 3. `backend/daily_report_regenerator.py` & `daily_returns_updater.py`

#### 3.1 로그 메시지 (라인 30, 46, 52, 98 등)
**용도**: 로그 메시지에 날짜/시간 표시
```python
datetime.now().strftime('%Y-%m-%d %H:%M:%S')
```
**상태**: ✅ 유지 가능 - 로그 출력용이므로 문제 없음
**영향도**: 매우 낮음 (로그만)

### 4. `backend/tests/test_maintenance_api.py`

#### 4.1 테스트 코드 (라인 89, 106, 249, 260)
**용도**: 메인트넌스 API 테스트
```python
past_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
end_datetime = datetime.strptime(end_date, "%Y-%m-%d")
```
**상태**: ⚠️ 테스트 코드 - 메인트넌스 기능 테스트용이므로 일시 유지
**영향도**: 매우 낮음 (테스트 코드)

---

## 🟡 프론트엔드 코드에서 YYYY-MM-DD 형식 사용 위치

### 1. 날짜 입력 필드 (HTML input type="date")

#### 1.1 `frontend/pages/customer-scanner.js` (라인 512)
```javascript
defaultValue={new Date().toISOString().split('T')[0]}
```
**용도**: 날짜 입력 필드 기본값 (HTML input type="date"는 YYYY-MM-DD 형식 필요)
**상태**: ✅ 유지 필요 - HTML 표준 형식
**영향도**: 낮음 (UI 입력만)

#### 1.2 `frontend/pages/portfolio.js` (라인 32, 92)
```javascript
trade_date: new Date().toISOString().split('T')[0]
```
**용도**: 매매 내역 거래일 입력 필드
**상태**: ✅ 유지 필요 - HTML 표준 형식
**영향도**: 중간 (사용자 입력)

#### 1.3 기타 페이지들
- `frontend/pages/positions.js`
- `frontend/pages/scan.js`
- `frontend/components/ResultTable.jsx`
- 등등...

**상태**: ✅ 모두 UI 입력 필드이므로 유지 필요

### 2. 날짜 표시 (로컬라이제이션)

#### 2.1 `frontend/pages/customer-scanner.js` (라인 292-308)
```javascript
// YYYY-MM-DD 형식을 YYYY년 M월 D일 형식으로 변환
if (scanDate.includes('-')) {
  // YYYY-MM-DD 형식
  date = new Date(scanDate);
} else {
  // YYYYMMDD 형식 (기존 호환성)
  const year = scanDate.substring(0, 4);
  const month = parseInt(scanDate.substring(4, 6));
  const day = parseInt(scanDate.substring(6, 8));
  date = new Date(year, month - 1, day);
}
return date.toLocaleDateString('ko-KR', {...});
```
**용도**: 스캔 날짜를 한국어 형식으로 표시
**상태**: ✅ 양쪽 형식 모두 지원하므로 문제 없음
**영향도**: 중간 (화면 표시)

#### 2.2 `frontend/pages/admin.js` (라인 1004)
```javascript
{new Date(user.created_at).toLocaleDateString('ko-KR')}
```
**용도**: 사용자 생성일 표시
**상태**: ✅ 문제 없음
**영향도**: 낮음

### 3. API 호출 시 날짜 전송

**현재 상태**: 프론트엔드에서 백엔드로 날짜를 전송할 때 어떤 형식을 사용하는지 확인 필요
- 메인트넌스 설정: YYYY-MM-DD 형식으로 전송
- 스캔 요청: 확인 필요

---

## 📊 종합 분석

### 🔴 수정 필요 (백엔드)

1. **`backend/main.py`**:
   - `is_trading_day()` - 거래일 체크 (라인 309-311)
   - `delete_scan()` - 삭제 함수 (라인 603-607)
   - `validate_from_snapshot()` - 주석 및 코드 (라인 739-750)
   - `get_scan_by_date()` - API 엔드포인트 (라인 1363-1390)
   - `get_latest_scan_from_db()` - 버그 수정 필요 (라인 1478-1479)

### ✅ 이미 수정됨

1. `backend/main.py`:
   - `scan()` 엔드포인트 - 날짜 변환 (라인 353-354)
   - `get_available_scan_dates()` - 날짜 변환 (라인 1344-1345)

2. `backend/scan_service_refactored.py`:
   - `_parse_date()` - 날짜 변환 (라인 31-32)

### ⚠️ 유지 필요 (의도적인 사용)

1. 프론트엔드:
   - HTML `input type="date"` 필드 (표준 형식이 YYYY-MM-DD)
   - 날짜 로컬라이제이션 표시

2. 백엔드:
   - 로그 메시지 (가독성)
   - 메인트넌스 설정 (프론트엔드와의 호환성)

### 📌 우선순위

**높음 (즉시 수정)**:
1. `get_latest_scan_from_db()` - 버그 수정 (strptime 형식 불일치)
2. `get_scan_by_date()` - API 엔드포인트 형식 통일
3. `delete_scan()` - 삭제 함수 형식 통일

**중간 (단기 수정)**:
4. `is_trading_day()` - 거래일 체크 함수
5. `validate_from_snapshot()` - 주석 및 코드 정리

**낮음 (선택적)**:
6. 테스트 코드 정리

---

## 🔧 수정 방안

### 1. 백엔드 API 엔드포인트 수정
- `get_scan_by_date()`: YYYYMMDD 형식으로 변경 또는 양쪽 형식 모두 지원
- `delete_scan()`: YYYYMMDD 형식으로 통일

### 2. 내부 함수 수정
- `is_trading_day()`: 입력은 양쪽 형식 지원, 내부 처리는 YYYYMMDD
- `validate_from_snapshot()`: 주석 수정 및 코드 정리
- `get_latest_scan_from_db()`: strptime 버그 수정

### 3. 프론트엔드
- HTML 입력 필드는 그대로 유지 (표준)
- API 호출 시 YYYYMMDD 형식으로 변환하여 전송

---

## 📝 참고사항

1. **DB 저장 형식**: 현재 YYYYMMDD로 통일됨
2. **API 응답 형식**: `as_of` 필드는 YYYYMMDD 형식 사용
3. **프론트엔드 입력**: HTML 표준에 따라 YYYY-MM-DD 형식 유지 필요
4. **호환성**: 기존 데이터 및 외부 연동 고려 필요




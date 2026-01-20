# 등락률 표시 로직 일관성 코드리뷰 보고서

## 개요
백엔드와 프론트엔드 간의 `change_rate` 처리 일관성을 검증하고 문제점을 파악합니다.

## 데이터 플로우

### 1. 스캐너 계산 단계
**파일**: `backend/scanner_v2/core/scanner.py`
**함수**: `_calculate_change_rate()`

```python
def _calculate_change_rate(self, df: pd.DataFrame) -> float:
    """등락률 계산 (소수 형태로 반환, 예: 0.0596 = 5.96%)"""
    # ...
    return round((current_close - prev_close) / prev_close, 4)
```

**반환 형태**: 소수 형태 (예: `0.0057` = 0.57%)

### 2. DB 저장 단계
**파일**: `backend/services/scan_service.py`
**함수**: `save_scan_snapshot()`

```python
# change_rate 변환: 스캐너 v2는 소수 형태로 반환
if abs(scan_change_rate) < 1.0 and scan_change_rate != 0.0:
    scan_change_rate = scan_change_rate * 100

# 퍼센트로 저장, 소수점 2자리
"change_rate": round(float(scan_change_rate), 2)
```

**저장 형태**: 퍼센트 형태 (예: `0.57` = 0.57%)

### 3. API 반환 단계
**파일**: `backend/main.py`
**엔드포인트**: `/scan-by-date/{date}`

```python
# change_rate 정규화: scanner_version이 'v2'인 경우 이미 퍼센트 형태로 저장됨
change_rate_raw = data.get("change_rate") or 0.0
change_rate = float(change_rate_raw)
row_scanner_version = data.get("scanner_version")

if row_scanner_version != 'v2' and abs(change_rate) < 1.0 and change_rate != 0.0:
    change_rate = change_rate * 100
```

**반환 형태**: 
- v2: 퍼센트 형태 그대로 반환 (예: `0.57`)
- v1: 소수 형태면 퍼센트로 변환

### 4. 프론트엔드 표시 단계
**파일**: `frontend/v2/pages/customer-scanner.js`

```javascript
{item.change_rate !== 0 ? `${item.change_rate > 0 ? '+' : ''}${item.change_rate}%` : '데이터 없음'}
```

**표시 형태**: 퍼센트 형태 그대로 표시 (예: `0.57%`)

## 일관성 검증 결과

### ✅ 정상 동작
1. **스캐너 → DB 저장**: 소수 형태(0.0057) → 퍼센트 형태(0.57%) 변환 ✅
2. **DB 저장 → API 반환 (v2)**: 퍼센트 형태(0.57%) → 퍼센트 형태(0.57%) 그대로 ✅
3. **API 반환 → 프론트엔드 표시**: 퍼센트 형태(0.57%) → 퍼센트 형태(0.57%) 그대로 ✅

### ⚠️ 잠재적 문제점

#### 1. 프론트엔드 변환 로직 부재
**문제**: 프론트엔드에서 `change_rate`가 소수 형태로 올 경우를 처리하지 않음

**현재 코드**:
```javascript
{item.change_rate}%  // 그대로 표시
```

**개선 제안**:
```javascript
{(() => {
  const rate = item.change_rate;
  if (rate === null || rate === undefined) return '데이터 없음';
  if (rate === 0) return '0%';
  
  // 소수 형태면 퍼센트로 변환 (안전장치)
  const displayRate = Math.abs(rate) < 1.0 && rate !== 0.0 ? rate * 100 : rate;
  return `${rate > 0 ? '+' : ''}${displayRate.toFixed(2)}%`;
})()}
```

#### 2. v1/v2 혼용 시 혼란 가능성
**문제**: v1 스캐너의 경우 소수 형태로 저장될 수 있어 API에서 변환 필요

**현재 처리**: ✅ API에서 `scanner_version` 확인하여 변환

#### 3. 경계값 처리
**문제**: `change_rate`가 정확히 1.0 또는 -1.0인 경우

**현재 로직**:
```python
if abs(change_rate) < 1.0 and change_rate != 0.0:
    change_rate = change_rate * 100
```

**분석**: 
- `1.0`은 변환하지 않음 (이미 퍼센트 형태로 간주) ✅
- `-1.0`도 변환하지 않음 ✅
- `0.0`은 변환하지 않음 ✅

## 테스트 결과

### 백엔드 단위 테스트
```bash
python -m pytest backend/tests/test_change_rate_consistency.py -v
```

**예상 결과**:
- ✅ 스캐너 계산값: 소수 형태
- ✅ 저장 변환값: 퍼센트 형태
- ✅ API 반환값 (v2): 퍼센트 형태 (변환 없음)
- ✅ API 반환값 (v1): 퍼센트 형태 (변환됨)
- ✅ 프론트엔드 표시값: 퍼센트 형태

### 프론트엔드 단위 테스트
```bash
npm test -- change-rate-display.test.js
```

**예상 결과**:
- ✅ 퍼센트 형태로 표시
- ✅ 양수/음수 처리
- ✅ 0 처리
- ✅ 경계값 처리

### API 통합 테스트
```bash
python -m pytest backend/tests/test_change_rate_api_integration.py -v
```

**예상 결과**:
- ✅ v2 스캔 결과가 퍼센트 형태로 반환
- ✅ 모든 v2 스캔 결과의 change_rate가 100 미만

## 권장 사항

### 1. 프론트엔드 안전장치 추가
프론트엔드에서 소수 형태가 올 경우를 대비한 변환 로직 추가 (방어적 프로그래밍)

### 2. 타입 명시
API 응답에 `change_rate`의 단위를 명시하는 필드 추가 고려:
```json
{
  "change_rate": 0.57,
  "change_rate_unit": "percent"
}
```

### 3. 문서화
각 단계에서의 `change_rate` 형태를 명확히 문서화

## 결론

현재 구현은 **일관성 있게 동작**하고 있습니다:
- 스캐너 v2: 소수 형태 → DB 저장 시 퍼센트 변환 → API 퍼센트 반환 → 프론트엔드 퍼센트 표시 ✅

다만, **프론트엔드에 안전장치를 추가**하여 예외 상황을 처리하는 것을 권장합니다.


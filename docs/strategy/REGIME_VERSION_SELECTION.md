# 레짐 분석 버전 선택 가이드

**최종 업데이트**: 2025-11-24

## 개요

레짐 분석 버전은 시장 상황을 분석하는 방법을 결정합니다. Scanner 버전과는 독립적으로 관리되며, DB에서 선택할 수 있습니다.

## 지원 버전

### V1 (기본 장세 분석)

- **설명**: KOSPI 수익률 기반 시장 상황 판단
- **특징**:
  - KOSPI 종가/저가 수익률 분석
  - 며칠간의 추세 반영 (가중 평균)
  - 유니버스 평균 수익률 고려
  - 변동성 분석
- **장점**: 빠른 분석, 단순한 로직
- **단점**: 글로벌 시장 고려 없음

### V3 (Global Regime v3)

- **설명**: 한국/미국 시장 분석
- **특징**:
  - 한국 시장 추세 분석
  - 미국 시장 추세 분석 (SPY, QQQ)
  - 글로벌 추세 결합
- **장점**: 글로벌 시장 고려
- **단점**: 리스크 분석 미포함

### V4 (Global Regime v4) - 권장

- **설명**: 한국/미국 시장 + 리스크 분석
- **특징**:
  - 한국 시장 추세/리스크 분석
  - 미국 시장 추세/리스크 분석 (SPY, QQQ, VIX)
  - 글로벌 추세/리스크 결합
  - 최종 레짐 결정 (bull/neutral/bear/crash)
- **장점**: 가장 정확한 시장 상황 분석
- **단점**: 데이터 요구사항 높음

## 버전 선택 방법

### 1. 관리자 UI 사용 (권장)

1. 관리자 페이지 접속: `/admin`
2. "스캐너 설정" 섹션으로 이동
3. "레짐 분석 버전" 드롭다운에서 선택:
   - V1 (기본 장세 분석)
   - V3 (Global Regime v3)
   - V4 (Global Regime v4)
4. "설정 저장" 클릭

다음 스캔부터 선택한 레짐 버전이 적용됩니다.

### 2. API 사용

**설정 조회:**
```bash
GET /admin/scanner-settings
Authorization: Bearer <admin_token>
```

**응답 예시:**
```json
{
  "ok": true,
  "settings": {
    "scanner_version": "v1",
    "scanner_v2_enabled": "false",
    "regime_version": "v4"
  }
}
```

**설정 업데이트:**
```bash
POST /admin/scanner-settings
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "regime_version": "v4"
}
```

### 3. 환경 변수 설정 (Fallback)

DB 설정이 없거나 DB 연결 실패 시 `.env` 파일의 설정을 사용합니다:

```env
REGIME_VERSION=v4
```

### 4. 직접 SQL 실행

```sql
-- 설정 조회
SELECT * FROM scanner_settings WHERE setting_key = 'regime_version';

-- 설정 업데이트
UPDATE scanner_settings 
SET setting_value = 'v4', updated_at = NOW() 
WHERE setting_key = 'regime_version';
```

## 설정 우선순위

1. **DB 우선**: `scanner_settings` 테이블에서 조회
2. **.env Fallback**: DB에 없으면 환경 변수에서 읽기
3. **기본값**: 둘 다 없으면 `v1` 사용

## 버전별 사용 시나리오

### V1 사용 권장

- 빠른 분석이 필요한 경우
- 글로벌 시장 데이터가 없는 경우
- 단순한 장세 판단만 필요한 경우

### V3 사용 권장

- 글로벌 시장을 고려해야 하는 경우
- 리스크 분석이 불필요한 경우
- V4 데이터 요구사항을 충족하지 못하는 경우

### V4 사용 권장 (기본 권장)

- 가장 정확한 시장 상황 분석이 필요한 경우
- 리스크 관리가 중요한 경우
- 한국/미국 시장 데이터가 모두 있는 경우

## Scanner 버전과의 조합

레짐 분석 버전은 Scanner 버전과 독립적으로 선택할 수 있습니다:

| Scanner 버전 | 레짐 분석 버전 | 설명 |
|------------|--------------|------|
| V1 | V1 | 기본 조합 |
| V1 | V4 | 기본 스캐너 + 고급 레짐 분석 |
| V2 | V1 | 고급 스캐너 + 기본 레짐 분석 |
| V2 | V4 | 최고 조합 (권장) |

## 버전 변경 시 주의사항

1. **적용 시점**: 다음 스캔부터 적용됩니다
2. **기존 데이터**: 기존 스캔 결과는 변경되지 않습니다
3. **캐시**: 레짐 분석 캐시는 자동으로 클리어됩니다
4. **데이터 요구사항**: V3/V4는 미국 시장 데이터가 필요합니다

## 문제 해결

### V4가 작동하지 않는 경우

1. **데이터 확인**: 미국 시장 데이터 (SPY, QQQ, VIX) 확인
2. **로그 확인**: 에러 로그에서 자세한 오류 확인
3. **Fallback**: 자동으로 V3 또는 V1으로 fallback됩니다

### 버전이 적용되지 않는 경우

1. **DB 확인**: `scanner_settings` 테이블에서 `regime_version` 값 확인
2. **캐시 확인**: 레짐 분석 캐시 클리어
3. **서비스 재시작**: 필요시 백엔드 서비스 재시작

## 관련 문서

- [레짐 분석 가이드](./REGIME_ANALYSIS.md)
- [Scanner V2 사용 가이드](../scanner-v2/SCANNER_V2_USAGE.md)
- [스캐너 설정 테이블](../database/SCANNER_SETTINGS_TABLE.md)
- [프로젝트 개요](../PROJECT_OVERVIEW.md)


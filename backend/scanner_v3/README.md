# Scanner V3 - 중기+단기 조합 엔진

## 개요

Scanner V3는 기존 v1, v2와 완전히 독립된 신규 검색기로, **중기(midterm) + 단기(v2-lite) 조합 엔진**입니다.

## 엔진 버전 정의

- **v1**: 기존 레거시 검색기 (변경 없음)
- **v2**: 기존 단기 검색기 (변경 없음)
- **v3**: 신규 검색기 (v2-lite + midterm 조합)

## 핵심 운영 원칙

1. **midterm은 항상 실행**
2. **v2-lite는 neutral/normal 레짐에서만 실행**
3. **v2-lite는 neutral/normal이 아니면 호출 자체를 하지 않음**
4. **두 엔진의 결과는 절대 병합하지 않음**
5. **두 엔진은 서로의 fallback, ranking, score, filter에 영향을 주지 않음**

## 레짐 판정 규칙

- 기존 `final_regime`, `risk_label` 판정 로직을 그대로 사용
- **neutral/normal 조건**:
  - `final_regime == "neutral"`
  - AND `risk_label == "normal"`

## 실행 흐름

### Step 1. 레짐 판정
- `final_regime`, `risk_label` 계산 (기존 로직 재사용)

### Step 2. 엔진 실행
- **midterm**: 항상 실행
- **v2-lite**: neutral/normal일 때만 실행

### Step 3. 결과 분리 반환
- midterm 결과는 항상 반환
- v2-lite 결과는 neutral/normal일 때만 반환
- 결과를 합치거나 정렬하거나 보정하지 않음

## API 응답 구조

```json
{
  "engine_version": "v3",
  "date": "YYYYMMDD",
  "regime": {
    "final": "neutral",
    "risk": "normal"
  },
  "results": {
    "midterm": {
      "enabled": true,
      "candidates": [...]
    },
    "v2_lite": {
      "enabled": true,
      "candidates": [...]
    }
  }
}
```

## 노출 규칙

### neutral/normal 레짐
- midterm 결과 노출
- v2-lite 결과 노출

### 그 외 레짐
- midterm 결과만 노출
- `v2_lite.enabled = false`
- `v2_lite.candidates = []`

## 관리자 화면

관리자 화면에서 **활성 엔진**을 선택할 수 있습니다:
- V1 (기존 레거시 검색기)
- V2 (기존 단기 검색기)
- V3 (신규: 중기+단기 조합)

선택된 엔진만 스케줄러에 의해 실행됩니다.

## 중요 제약

- v3는 기존 v2 코드 경로를 재사용하지 않음
- v2-lite는 v3 내부 전용 인스턴스로 사용
- v3 실행이 기존 v1, v2 결과에 영향을 주지 않음
- 기존 v1/v2 스케줄, 로그, 결과는 변경되지 않음

## 파일 구조

```
backend/scanner_v3/
├── __init__.py
└── core/
    ├── __init__.py
    └── engine.py  # ScannerV3 클래스
```

## 사용 방법

V3는 `active_engine` 설정을 통해 활성화됩니다:

1. 관리자 화면에서 "활성 엔진"을 "V3"로 선택
2. 스케줄러가 자동으로 V3 엔진 실행
3. `/scan` API가 V3 결과 반환

## 검증 체크리스트

- [ ] 관리자 화면에서 v3 선택 시에만 v3가 실행되는가
- [ ] v3 실행 시 v1/v2 로그가 생성되지 않는가
- [ ] neutral/normal이 아닌 날에 v2-lite 로그가 없는가
- [ ] midterm coverage가 기존 단독 실행과 동일한가
- [ ] v2-lite 결과가 midterm 결과에 영향을 주지 않는가






















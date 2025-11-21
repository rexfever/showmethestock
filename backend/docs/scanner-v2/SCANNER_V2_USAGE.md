# 스캐너 V2 사용 가이드

## 개요

스캐너 V2는 최근 개선된 스캔 로직을 독립적으로 관리할 수 있도록 분리한 버전입니다.

### 주요 개선 사항

1. **신호 우선 원칙**: 신호 충족만 후보군 포함, 점수는 순위용
2. **멀티데이 트렌드 분석**: 하루가 아닌 며칠간의 추세 반영
3. **점수 구성 기반 전략 분류**: 점수 합계가 아닌 구성에 따라 전략 결정
4. **RSI 동적 조정**: 시장 상황에 따라 RSI 임계값 동적 조정

## 설정 방법

### 1. 환경 변수 설정

`.env` 파일에 다음 설정 추가:

```bash
# 스캐너 버전 선택
SCANNER_VERSION=v2
SCANNER_V2_ENABLED=true
```

### 2. 스캐너 V2 설정 (선택사항)

**중요**: 스캐너 V2는 **V1 설정을 기본으로 공유**합니다. V2 전용 설정(`SCANNER_V2_` 접두사)이 없으면 V1 설정을 자동으로 사용합니다.

#### 기본 사용 (V1 설정 공유)

```bash
# V1 설정 그대로 사용 (추가 설정 불필요)
MIN_SIGNALS=3
GAP_MAX=0.015
VOL_MA5_MULT=2.5
```

#### V2 전용 설정 추가 (필요한 경우만)

```bash
# V1 설정
MIN_SIGNALS=3

# V2 전용 설정 (V1과 다르게 설정하려는 경우만)
SCANNER_V2_MIN_SIGNALS=4  # V2만 4개 필요
# GAP_MAX는 V1 설정 그대로 사용
```

**설정 우선순위:**
1. `SCANNER_V2_*` (V2 전용) - 최우선
2. `*` (V1 설정) - Fallback
3. 기본값 - 최종 Fallback

자세한 내용은 `docs/scanner-v2/CONFIG_SHARING.md`를 참고하세요.

## 사용 방법

### 코드에서 사용

```python
from scanner_factory import get_scanner
from market_analyzer import market_analyzer

# 스캐너 가져오기 (config에서 버전 자동 선택)
scanner = get_scanner()

# 또는 명시적으로 버전 지정
scanner = get_scanner(version='v2')

# 스캔 실행
results = scanner.scan(universe, date, market_condition)
```

### API에서 사용

`/scan` 엔드포인트는 `config.scanner_version` 설정에 따라 자동으로 적절한 스캐너를 사용합니다.

## 스캐너 버전 전환

### V1 → V2 전환

1. `.env` 파일 수정:
   ```bash
   SCANNER_VERSION=v2
   SCANNER_V2_ENABLED=true
   ```

2. 스캐너 V2 전용 설정 추가 (선택사항)

3. 서버 재시작

### V2 → V1 전환

1. `.env` 파일 수정:
   ```bash
   SCANNER_VERSION=v1
   # 또는
   SCANNER_V2_ENABLED=false
   ```

2. 서버 재시작

## 설정 분리

### V1 설정 (기존)

기존 `config.py`의 설정을 그대로 사용합니다.

### V2 설정 (새로운)

`scanner_v2/config_v2.py`의 `ScannerV2Config` 클래스를 사용하며, 환경 변수는 `SCANNER_V2_` 접두사로 시작합니다.

이렇게 분리함으로써:
- V1과 V2의 설정이 독립적으로 관리됨
- 환경 변수 충돌 방지
- 각 버전별로 최적화된 설정 가능

## 모니터링

스캐너 버전은 로그에서 확인할 수 있습니다:

```
📊 스캐너 버전: v2
🔍 스캔 실행 중...
```

## 문제 해결

### V2가 활성화되지 않는 경우

1. `SCANNER_V2_ENABLED=true` 확인
2. `SCANNER_VERSION=v2` 확인
3. 서버 재시작 확인

### 설정이 적용되지 않는 경우

1. 환경 변수 이름이 `SCANNER_V2_` 접두사로 시작하는지 확인
2. `.env` 파일이 올바른 위치에 있는지 확인
3. 서버 재시작 확인

## 참고

- 스캐너 V2 설계 문서: `backend/docs/scanner-v2/SCANNER_V2_DESIGN.md`
- 스캔 로직 개선 사항: `backend/docs/SCAN_LOGIC_IMPROVEMENTS_SUMMARY.md`


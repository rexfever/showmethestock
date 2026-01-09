# Scanner V3 구현 요약

## 구현 완료 사항

### 1. DB 설정 관리
- ✅ `scanner_settings` 테이블에 `active_engine` 추가
- ✅ `get_active_engine()`, `set_active_engine()` 함수 구현
- ✅ 기본값: `v1`

### 2. V3 엔진 코어
- ✅ `backend/scanner_v3/core/engine.py` 구현
- ✅ 레짐 판정 로직 (기존 `_extract_final_regime`, `_extract_risk_label` 재사용)
- ✅ Midterm 엔진 실행 (항상)
- ✅ V2-Lite 엔진 실행 (neutral/normal일 때만)
- ✅ 결과 분리 반환 (병합하지 않음)

### 3. API 엔드포인트
- ✅ `/scan` 엔드포인트에서 `active_engine` 확인
- ✅ V3 선택 시 `ScannerV3.scan()` 호출
- ✅ V3 결과를 기존 `ScanItem` 형식으로 변환 (하위 호환성)
- ✅ V1/V2는 기존 로직 유지

### 4. 스케줄러
- ✅ `scheduler.py`의 `run_scan()`에서 `active_engine` 확인
- ✅ 선택된 엔진만 실행

### 5. 관리자 화면
- ✅ 활성 엔진 선택 UI 추가 (최우선 표시)
- ✅ V3 선택 시 안내 메시지 표시
- ✅ V3 선택 시 스캐너 버전 선택 숨김
- ✅ 현재 설정 정보에 활성 엔진 표시

### 6. 결과 저장
- ✅ `save_scan_snapshot()`에서 `v3` 버전 지원
- ✅ `scan_rank` 테이블에 `scanner_version='v3'`으로 저장

## 파일 구조

```
backend/
├── scanner_v3/
│   ├── __init__.py
│   ├── README.md
│   ├── IMPLEMENTATION_SUMMARY.md
│   └── core/
│       ├── __init__.py
│       └── engine.py  # ScannerV3 클래스
├── scanner_settings_manager.py  # active_engine 관리 함수 추가
├── main.py  # /scan 엔드포인트 수정
├── scheduler.py  # run_scan() 수정
└── services/scan_service.py  # v3 버전 지원

frontend/
└── pages/
    └── admin.js  # active_engine 선택 UI 추가
```

## 주요 변경 사항

### backend/scanner_settings_manager.py
- `create_scanner_settings_table()`: `active_engine` 기본값 추가
- `get_active_engine()`: 활성 엔진 조회 함수
- `set_active_engine()`: 활성 엔진 설정 함수

### backend/scanner_v3/core/engine.py
- `ScannerV3` 클래스: V3 엔진 메인 클래스
- `_determine_regime()`: 레짐 판정 (기존 로직 재사용)
- `_run_midterm()`: Midterm 엔진 실행
- `_run_v2_lite()`: V2-Lite 엔진 실행

### backend/main.py
- `/scan` 엔드포인트: `active_engine` 확인 후 V3 실행
- V3 결과를 `ScanItem` 형식으로 변환 (하위 호환성)
- trend/flags 누락 시 기본값 처리

### backend/scheduler.py
- `run_scan()`: `active_engine` 확인 및 로그 출력

### frontend/pages/admin.js
- 활성 엔진 선택 UI (최우선)
- V3 선택 시 안내 메시지
- 현재 설정 정보에 활성 엔진 표시

## 검증 방법

### 1. 관리자 화면에서 v3 선택
```bash
# 관리자 화면 접속
# "활성 엔진"을 "V3"로 선택
# 저장 버튼 클릭
```

### 2. 스케줄러 실행 확인
```bash
# 스케줄러 로그 확인
# "활성 엔진: v3" 메시지 확인
# V3 스캔 완료 메시지 확인
```

### 3. 레짐별 v2-lite 실행 확인
- neutral/normal 레짐: v2-lite 결과 포함
- 그 외 레짐: v2-lite 결과 없음 (`enabled=false`)

### 4. 결과 분리 확인
- midterm 결과와 v2-lite 결과가 별도로 반환되는지 확인
- 두 결과가 병합되지 않는지 확인

## 주의사항

1. **격리**: V3는 기존 v1/v2 코드 경로를 재사용하지 않음
2. **독립성**: V3 실행이 기존 v1/v2 결과에 영향을 주지 않음
3. **레짐 판정**: neutral/normal 조건이 정확히 작동하는지 확인 필요
4. **결과 변환**: V3 결과를 ScanItem으로 변환할 때 trend/flags 누락 처리

## 다음 단계

1. 실제 환경에서 테스트
2. 레짐별 v2-lite 실행 확인
3. 결과 분리 검증
4. 성능 모니터링






















# 서버 운영에 불필요한 파일들

이 폴더에는 서버 운영에 직접적으로 필요하지 않은 파일들이 보관되어 있습니다.

## 폴더 구조

- `tests/`: 테스트 파일들 (test_*.py)
- `analysis/`: 분석 및 검증 스크립트들
  - analyze_*.py
  - calculate_*.py
  - check_*.py
  - scan_october_*.py
  - evaluate_*.py
- `validation/`: 검증 스크립트들 (validate_*.py)
- `temp/`: 임시 파일들 (temp_*.py)
- `scripts/`: 일회성 스크립트들
  - update_*.py
  - regenerate_*.py
  - daily_*.py
  - *.sh
  - *.service
  - *.html
- `docs/`: 문서 파일들 (*.md)
- `data/`: 데이터 파일들 (*.json)

## 참고사항

- 이 파일들은 개발, 테스트, 분석 목적으로 사용되었습니다
- 서버 운영에는 `main.py`에서 import하는 핵심 모듈들만 필요합니다
- 필요시 이 파일들을 참조하여 기능을 확인할 수 있습니다

## 이동 일시

2025-11-24


# 서버 파일 정리 요약

## 정리 일시
2025-11-24

## 이동된 파일 통계
- **총 112개 파일** 이동
- 테스트 파일: 약 40개
- 분석 스크립트: 약 15개
- 검증 스크립트: 4개
- 임시 파일: 3개
- 일회성 스크립트: 약 10개
- 문서 파일: 약 40개
- 데이터 파일: 5개

## 정리 후 상태
- **핵심 Python 파일**: 51개 (서버 운영에 필요한 파일들)
- **archive 폴더**: 112개 파일 보관

## 서버 운영에 필요한 핵심 파일들
- `main.py`: FastAPI 메인 애플리케이션
- `config.py`: 설정 관리
- `scanner.py`, `scanner_v2/`: 스캐너 엔진
- `services/`: 핵심 서비스 모듈들
- `models.py`, `auth_*.py`: 데이터 모델 및 인증
- `kiwoom_api.py`, `db_manager.py`: 외부 API 및 DB 관리
- `scheduler.py`: 스케줄러
- `market_analyzer.py`, `market_guide.py`: 시장 분석
- 기타 서비스 모듈들

## 참고사항
- 이동된 파일들은 `backend/archive/non-essential-files/` 폴더에 보관되어 있습니다
- 필요시 해당 파일들을 참조하여 기능을 확인할 수 있습니다
- 서버 운영에는 `main.py`에서 import하는 핵심 모듈들만 필요합니다


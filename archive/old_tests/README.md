# 구버전 테스트 파일 아카이브

이 디렉토리에는 프로젝트 루트에 있던 구버전 테스트 파일들이 보관되어 있습니다.

## 📋 파일 목록

### 통합 테스트
- `test_auth_integration.py` - 인증 통합 테스트
- `test_portfolio_integration.py` - 포트폴리오 통합 테스트
- `test_server_reflection.py` - 서버 반영 테스트

### 단위 테스트
- `test_endpoints.py` - API 엔드포인트 테스트
- `test_imports.py` - 모듈 import 테스트
- `test_syntax.py` - 문법 체크
- `test_syntax_check.py` - 문법 체크 (중복)
- `test_duplicate_removal.py` - 중복 제거 테스트
- `test_portfolio_profit.py` - 포트폴리오 수익 테스트

### tests/ 폴더
- `test_filtering.py` - 필터링 테스트
- `__pycache__/` - Python 캐시

## ⚠️ 중요 사항

### 현재 상태
- 이 테스트 파일들은 프로젝트 초기에 작성된 것입니다
- **현재 사용 중인 테스트**: `backend/tests/` 폴더
- 이 파일들은 더 이상 사용되지 않습니다

### 보관 이유
1. **히스토리 보존**: 초기 테스트 방법론 참조
2. **코드 참고**: 필요시 테스트 로직 참조
3. **롤백 대비**: 만약의 경우 참조 가능

### 삭제 가능 시점
- 현재 테스트 시스템 안정화 후
- 디스크 공간 부족 시 우선 삭제 대상

## 🔗 현재 테스트 위치

- **백엔드 테스트**: `backend/tests/`
  - `test_market_validation_system.py`
  - `test_validation_api.py`
  - `test_scheduler_integration.py`
  - `TEST_REPORT.md`

- **프론트엔드 테스트**: `frontend/__tests__/`

## 📊 파일 크기

```
총 크기: ~30KB
파일 수: 9개 + tests/ 폴더
```

---

**마지막 업데이트**: 2025년 11월 9일


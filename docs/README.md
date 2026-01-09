# 스톡인사이트 (Stock Insight) 문서

## 문서 구조

```
docs/
├── README.md                          # 이 파일 (문서 인덱스)
├── DOCUMENTATION_STRUCTURE.md         # 문서 구조 가이드
│
├── v3/                                # V3 추천 시스템 문서
│   ├── README.md                      # V3 문서 인덱스
│   ├── implementation/                # 구현 관련 문서
│   ├── migration/                     # 마이그레이션 관련 문서
│   ├── verification/                  # 검증 관련 문서
│   └── ux/                            # UX 구현 관련 문서
│
├── backend/                           # 백엔드 관련 문서
│   ├── scanner/                       # 스캐너 관련 문서
│   ├── backtest/                      # 백테스트 관련 문서
│   └── analysis/                      # 분석 관련 문서
│
├── frontend/                          # 프론트엔드 관련 문서
│   └── v3/                            # V3 프론트엔드 문서
│
├── database/                          # 데이터베이스 관련 문서
├── deployment/                        # 배포 관련 문서
├── scanner-v2/                        # Scanner V2 문서
├── strategy/                          # 전략 관련 문서
├── analysis/                          # 분석 리포트
├── code-review/                       # 코드 리뷰 문서
├── migrations/                        # 마이그레이션 가이드
│   └── README.md                     # 마이그레이션 문서 인덱스
└── work-logs/                         # 작업 로그
```

## 주요 문서

### V3 추천 시스템
- [V3 문서 인덱스](./v3/README.md)
- [ARCHIVED 스냅샷 구현 리포트](./v3/implementation/V3_ARCHIVED_SNAPSHOT_IMPLEMENTATION_REPORT.md)
- [V3 구현 리포트](./v3/implementation/V3_IMPLEMENTATION_REPORT.md)

### 프로젝트 개요
- [프로젝트 개요](./PROJECT_OVERVIEW.md)
- [API 엔드포인트](./API_ENDPOINTS.md)
- [문제 해결 가이드](./TROUBLESHOOTING_GUIDE.md)

### 배포 및 운영
- [로컬 개발 환경 구성](./deployment/LOCAL_DEVELOPMENT_SETUP.md)
- [서버 운영 메뉴얼](./deployment/SERVER_OPERATION_MANUAL.md)

### Scanner V2
- [Scanner V2 가이드](./scanner-v2/SCANNER_V2_USAGE.md)
- [Scanner V2 설계](./scanner-v2/SCANNER_V2_DESIGN.md)

### 백엔드 스크립트
- [스캔 스크립트 작성 가이드](./backend/scanner/SCAN_SCRIPT_GUIDE.md) - 서버 API를 사용한 스캔 스크립트 작성 방법

## 문서 작성 규칙

1. **위치**: 모든 문서는 `/docs` 디렉토리 아래에 분류하여 저장
2. **네이밍**: 명확하고 일관된 네이밍 규칙 사용
3. **구조**: 각 하위 디렉토리에는 `README.md`로 인덱스 제공
4. **링크**: 문서 간 상호 참조는 상대 경로 사용

## 문서 분류 기준

- **V3 관련**: `docs/v3/`
- **백엔드**: `docs/backend/`
- **프론트엔드**: `docs/frontend/`
- **데이터베이스**: `docs/database/`
- **배포**: `docs/deployment/`
- **분석**: `docs/analysis/`

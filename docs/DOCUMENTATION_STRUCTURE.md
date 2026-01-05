# 문서 구조 가이드

## 문서 디렉토리 구조

```
docs/
├── README.md                          # 문서 인덱스
├── DOCUMENTATION_STRUCTURE.md         # 이 파일 (문서 구조 가이드)
│
├── v3/                                # V3 추천 시스템 문서
│   ├── implementation/               # 구현 관련 문서
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
└── work-logs/                         # 작업 로그
```

## 문서 분류 규칙

### V3 관련 문서
- **구현 문서**: `docs/v3/implementation/`
- **마이그레이션 문서**: `docs/v3/migration/`
- **검증 문서**: `docs/v3/verification/`
- **UX 문서**: `docs/v3/ux/`

### 백엔드 문서
- **스캐너 문서**: `docs/backend/scanner/`
- **백테스트 문서**: `docs/backend/backtest/`
- **분석 문서**: `docs/backend/analysis/`

### 프론트엔드 문서
- **V3 프론트엔드**: `docs/frontend/v3/`

### 마이그레이션 문서
- **마이그레이션 가이드**: `docs/migrations/`

## 문서 네이밍 규칙

- **구현 리포트**: `*_IMPLEMENTATION_REPORT.md`
- **실행 결과**: `*_EXECUTION_RESULTS.md`
- **검증 리포트**: `*_VERIFICATION_REPORT.md`
- **마이그레이션 가이드**: `*_MIGRATION_GUIDE.md`
- **UX 문서**: `*_UX_*.md`



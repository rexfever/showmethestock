# Global Regime Model v3 스크립트 모음

## 📁 디렉토리 구조

```
scripts/regime_v3/
├── README.md                    # 이 파일
├── setup/                       # 설치 및 설정
│   ├── install_dependencies.py
│   └── run_migration.py
├── analysis/                    # 분석 도구
│   ├── daily_regime_check.py
│   ├── regime_backtest.py
│   └── regime_comparison.py
├── maintenance/                 # 유지보수
│   ├── cleanup_old_data.py
│   └── validate_data.py
└── examples/                    # 사용 예제
    ├── basic_usage.py
    └── advanced_analysis.py
```

## 🚀 빠른 시작

1. **의존성 설치**: `python scripts/regime_v3/setup/install_dependencies.py`
2. **DB 마이그레이션**: `python scripts/regime_v3/setup/run_migration.py`
3. **일일 장세 확인**: `python scripts/regime_v3/analysis/daily_regime_check.py`
4. **백테스트 실행**: `python scripts/regime_v3/analysis/regime_backtest.py --start 20241101 --end 20241205`

## 📊 주요 기능

- **실시간 장세 분석**: 한국+미국 시장 데이터 결합
- **백테스트**: 레짐별 성과 분석
- **데이터 검증**: DB 무결성 체크
- **비교 분석**: v1 vs v3 장세 비교
# Market Analyzer Enhancement Plan (2025-11-09)

## 목표
- 15:35 장세 분석 배치 → 스캔 실행 흐름 확립
- 안정적인 데일리 장세 요약 제공 (bull / neutral / bear / crash 등)
- 향후 지표 확장 및 자동 튜닝을 위한 구조화

## 전체 파이프라인

```
15:35 ±1분 : 장세 분석 배치
    └─ KOSPI/코스닥 데이터 수집
    └─ Breadth / 수급 / 섹터 지표 계산
    └─ 스코어링 → market_conditions 저장

장세 분석 완료 확인 → 스캐너 실행
    └─ 최신 market_conditions 로드
    └─ 파라미터 조정 + 스캔 수행
    └─ 결과 DB 저장 + 알림/프런트 반영
```

## 데이터 지표 설계

| 카테고리 | 지표 | 소스 | 비고 |
| --- | --- | --- | --- |
| 추세 | KOSPI/KOSDAQ 종가/저가 수익률, 5/20일 경사, ATR | Kiwoom `get_ohlcv` | 종가 확정 후 계산 |
| Breadth | 상승/하락 종목 비율, 거래대금 상위 동향 | Kiwoom 상위 종목 조회 | 최대 100종 샘플링 |
| 수급 | 외국인/기관 순매수 추세 | 추후 데이터 소스 확정 | 우선은 placeholder |
| 섹터/스타일 | 섹터별 상승률, 성장/가치 스타일 | 추후 확장 | 1차 버전은 기본값 |
| 변동성 | ATR, BB Width, KOSPI intraday range | KOSPI 069500 | 급락 감지 |

## 스코어링 로직 개요

- 지표별 표준화 (Z-score 또는 min-max → -2 ~ +2)
- 가중치 합산 → 총점 계산
- 총점/주요 지표 임계값으로 레이블 결정
    - `>= +1.0`: bull
    - `-0.5 ~ +1.0`: neutral
    - `-1.5 ~ -0.5`: bear
    - `< -1.5`: crash
- 결과 구조: `market_sentiment`, `score_detail` (JSON), `rsi_threshold`, `min_signals` 등

## DB 저장 및 인터페이스

- `market_conditions` 테이블 확장안 (초안)

| 컬럼 | 타입 | 설명 |
| --- | --- | --- |
| `date` | DATE (PK) | 분석 기준일 (장 마감 기준) |
| `market_sentiment` | TEXT | bull / neutral / bear / crash |
| `sentiment_score` | NUMERIC(5,2) | 종합 점수 (-5.00 ~ +5.00) |
| `trend_metrics` | JSONB | KOSPI/KOSDAQ 추세, EMA 기울기, ATR 등 |
| `breadth_metrics` | JSONB | 상승/하락 비율, 거래대금 상위 추세 등 |
| `flow_metrics` | JSONB | 외국인/기관 순매수, 프로그램 매매 등 |
| `sector_metrics` | JSONB | 섹터/스타일 퍼포먼스 요약 |
| `volatility_metrics` | JSONB | ATR, intraday range, 변동성 지표 |
| `foreign_flow_label` | TEXT | buy / sell / neutral (요약) |
| `volume_trend_label` | TEXT | high / normal / low |
| `adjusted_params` | JSONB | 스캐너용 파라미터 (rsi, min_signals 등) |
| `analysis_notes` | TEXT | 추가 설명/로그 |
| `created_at` | TIMESTAMPTZ | 분석 저장 시각 |
| `updated_at` | TIMESTAMPTZ | 재계산 시각 |

- 마이그레이션 전략
    1. 기존 테이블 백업 (필요 시 dump)
    2. 신규 컬럼 추가 (기본값 NULL) → 기존 데이터 유지
    3. 기본 레코드 업데이트: `sentiment_score`, `adjusted_params` 기본값 채우기
    4. 인덱스 검토 (`date DESC`, `market_sentiment`)

- 스캐너는 `SELECT * FROM market_conditions ORDER BY date DESC LIMIT 1`
- 실패 시 기본 프리셋 fallback (neutral)

## 배치 스케줄링

- `scheduler.py` 업데이트
    - 15:35 → `run_market_analysis()` 실행
    - 성공 시 → `run_scan()` 호출
    - 실패 시 → 알림 후 기본값으로 스캔 (옵션)
- cron/systemd timer 등 외부 스케줄러와 연동 가능

## 모니터링/운영

- 장세 분석 성공/실패 로그 남기기
- Slack/Webhook 알림 (선택)
- 관리자 페이지에서 최신 장세 정보 및 지표 확인 기능 제공

## 향후 확장 아이디어

- 장중 간이 분석 (30분 간격) → 실시간 경고/알림에 활용
- 더 정밀한 수급/섹터 데이터 연결 (KRX Data, OpenAPI 등)
- 머신러닝 기반 장세 클러스터링/예측 모델 시험
- 스캔 결과와 장세 지표 상관관계 분석 → 파라미터 자동 튜닝

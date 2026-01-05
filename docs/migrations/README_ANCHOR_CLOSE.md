# anchor_close 마이그레이션 가이드

## 개요

추천 기준 종가(anchor_close) 오류를 수정하기 위한 마이그레이션 및 Backfill 가이드입니다.

## 문제 정의

- 추천 카드에 표시되는 "추천 기준 종가"가 실제 해당 거래일의 종가와 불일치
- 원인: 추천 생성 시점의 기준가가 불변값으로 고정되지 않았거나, 조회 시 재계산되면서 소스가 섞임

## 해결 방법

1. **추천 생성 시점에 anchor_close 저장**: 추천 생성 시 한 번만 결정하여 DB에 저장
2. **API 응답에서 재계산 금지**: 저장된 anchor_close를 그대로 사용
3. **기존 데이터 Backfill**: 과거 추천의 anchor_close 업데이트

## 마이그레이션 실행

### 1. 스키마 마이그레이션

```bash
# PostgreSQL에 연결하여 마이그레이션 실행
psql -U your_user -d your_database -f backend/migrations/add_anchor_fields_to_scan_rank.sql
```

또는 Python에서 실행:

```python
from db_manager import db_manager

with db_manager.get_cursor(commit=True) as cur:
    with open('backend/migrations/add_anchor_fields_to_scan_rank.sql', 'r') as f:
        cur.execute(f.read())
```

### 2. 기존 데이터 Backfill

```bash
# 전체 데이터 Backfill (Dry-run 먼저 실행 권장)
python backend/backfill/backfill_anchor_close.py --dry-run

# 실제 업데이트
python backend/backfill/backfill_anchor_close.py

# 특정 날짜만 업데이트
python backend/backfill/backfill_anchor_close.py --date 20251210

# 특정 종목만 업데이트
python backend/backfill/backfill_anchor_close.py --ticker 047810

# 제한된 건수만 테스트
python backend/backfill/backfill_anchor_close.py --limit 10
```

## 검증

### 1. 한국항공우주 케이스 검증

```bash
# 2025-12-10 추천 케이스 확인
python backend/scripts/debug_anchor_close.py --ticker 047810 --date 20251210
```

### 2. 테스트 실행

```bash
# anchor_close 정확성 테스트
python -m pytest backend/tests/test_anchor_close.py -v
```

## 변경 사항 요약

### 1. 스키마 변경

- `scan_rank` 테이블에 다음 필드 추가:
  - `anchor_date`: 추천 기준 거래일 (DATE)
  - `anchor_close`: 추천 기준 종가 (DOUBLE PRECISION)
  - `anchor_price_type`: 가격 타입 (TEXT, 기본값: "CLOSE")
  - `anchor_source`: 데이터 소스 (TEXT, 기본값: "KRX_EOD")

### 2. 코드 변경

- **date_helper.py**: 공용 함수 추가
  - `get_trading_date()`: 거래일 결정
  - `get_anchor_close()`: 종가 조회
  - `is_trading_day_kr()`: 거래일 확인

- **services/scan_service.py**: 추천 생성 시 anchor 필드 저장
  - `save_scan_snapshot()`: anchor 필드 추가

- **main.py**: API 응답에서 anchor_close 우선 사용
  - `/scan-by-date/{date}`: anchor_close 우선 사용
  - `/v3/scan`: anchor_close 우선 사용

### 3. 절대 원칙

1. ✅ 추천 기준점은 "추천 생성 시점에 단 한 번 결정"하고 DB에 저장
2. ✅ 화면/API 요청 시점에 anchor_close를 재계산하지 않음
3. ✅ close vs adjClose 중 하나로 고정 (현재는 "CLOSE" 사용)
4. ✅ 거래일 정의와 타임존(Asia/Seoul), 장 마감 기준을 공용 함수로 통일
5. ✅ 기존 데이터(backfill)까지 처리하여 과거 추천의 anchor_close도 정합하게 만듦

## 모니터링 (권장)

매일 EOD 이후 추천된 종목에 대해:
- (추천 레코드의 anchor_close) vs (공식 종가) 비교
- 불일치 발견 시 에러 로그/알림

모니터링 스크립트는 별도로 구현 필요.

## 롤백 방법

만약 문제가 발생하면:

1. anchor 필드 제거 (필요한 경우):
```sql
ALTER TABLE scan_rank DROP COLUMN IF EXISTS anchor_date;
ALTER TABLE scan_rank DROP COLUMN IF EXISTS anchor_close;
ALTER TABLE scan_rank DROP COLUMN IF EXISTS anchor_price_type;
ALTER TABLE scan_rank DROP COLUMN IF EXISTS anchor_source;
```

2. 코드 롤백: Git에서 이전 버전으로 복원

## 참고

- 마이그레이션 파일: `backend/migrations/add_anchor_fields_to_scan_rank.sql`
- Backfill 스크립트: `backend/backfill/backfill_anchor_close.py`
- 디버그 스크립트: `backend/scripts/debug_anchor_close.py`
- 테스트 코드: `backend/tests/test_anchor_close.py`


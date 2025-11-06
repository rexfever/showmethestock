# 보고서 기능 개선 계획

## 📋 현재 상태 분석

### ✅ 잘 작동하는 부분
1. **계층적 보고서 구조**: 주간 → 월간 → 분기 → 연간 자동 집계
2. **반복 스캔 분석**: 종목별 재등장 패턴 분석
3. **기본 통계**: 평균 수익률, 수익 종목 비율, 최고/최저 성과
4. **프론트엔드 UI**: 탭 기반 인터페이스, 손실 파란색 표시

### ❌ 발견된 문제점

#### 1. 경로 불일치 문제 [P0 - Critical]
**문제:**
- `ReportGenerator.reports_dir = "backend/reports"` (상대 경로)
- 작업 디렉토리에 따라 `backend/backend/reports` 또는 `reports`로 해석됨
- API가 파일을 찾지 못하는 경우 발생

**영향:**
- 보고서 생성은 되지만 API에서 조회 불가
- 수동으로 파일 복사 필요

**해결:**
```python
# 절대 경로 사용 또는 명확한 상대 경로
import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
self.reports_dir = os.path.join(BASE_DIR, "backend", "reports")
```

#### 2. 날짜 형식 불일치 [P0 - Critical]
**문제:**
- DB: `YYYYMMDD` 형식 (예: `20251103`)
- `_get_scan_data`: `YYYY-MM-DD` 형식 기대 (예: `2025-11-03`)
- SQL BETWEEN 쿼리가 실패하여 데이터 미조회

**영향:**
- 주간 보고서 생성 실패 (데이터 없음 오류)
- 수동으로 DB 직접 조회 필요

**해결:**
```python
def _get_scan_data(self, start_date: str, end_date: str) -> List[Dict]:
    # YYYY-MM-DD → YYYYMMDD 변환
    start_compact = start_date.replace('-', '') if '-' in start_date else start_date
    end_compact = end_date.replace('-', '') if '-' in end_date else end_date
    
    cursor.execute("""
        SELECT date, code, name, current_price, volume, change_rate, market, strategy, 
               indicators, trend, flags, details, returns, recurrence
        FROM scan_rank 
        WHERE date >= ? AND date <= ?
        ORDER BY date
    """, (start_compact, end_compact))
```

#### 3. 수익률 계산 성능 문제 [P1 - High]
**문제:**
- `_calculate_returns_for_stocks`: 순차 처리
- 종목당 API 호출 발생
- 5개 종목 기준 약 5초 소요

**해결:**
```python
from concurrent.futures import ThreadPoolExecutor

def _calculate_returns_for_stocks(self, stocks_data: List) -> List[Dict]:
    processed_stocks = []
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(self._process_stock_return, row): row 
            for row in stocks_data
        }
        
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                processed_stocks.append(result)
    
    return processed_stocks
```

#### 4. 통계 계산 한계 [P2 - Medium]
**현재:**
- 평균 수익률, 수익 종목 비율, 최고/최저만 제공

**개선:**
- 중앙값 (median)
- 표준편차 (volatility)
- 수익률 분포 (histogram)
- 승률 (win rate) - 상위 10% vs 하위 10%
- 최대 낙폭 (max drawdown)
- 샤프 비율 (Sharpe ratio)

#### 5. 에러 처리 부족 [P1 - High]
**문제:**
- `print()`로만 에러 출력
- API 응답에 상세한 에러 정보 없음
- 프론트엔드에서 에러 원인 파악 어려움

**해결:**
```python
import logging
logger = logging.getLogger(__name__)

def generate_weekly_report(self, year: int, month: int, week: int) -> bool:
    try:
        # ... 기존 로직
    except Exception as e:
        logger.error(f"주간 보고서 생성 오류: {e}", exc_info=True)
        return False
```

#### 6. 중복 종목 처리 로직 [P2 - Medium]
**문제:**
- 같은 종목이 여러 주차/월에 나타날 때 최고 수익률만 유지
- 시간 경과에 따른 수익률 변화 추적 불가
- 첫 스캔일 vs 최고 수익률 기준 혼용

**개선:**
```python
# 옵션 1: 첫 스캔일 기준 (추천 시점 기준)
# 옵션 2: 최신 스캔일 기준 (현재 성과 기준)
# 옵션 3: 기간별 평균 수익률
```

#### 7. 데이터 검증 부족 [P2 - Medium]
**문제:**
- `scan_price`가 0인 경우 처리 안 함
- `current_return` 계산 실패 시 조용히 0으로 처리
- 데이터 무결성 검증 없음

**해결:**
```python
def _calculate_returns_for_stocks(self, stocks_data: List) -> List[Dict]:
    processed_stocks = []
    
    for row in stocks_data:
        date, code, name, current_price, volume, change_rate, market, strategy, ...
        
        # 데이터 검증
        if not name or not code or code == 'NORESULT':
            continue
            
        if not current_price or current_price <= 0:
            logger.warning(f"유효하지 않은 가격: {code} {name} - {current_price}")
            continue
        
        # 수익률 계산
        returns_info = calculate_returns(code, date)
        if not returns_info:
            logger.warning(f"수익률 계산 실패: {code} {name}")
            continue
        
        # ... 처리
```

#### 8. 프론트엔드 개선 [P2 - Medium]
**문제:**
- 사용 가능한 보고서 목록과 선택 가능한 옵션 불일치
- 에러 메시지가 단순함
- 로딩 상태 표시 부족

**개선:**
- 사용 가능한 보고서만 선택 가능하도록 드롭다운 제한
- 상세 에러 메시지 (예: "데이터 없음" vs "파일 읽기 실패")
- 진행률 표시 (대용량 보고서 생성 시)

#### 9. 캐싱 부재 [P3 - Low]
**문제:**
- 매번 수익률 계산 (API 호출)
- 보고서 조회 시마다 파일 읽기

**개선:**
- 수익률 계산 결과 캐싱 (TTL: 1시간)
- 보고서 파일 메타데이터 캐싱

#### 10. 보고서 스케줄링 문제 [P1 - High]
**문제:**
- `report_scheduler`가 venv_new 경로 오류로 동작 안 함
- 주간 보고서 생성 시점 불명확
- 월간 보고서는 주간 보고서 의존 (주간이 없으면 실패)

**해결:**
- 스케줄러 경로 수정
- 주간 보고서 없을 때 DB에서 직접 생성
- 보고서 생성 실패 시 재시도 로직

## 🎯 우선순위별 개선 계획

### Phase 1: Critical Fixes (즉시)
1. ✅ 경로 문제 해결 (절대 경로 사용)
2. ✅ 날짜 형식 통일 (YYYYMMDD로 통일)
3. ✅ 에러 처리 개선 (로깅 추가)

### Phase 2: Performance (1주일 내)
4. 수익률 계산 병렬화
5. 데이터 검증 강화
6. 보고서 스케줄러 수정

### Phase 3: Enhancement (2주일 내)
7. 통계 지표 확장
8. 중복 종목 처리 개선
9. 프론트엔드 UX 개선

### Phase 4: Optimization (1개월 내)
10. 캐싱 구현
11. 보고서 생성 최적화

## 📊 예상 효과

### 성능
- 보고서 생성 시간: 5초 → 1초 (병렬화)
- API 응답 시간: 100ms → 50ms (캐싱)

### 안정성
- 데이터 조회 실패율: 30% → 5%
- 에러 추적 가능성: 20% → 90%

### 사용성
- 프론트엔드 에러 이해도: 40% → 80%
- 보고서 생성 성공률: 70% → 95%


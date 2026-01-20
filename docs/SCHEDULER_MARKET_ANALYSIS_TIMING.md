# 스케줄러 장세 분석 타이밍 문제 분석

**작성일**: 2026-01-08  
**문제**: 장세 분석이 완료되지 않았는데 스캔이 실행될 수 있음

---

## 현재 상황

### 스케줄러 실행 시간

| 시간 | 작업 | 예상 소요 시간 | 완료 예상 시간 |
|------|------|---------------|---------------|
| 15:40 | 장세 분석 실행 | 약 10초~1분 | 15:40~15:41 |
| 15:42 | 스캔 실행 (v2 + v3) | 약 4-6분 | 15:46~15:48 |

### 문제점

1. **장세 분석 완료 전 스캔 실행 가능**
   - 장세 분석이 15:40에 시작
   - 스캔이 15:42에 시작
   - 장세 분석이 1분 이상 걸리면 스캔이 장세 분석 완료 전에 실행될 수 있음

2. **중복 장세 분석**
   - 스케줄러에서 장세 분석 실행 (15:40)
   - `/scan` API에서 장세 분석을 다시 실행 (15:42)
   - 중복 작업으로 리소스 낭비

3. **캐시 클리어 문제**
   - `/scan` API에서 `market_analyzer.clear_cache()` 호출 (649줄)
   - 스케줄러에서 생성한 캐시가 클리어될 수 있음

---

## 코드 분석

### `/scan` API 동작

```python
# backend/main.py (649-652줄)
if config.market_analysis_enable:
    try:
        # 캐시 클리어 후 새로 분석 (레짐 버전 자동 선택)
        market_analyzer.clear_cache()  # ⚠️ 캐시 클리어
        regime_version = getattr(config, 'regime_version', 'v1')
        market_condition = market_analyzer.analyze_market_condition(today_as_of, regime_version=regime_version)
```

**문제점**:
- 스케줄러에서 생성한 캐시를 클리어함
- 장세 분석을 다시 수행 (중복)
- 스케줄러 장세 분석 완료 여부 확인 안 함

---

## 해결 방안

### 옵션 1: 스캔 시간 조정 (권장) ⭐

**변경 내용**:
- 스캔 시간을 15:42 → 15:43으로 변경
- 장세 분석 완료 후 실행 보장

**장점**:
- 구현 간단 (한 줄 수정)
- 장세 분석 완료 후 스캔 보장
- 기존 로직 변경 없음

**단점**:
- 스캔이 약 1분 지연

**코드 변경**:
```python
# backend/scheduler.py
schedule.every().day.at("15:43").do(run_scan)  # 15:42 → 15:43
```

---

### 옵션 2: 스캔 API에서 DB 조회 우선

**변경 내용**:
- `/scan` API에서 DB에 저장된 장세 분석 결과를 먼저 확인
- 있으면 재사용, 없으면 분석 수행

**장점**:
- 중복 분석 방지
- 리소스 절약

**단점**:
- 코드 변경 필요
- DB 조회 로직 추가

**코드 변경**:
```python
# backend/main.py
# DB에서 장세 분석 결과 조회
market_condition = None
if config.market_analysis_enable:
    try:
        # DB에서 먼저 조회
        with db_manager.get_cursor(commit=False) as cur:
            cur.execute("""
                SELECT * FROM market_conditions 
                WHERE date = %s
            """, (today_as_of,))
            row = cur.fetchone()
            
            if row:
                # DB에 저장된 결과 사용
                market_condition = MarketCondition.from_db_row(row)
            else:
                # DB에 없으면 분석 수행
                market_analyzer.clear_cache()
                market_condition = market_analyzer.analyze_market_condition(today_as_of, regime_version=regime_version)
    except Exception as e:
        print(f"⚠️ 시장 분석 실패, 기본 조건 사용: {e}")
```

---

### 옵션 3: 스캔 함수에서 장세 분석 완료 확인

**변경 내용**:
- `run_scan()` 함수에서 장세 분석 완료 여부 확인
- 완료되지 않았으면 대기 또는 재시도

**장점**:
- 장세 분석 완료 보장
- 스캔 시간 유지

**단점**:
- 구현 복잡
- 타임아웃 처리 필요

**코드 변경**:
```python
def run_scan():
    """한국 주식 스캔 실행 (15:42) - v2와 v3 모두 실행"""
    if not is_trading_day():
        logger.info(f"오늘은 거래일이 아닙니다. 스캔을 건너뜁니다.")
        return
    
    # 장세 분석 완료 확인
    from datetime import datetime
    today = datetime.now().strftime('%Y%m%d')
    with db_manager.get_cursor(commit=False) as cur:
        cur.execute("""
            SELECT COUNT(*) FROM market_conditions 
            WHERE date = %s
        """, (today,))
        count = cur.fetchone()[0]
        
        if count == 0:
            logger.warning("장세 분석이 완료되지 않았습니다. 30초 대기 후 재시도...")
            import time
            time.sleep(30)
            # 재확인
            cur.execute("""
                SELECT COUNT(*) FROM market_conditions 
                WHERE date = %s
            """, (today,))
            count = cur.fetchone()[0]
            if count == 0:
                logger.error("장세 분석이 완료되지 않았습니다. 스캔을 건너뜁니다.")
                return
    
    # 스캔 실행
    ...
```

---

## 권장 사항

### 즉시 적용: 옵션 1 (스캔 시간 조정)

**이유**:
1. 구현 간단 (한 줄 수정)
2. 장세 분석 완료 후 스캔 보장
3. 기존 로직 변경 없음
4. 안정성 향상

**변경 내용**:
```python
# backend/scheduler.py
schedule.every().day.at("15:43").do(run_scan)  # 15:42 → 15:43
```

**예상 타임라인**:
- 15:40: 장세 분석 시작
- 15:40~15:41: 장세 분석 완료
- 15:43: 스캔 시작 (장세 분석 완료 후)
- 15:47~15:49: 스캔 완료

---

### 추가 개선: 옵션 2 (DB 조회 우선)

**이유**:
1. 중복 분석 방지
2. 리소스 절약
3. 성능 향상

**적용 시기**:
- 옵션 1 적용 후 추가 개선으로 고려

---

## 최종 권장 스케줄

| 시간 | 작업 | 비고 |
|------|------|------|
| 15:40 | 장세 분석 실행 | 기존 유지 |
| 15:43 | 스캔 실행 (v2 + v3) | **15:42 → 15:43 변경** |
| 15:47 | 상태 평가 | 기존 유지 |

**이유**:
- 장세 분석 완료 후 스캔 보장
- 리소스 경합 최소화
- 안정성 향상

---

**작성일**: 2026-01-08  
**최종 업데이트**: 2026-01-08  
**상태**: 분석 완료, 권장 사항 제시


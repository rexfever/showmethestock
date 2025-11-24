# OHLCV 캐시 TTL 분석

## 현재 설정
- **TTL**: 5분 (300초)
- **고정값**: 모든 상황에서 동일

## 문제점 분석

### 1. 장중 데이터 (실시간 필요)
**상황**: 현재 날짜, 장중 시간대
- **문제**: 5분 TTL이 너무 길 수 있음
- **영향**: 최신 가격 정보가 5분간 지연될 수 있음
- **예시**: 
  - 09:00에 조회 → 캐시 저장
  - 09:03에 재조회 → 09:00 데이터 반환 (3분 지연)

### 2. 장 마감 후 데이터 (변경 없음)
**상황**: 현재 날짜, 장 마감 후
- **문제**: 5분 TTL이 너무 짧음
- **영향**: 불필요한 재조회 발생
- **예시**:
  - 16:00 (장 마감) 조회 → 캐시 저장
  - 16:10에 재조회 → 캐시 만료로 재조회 (불필요)

### 3. 과거 데이터 (영구 고정)
**상황**: 과거 날짜 (base_dt가 과거)
- **문제**: 5분 TTL이 너무 짧음
- **영향**: 과거 데이터는 변경되지 않으므로 영구 캐싱 가능
- **예시**:
  - 2025-11-20 데이터 조회 → 캐시 저장
  - 5분 후 재조회 → 캐시 만료로 재조회 (불필요)

## 개선 방안

### 옵션 1: 상황별 TTL 적용 (권장)

#### 1.1 과거 날짜 데이터
- **TTL**: 무제한 (또는 매우 긴 시간)
- **이유**: 과거 데이터는 변경되지 않음

#### 1.2 장 마감 후 데이터
- **TTL**: 다음 거래일까지
- **이유**: 장 마감 후 데이터는 변경되지 않음

#### 1.3 장중 데이터
- **TTL**: 1분 (또는 30초)
- **이유**: 실시간성 필요

### 옵션 2: 동적 TTL 계산

```python
def _calculate_ttl(self, base_dt: Optional[str]) -> int:
    """상황에 맞는 TTL 계산"""
    from datetime import datetime
    import pytz
    
    KST = pytz.timezone('Asia/Seoul')
    now = datetime.now(KST)
    
    # 과거 날짜: 무제한 (1년)
    if base_dt:
        try:
            base_date = datetime.strptime(base_dt, "%Y%m%d").date()
            if base_date < now.date():
                return 365 * 24 * 3600  # 1년
        except:
            pass
    
    # 장중 여부 확인
    hour = now.hour
    minute = now.minute
    
    # 장중: 09:00 ~ 15:30
    if (9 <= hour < 15) or (hour == 15 and minute <= 30):
        return 60  # 1분
    
    # 장 마감 후: 다음 거래일까지
    # (간단히 24시간으로 설정, 실제로는 다음 거래일 계산 필요)
    return 24 * 3600  # 24시간
```

### 옵션 3: 캐시 무효화 전략

#### 3.1 수동 무효화
- 특정 종목의 캐시를 수동으로 클리어
- 장중 실시간 데이터 필요 시 사용

#### 3.2 시간 기반 무효화
- 장 시작 시 전체 캐시 클리어
- 장 마감 후 과거 데이터는 유지

## 권장 구현

### 단계별 적용

#### Phase 1: 과거 날짜 영구 캐싱
```python
def _calculate_ttl(self, base_dt: Optional[str]) -> int:
    """TTL 계산"""
    if base_dt:
        from datetime import datetime
        try:
            base_date = datetime.strptime(base_dt, "%Y%m%d").date()
            now_date = datetime.now().date()
            if base_date < now_date:
                # 과거 날짜: 1년 캐싱
                return 365 * 24 * 3600
        except:
            pass
    
    # 현재 날짜: 기본 5분
    return 300
```

#### Phase 2: 장중/장 마감 구분
```python
def _is_market_open(self) -> bool:
    """장중 여부 확인"""
    from datetime import datetime
    import pytz
    
    KST = pytz.timezone('Asia/Seoul')
    now = datetime.now(KST)
    hour = now.hour
    minute = now.minute
    
    # 평일만 확인 (주말 제외)
    if now.weekday() >= 5:  # 토요일(5), 일요일(6)
        return False
    
    # 장중: 09:00 ~ 15:30
    return (9 <= hour < 15) or (hour == 15 and minute <= 30)

def _calculate_ttl(self, base_dt: Optional[str]) -> int:
    """TTL 계산"""
    # 과거 날짜: 1년
    if base_dt:
        from datetime import datetime
        try:
            base_date = datetime.strptime(base_dt, "%Y%m%d").date()
            now_date = datetime.now().date()
            if base_date < now_date:
                return 365 * 24 * 3600
        except:
            pass
    
    # 현재 날짜
    if self._is_market_open():
        return 60  # 장중: 1분
    else:
        return 24 * 3600  # 장 마감 후: 24시간
```

## 현재 5분 TTL의 문제

### 1. 과도한 캐싱 (장중)
- 실시간 데이터가 5분간 지연될 수 있음
- 사용자가 최신 가격을 기대하지만 오래된 데이터를 받을 수 있음

### 2. 불충분한 캐싱 (장 마감 후/과거)
- 변경되지 않는 데이터를 5분마다 재조회
- 불필요한 API 호출 증가

### 3. 일관성 부족
- 모든 상황에서 동일한 TTL 적용
- 데이터 특성을 고려하지 않음

## 결론

**현재 5분 TTL은 임의로 설정된 값**이며, 다음과 같은 문제가 있습니다:

1. ❌ 장중 실시간성 부족
2. ❌ 장 마감 후/과거 데이터 불필요한 재조회
3. ❌ 데이터 특성 미고려

**권장 개선**:
- ✅ 과거 날짜: 1년 캐싱
- ✅ 장중: 1분 캐싱
- ✅ 장 마감 후: 24시간 캐싱


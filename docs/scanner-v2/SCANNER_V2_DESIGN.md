# 스캐너 V2 설계 문서

## 목표
- 기존 스캐너의 개선된 버전
- 더 명확한 구조와 모듈화
- 향상된 성능과 유지보수성

## 현재 스캐너 구조 분석

### 주요 구성 요소
1. **지표 계산**: `compute_indicators()`
2. **매칭 로직**: `match_stats()` - 신호 충족 여부 판단
3. **점수 계산**: `score_conditions()` - 점수 산정 및 전략 분류
4. **단일 종목 스캔**: `scan_one_symbol()` - 종목별 스캔 실행
5. **배치 스캔**: `scan_with_preset()` - 유니버스 전체 스캔
6. **Fallback 로직**: `execute_scan_with_fallback()` - 단계별 완화

### 개선 포인트
1. **모듈화**: 기능별로 명확히 분리
2. **설정 관리**: 동적 조건 적용 개선
3. **성능**: 병렬 처리 최적화
4. **테스트**: 단위 테스트 용이한 구조
5. **확장성**: 새로운 지표/전략 추가 용이

## V2 구조 설계

### 디렉토리 구조
```
backend/scanner_v2/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── scanner.py          # 메인 스캐너 클래스
│   ├── indicator_calculator.py  # 지표 계산
│   ├── filter_engine.py    # 필터링 엔진
│   └── scorer.py           # 점수 계산
├── strategies/
│   ├── __init__.py
│   ├── base_strategy.py    # 기본 전략 인터페이스
│   ├── signal_strategy.py  # 신호 기반 전략
│   └── score_strategy.py   # 점수 기반 전략
├── filters/
│   ├── __init__.py
│   ├── hard_filters.py     # 하드 필터
│   ├── soft_filters.py     # 소프트 필터
│   └── market_filters.py   # 시장 상황 기반 필터
└── utils/
    ├── __init__.py
    ├── market_condition.py # 시장 조건 처리
    └── result_formatter.py  # 결과 포맷팅
```

### 핵심 클래스 설계

#### 1. ScannerV2 (메인 클래스)
```python
class ScannerV2:
    """스캐너 V2 메인 클래스"""
    
    def __init__(self, config, market_analyzer=None):
        self.config = config
        self.market_analyzer = market_analyzer
        self.indicator_calculator = IndicatorCalculator()
        self.filter_engine = FilterEngine()
        self.scorer = Scorer()
    
    def scan(self, universe: List[str], date: str = None) -> List[ScanResult]:
        """스캔 실행"""
        pass
    
    def scan_one(self, code: str, date: str = None) -> Optional[ScanResult]:
        """단일 종목 스캔"""
        pass
```

#### 2. FilterEngine (필터 엔진)
```python
class FilterEngine:
    """필터링 엔진"""
    
    def apply_hard_filters(self, data, stock_info) -> bool:
        """하드 필터 적용 (통과/실패)"""
        pass
    
    def apply_soft_filters(self, data, market_condition) -> tuple:
        """소프트 필터 적용 (신호 충족 여부, 신호 개수)"""
        pass
```

#### 3. Scorer (점수 계산)
```python
class Scorer:
    """점수 계산기"""
    
    def calculate_score(self, data, signals) -> float:
        """점수 계산"""
        pass
    
    def determine_strategy(self, score, signals) -> Strategy:
        """전략 결정"""
        pass
```

## 마이그레이션 계획

### Phase 1: 기본 구조 생성
- [ ] 디렉토리 구조 생성
- [ ] 기본 클래스 정의
- [ ] 인터페이스 설계

### Phase 2: 핵심 기능 이전
- [ ] 지표 계산 로직 이전
- [ ] 필터링 로직 이전
- [ ] 점수 계산 로직 이전

### Phase 3: 개선 및 최적화
- [ ] 성능 최적화
- [ ] 테스트 코드 작성
- [ ] 문서화

### Phase 4: 통합 및 배포
- [ ] 기존 코드와 통합
- [ ] 점진적 전환
- [ ] 기존 코드 제거

## 주요 개선 사항

### 1. 모듈화
- 기능별 명확한 분리
- 의존성 최소화
- 테스트 용이성

### 2. 설정 관리
- 동적 조건 적용 개선
- 시장 상황별 설정 분리
- 설정 검증 로직

### 3. 성능
- 병렬 처리 최적화
- 캐싱 전략
- 메모리 효율성

### 4. 확장성
- 플러그인 방식 지표 추가
- 전략 패턴 적용
- 필터 체인 구조

## 다음 단계
1. 기본 구조 생성
2. 핵심 기능 이전
3. 테스트 및 검증
4. 점진적 배포


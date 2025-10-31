# 개인 API Key 기능 도입 영향도 분석 - 2025.10.24

## 1. 기존 서비스 현황

### 1.1 현재 아키텍처
```
사용자 → 웹 서비스 → 공통 키움 API → 키움 서버
                   (단일 API Key)
```

### 1.2 기존 기능들
- AI 스캔 서비스 (15:36 자동 실행)
- 종목 분석 및 추천
- 성과 보고서 생성
- 사용자 인증 (Google/Kakao OAuth)
- 포트폴리오 관리 (가상)

## 2. 새로운 아키텍처

### 2.1 변경된 아키텍처
```
사용자A → 웹 서비스 → 사용자A API Key → 키움 서버
사용자B → 웹 서비스 → 사용자B API Key → 키움 서버
사용자C → 웹 서비스 → 사용자C API Key → 키움 서버
```

### 2.2 추가된 컴포넌트
- 사용자별 API Key 관리 시스템
- 개인별 자동매매 엔진
- 사용자별 매매 기록 관리

## 3. 기존 서비스별 영향도 분석

### 3.1 AI 스캔 서비스 ⚠️ **중간 영향**

**현재 상태:**
```python
# 공통 API로 스캔 실행
def daily_scan():
    api = KiwoomAPI()  # 공통 API Key
    kospi_codes = api.get_top_codes("KOSPI", 100)
    kosdaq_codes = api.get_top_codes("KOSDAQ", 100)
    # 스캔 실행 및 결과 저장
```

**변경 필요사항:**
```python
# 스캔은 공통 API 유지 (데이터 수집용)
def daily_scan():
    api = KiwoomAPI()  # 공통 API Key (스캔용)
    # 스캔 실행은 기존과 동일
    
# 자동매매는 개인별 API 사용
def execute_auto_trading(scan_results):
    active_users = get_active_users()
    for user_id in active_users:
        user_api = UserSpecificKiwoomAPI(user_id)
        # 개인 API로 매매 실행
```

**영향도:** 🟡 **낮음-중간**
- 스캔 로직은 변경 없음
- 자동매매 부분만 개인별 처리 추가

### 3.2 종목 분석 서비스 ✅ **영향 없음**

**현재 상태:**
- 시세 데이터 조회
- 기술적 분석
- 종목 정보 제공

**변경 필요사항:**
- **변경 없음** (읽기 전용 기능)
- 공통 API로 계속 사용 가능

**영향도:** 🟢 **없음**

### 3.3 성과 보고서 생성 ⚠️ **중간 영향**

**현재 상태:**
```python
# 가상의 성과 데이터 기반
def generate_weekly_report():
    # 임의의 수익률 데이터 사용
    return report_data
```

**변경 필요사항:**
```python
# 실제 사용자별 매매 기록 기반
def generate_user_report(user_id):
    user_trades = get_user_trade_records(user_id)
    # 실제 매매 기록으로 보고서 생성
    return real_report_data

# 전체 보고서 (익명화된 통계)
def generate_aggregate_report():
    all_users_data = get_all_users_performance()
    # 개인정보 제거 후 통계 생성
    return aggregate_report
```

**영향도:** 🟡 **중간**
- 보고서 생성 로직 수정 필요
- 실제 데이터 기반으로 변경

### 3.4 사용자 인증 시스템 ⚠️ **중간 영향**

**현재 상태:**
```python
# 기본 OAuth 인증만
class AuthContext:
    user_id: str
    name: str
    email: str
    provider: str
```

**변경 필요사항:**
```python
# API Key 등록 상태 추가
class AuthContext:
    user_id: str
    name: str
    email: str
    provider: str
    has_api_key: bool          # 추가
    auto_trading_enabled: bool # 추가
    daily_limit: float         # 추가
```

**영향도:** 🟡 **중간**
- 사용자 정보에 API Key 상태 추가
- 권한 체크 로직 수정

### 3.5 포트폴리오 관리 🔴 **높은 영향**

**현재 상태:**
```python
# 가상 포트폴리오
def add_to_portfolio(user_id, code, quantity, price):
    # 가상 데이터 저장
    save_virtual_portfolio(user_id, code, quantity, price)
```

**변경 필요사항:**
```python
# 실제 포트폴리오 연동
def get_real_portfolio(user_id):
    user_api = UserSpecificKiwoomAPI(user_id)
    # 실제 계좌에서 보유 종목 조회
    return user_api.get_positions()

# 가상 + 실제 포트폴리오 통합
def get_integrated_portfolio(user_id):
    real_portfolio = get_real_portfolio(user_id)
    virtual_portfolio = get_virtual_portfolio(user_id)
    return merge_portfolios(real_portfolio, virtual_portfolio)
```

**영향도:** 🔴 **높음**
- 실제 계좌 연동으로 대폭 변경
- 가상/실제 포트폴리오 구분 필요

## 4. 데이터베이스 영향도

### 4.1 새로 추가되는 테이블
```sql
-- 사용자 API Key 정보
CREATE TABLE user_api_keys (...)

-- 실제 매매 기록
CREATE TABLE trade_records (...)

-- 3단계 청산 전략
CREATE TABLE three_tier_strategies (...)

-- 조건부 주문
CREATE TABLE conditional_orders (...)
```

### 4.2 기존 테이블 수정
```sql
-- 사용자 테이블에 API 상태 추가
ALTER TABLE users ADD COLUMN has_api_key BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN auto_trading_enabled BOOLEAN DEFAULT FALSE;

-- 포트폴리오 테이블에 실제/가상 구분 추가
ALTER TABLE portfolio ADD COLUMN portfolio_type TEXT DEFAULT 'VIRTUAL';
```

**영향도:** 🟡 **중간**
- 기존 데이터 마이그레이션 필요
- 새로운 테이블 추가

## 5. 프론트엔드 영향도

### 5.1 새로 추가되는 페이지/기능
- API Key 등록 페이지
- 자동매매 설정 페이지
- 실제 매매 현황 대시보드
- 개인별 성과 분석 페이지

### 5.2 기존 페이지 수정
```javascript
// 더보기 페이지
export default function More() {
    const { user, hasApiKey, autoTradingEnabled } = useAuth();
    
    return (
        <div>
            {/* 기존 내용 */}
            
            {/* 새로 추가 */}
            {!hasApiKey && (
                <APIKeyRegistration />
            )}
            
            {hasApiKey && (
                <AutoTradingSettings />
            )}
        </div>
    );
}

// 포트폴리오 페이지
export default function Portfolio() {
    const [portfolioType, setPortfolioType] = useState('ALL');
    
    return (
        <div>
            {/* 실제/가상 포트폴리오 탭 추가 */}
            <PortfolioTabs 
                type={portfolioType} 
                onChange={setPortfolioType} 
            />
            
            {/* 기존 포트폴리오 표시 */}
            <PortfolioList type={portfolioType} />
        </div>
    );
}
```

**영향도:** 🟡 **중간**
- 새로운 UI 컴포넌트 추가
- 기존 페이지 일부 수정

## 6. API 엔드포인트 영향도

### 6.1 새로 추가되는 API
```python
# API Key 관리
POST /api/user/register-api
GET /api/user/api-status
PUT /api/user/auto-trading/enable

# 자동매매
POST /api/auto-trading/execute
GET /api/auto-trading/status
GET /api/auto-trading/history

# 실제 포트폴리오
GET /api/portfolio/real
GET /api/portfolio/integrated
```

### 6.2 기존 API 수정
```python
# 기존 스캔 API는 변경 없음
GET /api/scan  # 그대로 유지

# 포트폴리오 API 확장
GET /api/portfolio?type=virtual|real|all  # 파라미터 추가

# 보고서 API 확장
GET /api/reports/weekly?user_only=true  # 개인 보고서 옵션 추가
```

**영향도:** 🟡 **중간**
- 기존 API 대부분 유지
- 새로운 API 추가

## 7. 보안 및 권한 영향도

### 7.1 새로운 보안 요구사항
- API Key 암호화 저장 (AES-256)
- 사용자별 데이터 접근 권한 분리
- API Key 유효성 검증
- 개인정보 보호 강화

### 7.2 권한 체계 변경
```python
# 기존: 단순 로그인 체크
@require_auth
def some_endpoint():
    pass

# 변경: API Key 등록 상태 체크
@require_api_key
def trading_endpoint():
    pass

@require_auto_trading_enabled
def auto_trading_endpoint():
    pass
```

**영향도:** 🟡 **중간**
- 새로운 권한 체계 추가
- 기존 권한은 유지

## 8. 성능 영향도

### 8.1 긍정적 영향
- 사용자별 API 분산으로 레이트 리밋 완화
- 개인별 처리로 시스템 부하 분산

### 8.2 부정적 영향
- 사용자 수만큼 API 연결 증가
- 암호화/복호화 오버헤드
- 데이터베이스 쿼리 복잡도 증가

**영향도:** 🟡 **중간**
- 전반적으로는 성능 개선 예상

## 9. 운영 영향도

### 9.1 모니터링 복잡도 증가
- 사용자별 API 상태 모니터링
- 개인별 매매 성과 추적
- API Key 만료/오류 관리

### 9.2 지원 업무 증가
- API Key 등록 지원
- 개인별 매매 문의 처리
- 계좌 연동 문제 해결

**영향도:** 🔴 **높음**
- 운영 복잡도 상당히 증가

## 10. 마이그레이션 계획

### 10.1 단계별 배포 전략
```
Phase 1: API Key 관리 시스템 구축
- 기존 서비스 영향 없음
- 새로운 기능만 추가

Phase 2: 자동매매 기능 추가
- 기존 스캔 서비스 유지
- 자동매매는 옵션 기능

Phase 3: 실제 포트폴리오 연동
- 가상 포트폴리오와 병행 운영
- 점진적 전환

Phase 4: 통합 및 최적화
- 불필요한 기능 정리
- 성능 최적화
```

### 10.2 롤백 계획
- 각 Phase별 독립적 롤백 가능
- 기존 기능은 항상 유지
- 데이터 손실 없는 안전한 전환

## 11. 총 영향도 요약

| 서비스 영역 | 영향도 | 변경 범위 | 비고 |
|------------|--------|-----------|------|
| AI 스캔 | 🟡 낮음-중간 | 자동매매 부분만 | 스캔 로직은 유지 |
| 종목 분석 | 🟢 없음 | 변경 없음 | 읽기 전용 기능 |
| 성과 보고서 | 🟡 중간 | 로직 수정 | 실제 데이터 기반 |
| 사용자 인증 | 🟡 중간 | 상태 정보 추가 | 기본 인증은 유지 |
| 포트폴리오 | 🔴 높음 | 대폭 변경 | 실제 계좌 연동 |
| 데이터베이스 | 🟡 중간 | 테이블 추가/수정 | 마이그레이션 필요 |
| 프론트엔드 | 🟡 중간 | 새 페이지 추가 | 기존 UI 일부 수정 |
| API | 🟡 중간 | 새 엔드포인트 추가 | 기존 API 대부분 유지 |
| 보안 | 🟡 중간 | 권한 체계 확장 | 기존 보안 유지 |
| 성능 | 🟡 중간 | 분산 처리 | 전반적 개선 예상 |
| 운영 | 🔴 높음 | 복잡도 증가 | 모니터링/지원 강화 |

## 12. 권장사항

### 12.1 점진적 도입
1. **기존 서비스 유지하면서 새 기능 추가**
2. **사용자 선택권 제공** (가상 vs 실제)
3. **충분한 테스트 기간** 확보
4. **단계별 피드백 수집** 및 개선

### 12.2 리스크 완화
1. **롤백 계획 수립**
2. **데이터 백업 강화**
3. **모니터링 시스템 구축**
4. **사용자 교육 및 지원 체계** 마련

---

**결론**: 개인 API Key 기능 도입은 **중간-높은 수준의 영향**을 미치지만, **점진적 도입과 적절한 마이그레이션 전략**으로 안전하게 구현 가능합니다.
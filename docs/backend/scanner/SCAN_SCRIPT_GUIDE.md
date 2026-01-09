# 스캔 스크립트 작성 가이드

## 개요

서버 API를 사용하여 특정 날짜 또는 날짜 범위에 대해 스캔을 실행하는 스크립트 작성 방법을 설명합니다.

## 기본 원칙

1. **서버 API 사용**: 키움 API를 직접 호출하지 않고 서버의 `/scan` 엔드포인트를 사용
2. **캐시 자동 관리**: 서버가 필요한 캐시를 자동으로 생성/업데이트
3. **재사용 가능**: 날짜와 설정만 변경하여 재사용 가능한 템플릿 제공

## 스캔 스크립트 템플릿

### 기본 템플릿

```python
#!/usr/bin/env python3
"""
스캔 스크립트 템플릿
날짜와 설정만 변경하여 재사용 가능
"""
import os
import sys
import requests
from datetime import datetime, timedelta
import holidays

# 서버 URL 설정
if os.getenv('SSH_CONNECTION'):
    SERVER_URL = "http://localhost:8010"
else:
    SERVER_URL = os.getenv('BACKEND_URL', "http://localhost:8010")

import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_trading_days(start_date, end_date):
    """거래일 목록 생성 (주말, 공휴일 제외)"""
    kr_holidays = holidays.SouthKorea()
    trading_days = []
    current = start_date
    
    while current <= end_date:
        # 주말(토일) 및 공휴일 제외
        if current.weekday() < 5 and current not in kr_holidays:
            trading_days.append(current.strftime("%Y%m%d"))
        current += timedelta(days=1)
    
    return trading_days

def scan_date(date_str: str) -> bool:
    """
    서버 API를 사용하여 특정 날짜 스캔 실행
    
    Args:
        date_str: 스캔 날짜 (YYYYMMDD)
    
    Returns:
        성공 여부
    """
    try:
        logger.info(f"\n{'='*80}")
        logger.info(f"스캔 실행: {date_str}")
        logger.info(f"{'='*80}")
        
        # 서버 API 호출
        url = f"{SERVER_URL}/scan"
        params = {
            "date": date_str,
            "save_snapshot": True,
            "kospi_limit": 200,
            "kosdaq_limit": 200
        }
        
        logger.info(f"  🌐 서버 API 호출: {url}")
        logger.info(f"  📅 날짜: {date_str}")
        
        response = requests.get(url, params=params, timeout=600)
        
        if response.status_code == 200:
            data = response.json()
            matched_count = data.get('matched_count', 0)
            items = data.get('items', [])
            scanner_version = data.get('scanner_version', 'unknown')
            market_condition = data.get('market_condition', {})
            
            logger.info(f"  ✅ 스캔 완료: {matched_count}개 종목 발견")
            logger.info(f"  📊 스캐너 버전: {scanner_version}")
            
            if market_condition:
                final_regime = market_condition.get('final_regime', 'N/A')
                midterm_regime = market_condition.get('midterm_regime', 'N/A')
                logger.info(f"  📊 레짐 분석:")
                logger.info(f"     - final_regime: {final_regime}")
                logger.info(f"     - midterm_regime: {midterm_regime}")
            
            if items:
                logger.info(f"  🎯 상위 5개 종목:")
                for i, item in enumerate(items[:5], 1):
                    ticker = item.get('ticker', 'N/A')
                    name = item.get('name', 'N/A')
                    score = item.get('score', 0)
                    strategy = item.get('strategy', 'N/A')
                    logger.info(f"     {i}. {ticker} ({name}): 점수={score:.2f}, 전략={strategy}")
            
            # DB 저장은 서버에서 자동으로 처리됨
            logger.info(f"  💾 DB 저장 완료 (서버에서 처리됨)")
            
            return True
        else:
            error_detail = ""
            try:
                error_data = response.json()
                error_detail = error_data.get('detail', '')
            except:
                error_detail = response.text[:200]
            
            logger.error(f"  ❌ 스캔 실패: HTTP {response.status_code}")
            if error_detail:
                logger.error(f"     오류: {error_detail}")
            return False
        
    except requests.exceptions.RequestException as e:
        logger.error(f"  ❌ 네트워크 오류: {date_str} - {e}")
        return False
    except Exception as e:
        logger.error(f"  ❌ 스캔 실패: {date_str} - {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """메인 함수"""
    logger.info("🚀 스캔 배치 실행 시작 (서버 API 사용)")
    logger.info(f"🌐 서버 URL: {SERVER_URL}")
    
    # 서버 상태 확인
    try:
        health_url = f"{SERVER_URL}/health"
        health_response = requests.get(health_url, timeout=5)
        if health_response.status_code == 200:
            logger.info("✅ 서버 연결 확인")
        else:
            logger.warning(f"⚠️ 서버 상태 확인 실패: HTTP {health_response.status_code}")
    except Exception as e:
        logger.error(f"❌ 서버 연결 실패: {e}")
        logger.error("서버가 실행 중인지 확인하세요.")
        return
    
    # ==========================================
    # 여기서 날짜 범위 설정
    # ==========================================
    start_date = datetime(2026, 1, 2)  # 시작 날짜 변경
    end_date = datetime(2026, 1, 31)   # 종료 날짜 변경
    
    # 거래일 목록 생성
    trading_days = get_trading_days(start_date, end_date)
    logger.info(f"📅 총 {len(trading_days)}개 거래일 처리 예정")
    logger.info(f"   시작: {trading_days[0] if trading_days else 'N/A'}")
    logger.info(f"   종료: {trading_days[-1] if trading_days else 'N/A'}")
    
    success_count = 0
    error_count = 0
    
    for i, date_str in enumerate(trading_days, 1):
        logger.info(f"\n📈 [{i}/{len(trading_days)}] {date_str} 스캔 시작...")
        
        if scan_date(date_str):
            success_count += 1
        else:
            error_count += 1
    
    logger.info(f"\n{'='*80}")
    logger.info(f"🎉 배치 실행 완료!")
    logger.info(f"✅ 성공: {success_count}일")
    logger.info(f"❌ 실패: {error_count}일")
    if success_count + error_count > 0:
        logger.info(f"📊 성공률: {success_count/(success_count+error_count)*100:.1f}%")
    logger.info(f"{'='*80}\n")

if __name__ == "__main__":
    main()
```

## 사용 예시

### 예시 1: 특정 날짜 스캔

```python
# main() 함수에서 날짜 범위 설정
start_date = datetime(2026, 1, 7)
end_date = datetime(2026, 1, 7)  # 같은 날짜로 설정
```

### 예시 2: 여러 날짜 스캔

```python
# main() 함수에서 날짜 범위 설정
start_date = datetime(2026, 1, 5)
end_date = datetime(2026, 1, 7)
```

### 예시 3: 한 달 전체 스캔

```python
# main() 함수에서 날짜 범위 설정
start_date = datetime(2026, 1, 2)  # 1일은 보통 공휴일
end_date = datetime(2026, 1, 31)
```

## 빠른 실행 스크립트

단일 날짜를 빠르게 스캔하려면:

```python
#!/usr/bin/env python3
"""단일 날짜 빠른 스캔"""
import requests
import sys

SERVER_URL = "http://localhost:8010"
date_str = sys.argv[1] if len(sys.argv) > 1 else "20260107"

url = f"{SERVER_URL}/scan"
params = {
    "date": date_str,
    "save_snapshot": True,
    "kospi_limit": 200,
    "kosdaq_limit": 200
}

print(f"📅 {date_str} 스캔 실행 중...")
response = requests.get(url, params=params, timeout=600)

if response.status_code == 200:
    data = response.json()
    print(f"✅ 완료: {data.get('matched_count', 0)}개 종목")
else:
    print(f"❌ 실패: HTTP {response.status_code}")
```

**사용법:**
```bash
python3 quick_scan.py 20260107
```

## 서버 API 파라미터

### `/scan` 엔드포인트

**URL**: `GET /scan`

**파라미터**:
- `date` (선택): 스캔 날짜 (YYYYMMDD 형식). 없으면 오늘 날짜
- `save_snapshot` (선택): DB 저장 여부 (기본값: true)
- `kospi_limit` (선택): KOSPI 종목 수 제한 (기본값: 200)
- `kosdaq_limit` (선택): KOSDAQ 종목 수 제한 (기본값: 200)

**응답**:
```json
{
  "as_of": "20260107",
  "universe_count": 400,
  "matched_count": 5,
  "scanner_version": "v3",
  "items": [...],
  "market_condition": {...}
}
```

## 스캐너 버전

서버는 `scanner_settings` 테이블의 `scanner_version` 설정에 따라 자동으로 스캐너 버전을 선택합니다:
- `v1`: 기본 스캐너
- `v2`: V2 스캐너
- `v3`: V3 스캐너 (midterm + v2_lite)

## 주의사항

1. **서버 실행 확인**: 스크립트 실행 전 서버가 실행 중인지 확인
2. **타임아웃**: 스캔은 시간이 걸릴 수 있으므로 타임아웃을 충분히 설정 (기본: 600초)
3. **거래일 확인**: 주말과 공휴일은 자동으로 제외됨
4. **캐시**: 서버가 필요한 캐시를 자동으로 생성/업데이트하므로 별도 캐시 작업 불필요

## 기존 스크립트 위치

- `backend/scripts/scan_january_2026.py`: 2026년 1월 스캔 예시
- `backend/tools/rescan_date.py`: 날짜별 재스캔 (키움 API 직접 사용, 서버 API 사용 권장)

## 관련 문서

- [API 엔드포인트](../API_ENDPOINTS.md)
- [서버 운영 메뉴얼](../deployment/SERVER_OPERATION_MANUAL.md)
- [Scanner V2 사용 가이드](../scanner-v2/SCANNER_V2_USAGE.md)


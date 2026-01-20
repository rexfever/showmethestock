#!/usr/bin/env python3
"""
2026년 1월 스캔 스크립트 (서버 API 사용)

이 스크립트는 docs/backend/scanner/SCAN_SCRIPT_GUIDE.md의 템플릿을 기반으로 작성되었습니다.
날짜 범위만 변경하여 재사용 가능합니다.
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

def scan_date(date_str: str, skip_existing: bool = False) -> bool:
    """
    서버 API를 사용하여 특정 날짜 스캔 실행
    
    Args:
        date_str: 스캔 날짜 (YYYYMMDD)
        skip_existing: 기존 데이터가 있으면 건너뛰기 (서버에서 처리)
    
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
            market_condition = data.get('market_condition', {})
            
            logger.info(f"  ✅ 스캔 완료: {matched_count}개 종목 발견")
            
            if market_condition:
                final_regime = market_condition.get('final_regime', 'N/A')
                midterm_regime = market_condition.get('midterm_regime', 'N/A')
                logger.info(f"  📊 레짐 분석:")
                logger.info(f"     - final_regime: {final_regime}")
                logger.info(f"     - midterm_regime: {midterm_regime}")
            
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
    logger.info("🚀 2026년 1월 스캔 배치 실행 시작 (서버 API 사용)")
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
    
    # 날짜 범위 설정
    start_date = datetime(2026, 1, 2)
    end_date = datetime(2026, 1, 31)
    
    # 거래일 목록 생성
    trading_days = get_trading_days(start_date, end_date)
    logger.info(f"📅 총 {len(trading_days)}개 거래일 처리 예정")
    logger.info(f"   시작: {trading_days[0] if trading_days else 'N/A'}")
    logger.info(f"   종료: {trading_days[-1] if trading_days else 'N/A'}")
    
    success_count = 0
    error_count = 0
    
    for i, date_str in enumerate(trading_days, 1):
        logger.info(f"\n📈 [{i}/{len(trading_days)}] {date_str} 스캔 시작...")
        
        if scan_date(date_str, skip_existing=False):
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


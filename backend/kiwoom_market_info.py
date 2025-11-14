"""
키움 REST API를 통한 시황 정보 조회 모듈
"""
from typing import Dict, Optional
from datetime import datetime
import pandas as pd
from kiwoom_api import api


# 주요 지수 코드 (키움 API 기준)
# 참고: 키움 API에서는 지수를 종목처럼 조회할 수 있음
INDEX_CODES = {
    'KOSPI': '069500',      # KOSPI 200 지수 (현재 사용 중인 코드)
    'KOSPI200': '069500',   # KOSPI 200 지수
    'KOSDAQ': '229200',     # KOSDAQ 150 지수 (대표 지수로 사용)
    'KOSDAQ150': '229200',  # KOSDAQ 150 지수
    # 참고: 실제 KOSPI/KOSDAQ 지수 코드는 키움 API 문서 확인 필요
    # 일부 지수는 종목 코드처럼 조회되지 않을 수 있음
}


def get_index_info(index_name: str = 'KOSPI', date: str = None) -> Optional[Dict]:
    """
    지수 정보 조회
    
    Args:
        index_name: 'KOSPI', 'KOSPI200', 'KOSDAQ', 'KOSDAQ150'
        date: 기준일 (YYYYMMDD), None이면 최신 데이터
    
    Returns:
        {
            'index_name': str,
            'code': str,
            'date': str,
            'close': float,
            'change': float,
            'change_rate': float,
            'volume': int,
            'high': float,
            'low': float,
            'open': float
        } or None
    """
    if index_name.upper() not in INDEX_CODES:
        return None
    
    code = INDEX_CODES[index_name.upper()]
    
    try:
        # OHLCV 데이터 가져오기
        df = api.get_ohlcv(code, 2, date)
        
        if df.empty or len(df) < 1:
            return None
        
        latest = df.iloc[-1]
        
        # 전일 종가 (2일치 데이터가 있으면)
        prev_close = df.iloc[-2]['close'] if len(df) >= 2 else latest['close']
        
        # 등락률 계산
        change = latest['close'] - prev_close
        change_rate = (change / prev_close * 100) if prev_close > 0 else 0.0
        
        return {
            'index_name': index_name.upper(),
            'code': code,
            'date': latest['date'],
            'close': float(latest['close']),
            'change': float(change),
            'change_rate': round(change_rate, 2),
            'volume': int(latest['volume']),
            'high': float(latest['high']),
            'low': float(latest['low']),
            'open': float(latest['open']),
            'prev_close': float(prev_close)
        }
    except Exception as e:
        print(f"⚠️ 지수 정보 조회 실패 ({index_name}): {e}")
        return None


def get_market_overview(date: str = None) -> Dict:
    """
    시장 전체 시황 정보 조회
    
    Args:
        date: 기준일 (YYYYMMDD), None이면 최신 데이터
    
    Returns:
        {
            'date': str,
            'kospi': {...},
            'kosdaq': {...},
            'summary': {
                'kospi_change_rate': float,
                'kosdaq_change_rate': float,
                'market_sentiment': str  # 'bull', 'neutral', 'bear'
            }
        }
    """
    kospi = get_index_info('KOSPI', date)
    kosdaq = get_index_info('KOSDAQ', date)
    
    # 시장 심리 판단
    market_sentiment = 'neutral'
    if kospi and kosdaq:
        kospi_rate = kospi.get('change_rate', 0)
        kosdaq_rate = kosdaq.get('change_rate', 0)
        avg_rate = (kospi_rate + kosdaq_rate) / 2
        
        if avg_rate >= 1.0:
            market_sentiment = 'bull'
        elif avg_rate <= -1.0:
            market_sentiment = 'bear'
    
    return {
        'date': date or datetime.now().strftime('%Y%m%d'),
        'kospi': kospi,
        'kosdaq': kosdaq,
        'summary': {
            'kospi_change_rate': kospi.get('change_rate', 0) if kospi else 0,
            'kosdaq_change_rate': kosdaq.get('change_rate', 0) if kosdaq else 0,
            'market_sentiment': market_sentiment
        }
    }


if __name__ == '__main__':
    # 테스트
    print("📊 시황 정보 조회 테스트")
    print("=" * 60)
    
    # KOSPI 정보
    kospi = get_index_info('KOSPI')
    if kospi:
        print(f"\nKOSPI:")
        print(f"  날짜: {kospi['date']}")
        print(f"  종가: {kospi['close']:,.2f}")
        print(f"  등락: {kospi['change']:+,.2f} ({kospi['change_rate']:+.2f}%)")
        print(f"  거래량: {kospi['volume']:,}")
    
    # KOSDAQ 정보
    kosdaq = get_index_info('KOSDAQ')
    if kosdaq:
        print(f"\nKOSDAQ:")
        print(f"  날짜: {kosdaq['date']}")
        print(f"  종가: {kosdaq['close']:,.2f}")
        print(f"  등락: {kosdaq['change']:+,.2f} ({kosdaq['change_rate']:+.2f}%)")
        print(f"  거래량: {kosdaq['volume']:,}")
    
    # 시장 전체 시황
    overview = get_market_overview()
    print(f"\n시장 전체 시황:")
    print(f"  KOSPI 등락률: {overview['summary']['kospi_change_rate']:+.2f}%")
    print(f"  KOSDAQ 등락률: {overview['summary']['kosdaq_change_rate']:+.2f}%")
    print(f"  시장 심리: {overview['summary']['market_sentiment']}")


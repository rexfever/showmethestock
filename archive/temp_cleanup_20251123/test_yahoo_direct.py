#!/usr/bin/env python3
"""
Yahoo Finance API 직접 테스트
"""
import requests
import time
import random

def test_yahoo_direct():
    """Yahoo Finance API 직접 테스트"""
    
    # 다양한 User-Agent 시도
    user_agents = [
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    ]
    
    symbols = ["SPY", "QQQ"]
    
    for symbol in symbols:
        print(f"\n🔄 {symbol} 테스트 중...")
        
        # 랜덤 User-Agent 선택
        headers = {
            'User-Agent': random.choice(user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # 최근 1년 데이터만 요청 (period1/period2 조정)
        import time
        now = int(time.time())
        one_year_ago = now - (365 * 24 * 60 * 60)
        
        url = f"https://query1.finance.yahoo.com/v7/finance/download/{symbol}?period1={one_year_ago}&period2={now}&interval=1d&events=history"
        
        try:
            print(f"   URL: {url}")
            response = requests.get(url, headers=headers, timeout=30)
            
            print(f"   Status: {response.status_code}")
            print(f"   Headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                lines = response.text.split('\n')
                print(f"   ✅ 성공: {len(lines)}줄")
                if len(lines) > 1:
                    print(f"   첫 줄: {lines[0]}")
                    print(f"   마지막 줄: {lines[-2] if len(lines) > 2 else lines[-1]}")
            else:
                print(f"   ❌ 실패: {response.status_code}")
                print(f"   응답: {response.text[:200]}")
                
        except Exception as e:
            print(f"   ❌ 예외: {e}")
        
        # 요청 간격
        time.sleep(3)

def test_alternative_endpoints():
    """대안 엔드포인트 테스트"""
    print(f"\n🔄 대안 엔드포인트 테스트")
    
    # Yahoo Finance v8 API
    symbol = "SPY"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    
    # v8 API 시도
    try:
        url = f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}?range=1mo&interval=1d"
        print(f"   v8 API: {url}")
        
        response = requests.get(url, headers=headers, timeout=30)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ v8 API 성공")
            if 'chart' in data and 'result' in data['chart']:
                result = data['chart']['result'][0]
                timestamps = result['timestamp']
                prices = result['indicators']['quote'][0]['close']
                print(f"   데이터 포인트: {len(timestamps)}개")
                print(f"   최근 가격: {prices[-1]}")
        else:
            print(f"   ❌ v8 API 실패: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ v8 API 예외: {e}")

if __name__ == "__main__":
    print("🚀 Yahoo Finance API 직접 테스트")
    test_yahoo_direct()
    test_alternative_endpoints()
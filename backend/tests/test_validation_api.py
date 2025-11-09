"""
검증 API 엔드포인트 테스트
"""
import asyncio
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import get_market_validation


async def test_api():
    """API 엔드포인트 테스트"""
    print("\n" + "="*80)
    print("검증 API 엔드포인트 테스트")
    print("="*80)
    
    # 오늘 날짜로 테스트
    today_str = datetime.now().strftime('%Y%m%d')
    print(f"\n📅 테스트 날짜: {today_str}")
    
    try:
        result = await get_market_validation(date=today_str)
        
        print(f"\n✅ API 호출 성공")
        print(f"   - ok: {result.get('ok')}")
        
        if result.get('ok'):
            data = result.get('data', {})
            validations = data.get('validations', [])
            
            print(f"   - 검증 데이터 수: {len(validations)}")
            print(f"   - 첫 완전 시점: {data.get('first_complete_time')}")
            
            print(f"\n📊 검증 데이터:")
            for v in validations:
                time_str = v.get('time')
                kospi = v.get('kospi_return')
                samsung = v.get('samsung_return')
                available = v.get('data_available')
                complete = v.get('data_complete')
                error = v.get('error_message')
                
                status = "✅" if complete else ("⚠️" if available else "❌")
                
                print(f"   {status} {time_str}: ", end="")
                if kospi is not None:
                    print(f"KOSPI {kospi:+.2f}%", end="")
                if samsung is not None:
                    print(f", 삼성 {samsung:+.2f}%", end="")
                if error:
                    print(f" (오류: {error})", end="")
                print()
        else:
            print(f"   - 오류: {result.get('error')}")
    
    except Exception as e:
        print(f"\n❌ API 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*80)


if __name__ == "__main__":
    asyncio.run(test_api())


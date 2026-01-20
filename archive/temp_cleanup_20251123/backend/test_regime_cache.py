"""
레짐 캐시 시스템 테스트
"""
import asyncio
from datetime import datetime
from services.regime_analyzer_cached import regime_analyzer_cached
from services.us_futures_data_v8 import us_futures_data_v8

async def test_regime_cache():
    """레짐 캐시 시스템 테스트"""
    print("🧪 레짐 캐시 시스템 테스트 시작")
    
    # 1. 캐시 통계 확인
    print("\n📊 캐시 통계:")
    stats = regime_analyzer_cached.get_cache_stats()
    print(f"  총 파일: {stats.get('total_files', 0)}개")
    print(f"  총 크기: {stats.get('total_size', 0):,} bytes")
    
    # 2. 미국 데이터 테스트
    print("\n🇺🇸 미국 데이터 테스트:")
    symbols = ['SPY', 'QQQ', 'ES=F', '^VIX']
    for symbol in symbols:
        try:
            df = us_futures_data_v8.fetch_data(symbol)
            print(f"  {symbol}: {len(df)}개 행")
        except Exception as e:
            print(f"  {symbol}: 실패 - {e}")
    
    # 3. 레짐 분석 테스트
    print("\n📈 레짐 분석 테스트:")
    today = datetime.now().strftime('%Y%m%d')
    
    # 첫 번째 호출 (캐시 미스)
    print(f"  첫 번째 분석 ({today})...")
    result1 = regime_analyzer_cached.analyze_regime_v4_cached(today)
    print(f"    결과: {result1['final_regime']} (점수: {result1['final_score']:.2f})")
    
    # 두 번째 호출 (캐시 히트)
    print(f"  두 번째 분석 ({today})...")
    result2 = regime_analyzer_cached.analyze_regime_v4_cached(today)
    print(f"    결과: {result2['final_regime']} (점수: {result2['final_score']:.2f})")
    
    # 4. 최신 미국 데이터 조회
    print("\n📊 최신 미국 데이터:")
    latest_data = us_futures_data_v8.get_all_latest_data()
    for symbol, data in latest_data.items():
        print(f"  {symbol}: {data['close']:.2f} ({data['change_pct']:+.2f}%)")
    
    # 5. 캐시 통계 재확인
    print("\n📊 최종 캐시 통계:")
    final_stats = regime_analyzer_cached.get_cache_stats()
    print(f"  총 파일: {final_stats.get('total_files', 0)}개")
    print(f"  총 크기: {final_stats.get('total_size', 0):,} bytes")
    for cache_type, info in final_stats.get('by_type', {}).items():
        print(f"  {cache_type}: {info['count']}개 파일, {info['size']:,} bytes")
    
    print("\n✅ 레짐 캐시 시스템 테스트 완료")

if __name__ == "__main__":
    asyncio.run(test_regime_cache())
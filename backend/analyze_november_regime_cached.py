"""
캐시 기반 11월 레짐 분석
"""
import asyncio
from datetime import datetime, timedelta
from services.regime_analyzer_cached import regime_analyzer_cached
import json

async def analyze_november_regime_cached():
    """캐시 기반 11월 레짐 분석"""
    print("📊 캐시 기반 11월 레짐 분석 시작")
    
    # 11월 날짜 범위 생성
    november_dates = []
    for day in range(1, 24):  # 11월 1일~23일
        date_str = f"20241101" if day == 1 else f"202411{day:02d}"
        november_dates.append(date_str)
    
    results = {}
    
    print(f"📅 분석 대상: {len(november_dates)}일")
    
    for i, date in enumerate(november_dates, 1):
        try:
            print(f"  [{i:2d}/{len(november_dates)}] {date} 분석 중...")
            
            # 캐시 기반 레짐 분석
            result = regime_analyzer_cached.analyze_regime_v4_cached(date)
            
            results[date] = {
                'date': date,
                'final_regime': result['final_regime'],
                'final_score': result['final_score'],
                'kr_score': result['kr_score'],
                'kr_regime': result['kr_regime'],
                'us_prev_score': result['us_prev_score'],
                'us_prev_regime': result['us_prev_regime'],
                'us_futures_score': result['us_futures_score'],
                'us_futures_regime': result['us_futures_regime']
            }
            
            print(f"    결과: {result['final_regime']} (점수: {result['final_score']:.2f})")
            
        except Exception as e:
            print(f"    오류: {e}")
            results[date] = {
                'date': date,
                'error': str(e)
            }
    
    # 결과 통계
    regime_counts = {}
    total_score = 0
    valid_results = 0
    
    for date, result in results.items():
        if 'final_regime' in result:
            regime = result['final_regime']
            regime_counts[regime] = regime_counts.get(regime, 0) + 1
            total_score += result['final_score']
            valid_results += 1
    
    avg_score = total_score / valid_results if valid_results > 0 else 0
    
    print(f"\n📈 11월 레짐 분석 결과:")
    print(f"  총 분석일: {valid_results}일")
    print(f"  평균 점수: {avg_score:.2f}")
    print(f"  레짐 분포:")
    for regime, count in regime_counts.items():
        percentage = (count / valid_results * 100) if valid_results > 0 else 0
        print(f"    {regime}: {count}일 ({percentage:.1f}%)")
    
    # 결과 저장
    output_file = f"november_regime_analysis_cached_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    summary = {
        'analysis_date': datetime.now().isoformat(),
        'period': 'November 2024',
        'total_days': valid_results,
        'average_score': avg_score,
        'regime_distribution': regime_counts,
        'daily_results': results
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 결과 저장: {output_file}")
    
    # 캐시 통계 출력
    cache_stats = regime_analyzer_cached.get_cache_stats()
    print(f"\n📊 캐시 통계:")
    print(f"  총 캐시 파일: {cache_stats.get('total_files', 0)}개")
    print(f"  총 캐시 크기: {cache_stats.get('total_size', 0):,} bytes")
    
    return summary

if __name__ == "__main__":
    asyncio.run(analyze_november_regime_cached())
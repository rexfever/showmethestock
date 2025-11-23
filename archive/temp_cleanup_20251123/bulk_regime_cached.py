#!/usr/bin/env python3
"""
캐시 기반 대량 레짐 분석 스크립트
"""
import sys
import os
from datetime import datetime, timedelta
import json

# backend 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

def bulk_regime_analysis_cached(start_date, end_date):
    """캐시 기반 대량 레짐 분석"""
    try:
        from services.regime_analyzer_cached import regime_analyzer_cached
        
        print(f"📊 캐시 기반 대량 레짐 분석: {start_date} ~ {end_date}")
        
        # 날짜 범위 생성
        start_dt = datetime.strptime(start_date, '%Y%m%d')
        end_dt = datetime.strptime(end_date, '%Y%m%d')
        
        results = {}
        regime_counts = {}
        total_days = 0
        
        current_dt = start_dt
        while current_dt <= end_dt:
            date_str = current_dt.strftime('%Y%m%d')
            
            try:
                # 캐시 기반 분석
                result = regime_analyzer_cached.analyze_regime_v4_cached(date_str)
                
                results[date_str] = {
                    'date': date_str,
                    'final_regime': result['final_regime'],
                    'final_score': result['final_score'],
                    'kr_regime': result['kr_regime'],
                    'kr_score': result['kr_score'],
                    'us_prev_regime': result['us_prev_regime'],
                    'us_prev_score': result['us_prev_score'],
                    'us_futures_regime': result['us_futures_regime'],
                    'us_futures_score': result['us_futures_score']
                }
                
                # 통계 업데이트
                regime = result['final_regime']
                regime_counts[regime] = regime_counts.get(regime, 0) + 1
                total_days += 1
                
                print(f"  {date_str}: {result['final_regime']} ({result['final_score']:.2f})")
                
            except Exception as e:
                print(f"  {date_str}: 오류 - {e}")
                results[date_str] = {'date': date_str, 'error': str(e)}
            
            current_dt += timedelta(days=1)
        
        # 결과 요약
        print(f"\n📈 분석 결과 요약:")
        print(f"  총 분석일: {total_days}일")
        print(f"  레짐 분포:")
        for regime, count in regime_counts.items():
            pct = (count / total_days * 100) if total_days > 0 else 0
            print(f"    {regime}: {count}일 ({pct:.1f}%)")
        
        # 결과 저장
        output_file = f"bulk_regime_cached_{start_date}_{end_date}.json"
        summary = {
            'analysis_date': datetime.now().isoformat(),
            'period': f"{start_date} ~ {end_date}",
            'total_days': total_days,
            'regime_distribution': regime_counts,
            'daily_results': results,
            'cache_based': True
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 결과 저장: {output_file}")
        
        # 캐시 통계
        cache_stats = regime_analyzer_cached.get_cache_stats()
        print(f"\n📊 캐시 통계:")
        print(f"  캐시 파일: {cache_stats.get('total_files', 0)}개")
        print(f"  캐시 크기: {cache_stats.get('total_size', 0):,} bytes")
        
        return summary
        
    except Exception as e:
        print(f"❌ 대량 분석 실패: {e}")
        return None

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='캐시 기반 대량 레짐 분석')
    parser.add_argument('--start', required=True, help='시작 날짜 (YYYYMMDD)')
    parser.add_argument('--end', required=True, help='종료 날짜 (YYYYMMDD)')
    
    args = parser.parse_args()
    
    print("🚀 캐시 기반 대량 레짐 분석 시작\n")
    bulk_regime_analysis_cached(args.start, args.end)
    print("\n🎯 완료!")
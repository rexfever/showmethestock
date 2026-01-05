"""
Regime v4 + Scanner v2 최종 검증 스크립트

6개 날짜로 실제 스캔을 수행하여 검증합니다.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import datetime
from market_analyzer import market_analyzer
from scanner_factory import scan_with_scanner
from config import config


def test_end_to_end_scan(date_str: str):
    """특정 날짜로 스캔 테스트"""
    print(f"\n{'='*80}")
    print(f"날짜: {date_str}")
    print(f"{'='*80}")
    
    try:
        # 1. 시장 분석
        market_condition = market_analyzer.analyze_market_condition_v4(date_str, mode="backtest")
        
        midterm_regime = getattr(market_condition, 'midterm_regime', None)
        final_regime = getattr(market_condition, 'final_regime', None)
        short_term_risk = getattr(market_condition, 'short_term_risk_score', None)
        
        print(f"📊 레짐 분석:")
        print(f"   - midterm_regime: {midterm_regime}")
        print(f"   - final_regime: {final_regime}")
        print(f"   - short_term_risk_score: {short_term_risk}")
        
        # 2. 스캔 실행
        universe = config.universe_kospi + config.universe_kosdaq
        print(f"📋 유니버스: {len(universe)}개")
        
        scan_items = scan_with_scanner(universe, {}, date_str, market_condition)
        
        # 3. horizon별 카운트 (scanner v2의 _apply_regime_cutoff 로직 시뮬레이션)
        from scanner_v2.config_regime import REGIME_CUTOFFS
        
        regime = midterm_regime if midterm_regime else (final_regime if final_regime else 'neutral')
        cutoffs = REGIME_CUTOFFS.get(regime, REGIME_CUTOFFS['neutral'])
        
        swing_count = 0
        position_count = 0
        longterm_count = 0
        
        for item in scan_items:
            score = item.get('score', 0)
            flags = item.get('flags', {})
            risk_score = flags.get('risk_score', 0) if isinstance(flags, dict) else 0
            
            # short_term_risk_score 가중 적용
            if short_term_risk is not None:
                risk_score = (risk_score or 0) + short_term_risk
            
            effective_score = (score or 0) - (risk_score or 0)
            
            if effective_score >= cutoffs['swing']:
                swing_count += 1
            if effective_score >= cutoffs['position']:
                position_count += 1
            if effective_score >= cutoffs['longterm']:
                longterm_count += 1
        
        print(f"🎯 스캔 결과:")
        print(f"   - 총 후보: {len(scan_items)}개")
        print(f"   - swing: {swing_count}개 (cutoff: {cutoffs['swing']})")
        print(f"   - position: {position_count}개 (cutoff: {cutoffs['position']})")
        print(f"   - longterm: {longterm_count}개 (cutoff: {cutoffs['longterm']})")
        
        return {
            'date': date_str,
            'midterm_regime': midterm_regime,
            'final_regime': final_regime,
            'short_term_risk': short_term_risk,
            'swing_count': swing_count,
            'position_count': position_count,
            'longterm_count': longterm_count
        }
        
    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == '__main__':
    test_dates = [
        '20250723',  # neutral/bull
        '20250917',  # neutral
        '20251022',  # neutral
        '20250820',  # bear
        '20251105',  # crash
        '20251121',  # crash
    ]
    
    results = []
    for date in test_dates:
        result = test_end_to_end_scan(date)
        if result:
            results.append(result)
    
    # 결과 테이블 출력
    print(f"\n{'='*80}")
    print("최종 검증 결과 테이블")
    print(f"{'='*80}")
    print(f"{'date':<12} {'midterm':<10} {'final':<10} {'short_risk':<10} {'swing':<8} {'position':<10} {'longterm':<10}")
    print("-" * 80)
    
    for r in results:
        print(f"{r['date']:<12} {str(r['midterm_regime']):<10} {str(r['final_regime']):<10} "
              f"{str(r['short_term_risk']):<10} {r['swing_count']:<8} {r['position_count']:<10} "
              f"{r['longterm_count']:<10}")
    
    # 검증 기준 확인
    print(f"\n{'='*80}")
    print("검증 기준 확인")
    print(f"{'='*80}")
    
    all_pass = True
    for r in results:
        regime = r['midterm_regime'] or r['final_regime'] or 'neutral'
        
        if regime == 'crash':
            if r['swing_count'] != 0:
                print(f"❌ {r['date']}: crash에서 swing={r['swing_count']} (기대: 0)")
                all_pass = False
            if r['position_count'] != 0:
                print(f"❌ {r['date']}: crash에서 position={r['position_count']} (기대: 0)")
                all_pass = False
            if r['longterm_count'] < 0:
                print(f"❌ {r['date']}: crash에서 longterm={r['longterm_count']} (기대: >= 0)")
                all_pass = False
            else:
                print(f"✅ {r['date']}: crash 검증 통과")
        
        elif regime == 'bear':
            if r['swing_count'] != 0:
                print(f"❌ {r['date']}: bear에서 swing={r['swing_count']} (기대: 0)")
                all_pass = False
            if r['position_count'] > 8:
                print(f"❌ {r['date']}: bear에서 position={r['position_count']} (기대: <= 8)")
                all_pass = False
            else:
                print(f"✅ {r['date']}: bear 검증 통과")
        
        elif regime in ['neutral', 'bull']:
            if r['swing_count'] > 20:
                print(f"❌ {r['date']}: {regime}에서 swing={r['swing_count']} (기대: <= 20)")
                all_pass = False
            if r['position_count'] > 15:
                print(f"❌ {r['date']}: {regime}에서 position={r['position_count']} (기대: <= 15)")
                all_pass = False
            else:
                print(f"✅ {r['date']}: {regime} 검증 통과")
    
    print(f"\n{'='*80}")
    if all_pass:
        print("✅ 전체 검증: PASS")
    else:
        print("❌ 전체 검증: FAIL")
    print(f"{'='*80}")




































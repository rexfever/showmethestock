#!/usr/bin/env python3
"""
Global Regime v3 고급 분석 예제
"""
import sys
import os
import json
from datetime import datetime, timedelta
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../backend'))

def regime_correlation_analysis():
    """레짐과 시장 수익률 상관관계 분석"""
    print("📈 레짐-수익률 상관관계 분석\n")
    
    try:
        from scanner_v2.regime_backtest_v3 import run_regime_backtest
        
        # 최근 30일 백테스트
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
        
        print(f"분석 기간: {start_date} ~ {end_date}")
        
        result = run_regime_backtest(start_date, end_date)
        
        if 'error' not in result:
            print("\n📊 레짐별 성과 요약:")
            for regime, stats in result['regime_stats'].items():
                print(f"  {regime}:")
                print(f"    평균 수익률: {stats['avg_return']*100:+.2f}%")
                print(f"    승률: {stats['win_rate']*100:.1f}%")
                print(f"    변동성: {stats['std_return']*100:.2f}%")
                
                # 샤프 비율 계산 (간단 버전)
                if stats['std_return'] > 0:
                    sharpe = stats['avg_return'] / stats['std_return']
                    print(f"    샤프 비율: {sharpe:.2f}")
        
        return result
        
    except Exception as e:
        print(f"❌ 상관관계 분석 실패: {e}")
        return None

def regime_prediction_accuracy():
    """레짐 예측 정확도 분석"""
    print("\n🎯 레짐 예측 정확도 분석\n")
    
    try:
        from services.regime_storage import load_regime
        from kiwoom_api import api
        from main import is_trading_day
        
        # 최근 20일 데이터로 분석
        end_date = datetime.now()
        predictions = []
        
        for i in range(20):
            date_dt = end_date - timedelta(days=i)
            date_str = date_dt.strftime('%Y%m%d')
            
            try:
                if not is_trading_day(date_str):
                    continue
            except:
                if date_dt.weekday() >= 5:
                    continue
            
            # 레짐 데이터 로드
            regime_data = load_regime(date_str)
            if not regime_data:
                continue
            
            # 다음날 실제 수익률 계산
            next_date = (date_dt + timedelta(days=1)).strftime('%Y%m%d')
            try:
                df = api.get_ohlcv("069500", 2, next_date)  # KOSPI200
                if not df.empty and len(df) >= 2:
                    actual_return = (df.iloc[-1]['close'] / df.iloc[-2]['close'] - 1)
                    
                    predictions.append({
                        'date': date_str,
                        'predicted_regime': regime_data['final_regime'],
                        'actual_return': actual_return,
                        'correct': (
                            (regime_data['final_regime'] == 'bull' and actual_return > 0.01) or
                            (regime_data['final_regime'] == 'bear' and actual_return < -0.01) or
                            (regime_data['final_regime'] == 'neutral' and -0.01 <= actual_return <= 0.01) or
                            (regime_data['final_regime'] == 'crash' and actual_return < -0.025)
                        )
                    })
            except:
                continue
        
        if predictions:
            correct_count = sum(1 for p in predictions if p['correct'])
            accuracy = correct_count / len(predictions) * 100
            
            print(f"분석 대상: {len(predictions)}일")
            print(f"예측 정확도: {correct_count}/{len(predictions)} ({accuracy:.1f}%)")
            
            # 레짐별 정확도
            regime_accuracy = {}
            for regime in ['bull', 'neutral', 'bear', 'crash']:
                regime_preds = [p for p in predictions if p['predicted_regime'] == regime]
                if regime_preds:
                    regime_correct = sum(1 for p in regime_preds if p['correct'])
                    regime_acc = regime_correct / len(regime_preds) * 100
                    regime_accuracy[regime] = regime_acc
                    print(f"  {regime}: {regime_correct}/{len(regime_preds)} ({regime_acc:.1f}%)")
            
            return {
                'overall_accuracy': accuracy,
                'regime_accuracy': regime_accuracy,
                'sample_size': len(predictions)
            }
        
    except Exception as e:
        print(f"❌ 예측 정확도 분석 실패: {e}")
        return None

def export_regime_report():
    """종합 레짐 분석 리포트 생성"""
    print("\n📋 종합 레짐 분석 리포트 생성\n")
    
    try:
        # 상관관계 분석
        correlation_result = regime_correlation_analysis()
        
        # 예측 정확도 분석
        accuracy_result = regime_prediction_accuracy()
        
        # 리포트 생성
        report = {
            'generated_at': datetime.now().isoformat(),
            'correlation_analysis': correlation_result,
            'prediction_accuracy': accuracy_result,
            'summary': {
                'total_regimes': len(correlation_result.get('regime_stats', {})) if correlation_result else 0,
                'best_regime': None,
                'worst_regime': None
            }
        }
        
        # 최고/최악 레짐 찾기
        if correlation_result and 'regime_stats' in correlation_result:
            regime_returns = {r: s['avg_return'] for r, s in correlation_result['regime_stats'].items()}
            if regime_returns:
                report['summary']['best_regime'] = max(regime_returns, key=regime_returns.get)
                report['summary']['worst_regime'] = min(regime_returns, key=regime_returns.get)
        
        # 파일 저장
        report_file = f"regime_analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'backend', 'reports', report_file)
        
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"💾 리포트 저장: {report_path}")
        
        return report
        
    except Exception as e:
        print(f"❌ 리포트 생성 실패: {e}")
        return None

if __name__ == "__main__":
    print("🚀 Global Regime v3 고급 분석 예제\n")
    
    # 종합 분석 실행
    report = export_regime_report()
    
    if report:
        print("\n🎉 고급 분석 완료!")
        if report['summary']['best_regime']:
            print(f"최고 성과 레짐: {report['summary']['best_regime']}")
        if report['summary']['worst_regime']:
            print(f"최악 성과 레짐: {report['summary']['worst_regime']}")
    else:
        print("\n⚠️ 일부 분석 실패")
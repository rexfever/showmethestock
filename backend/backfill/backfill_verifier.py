"""
백필 품질 자동 검증기
- 레짐별 후보 수 검증
- 데이터 품질 검증
- 누락 날짜 검증
"""
import argparse
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Tuple
import pandas as pd

# Import 처리
try:
    # 패키지로 실행될 때
    from ..db_manager import db_manager
except (ImportError, ValueError):
    # 직접 실행 시 fallback
    import os
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from db_manager import db_manager

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BackfillVerifier:
    """백필 품질 검증기"""
    
    def __init__(self):
        # 검증 기준
        self.validation_criteria = {
            'neutral': {
                'position_min': 5,
                'position_max': 15,
                'swing_min': 3,
                'swing_max': 20,
                'longterm_min': 0,
                'longterm_max': 20
            },
            'bear': {
                'position_min': 0,
                'position_max': 8,
                'swing_min': 0,
                'swing_max': 5,
                'longterm_min': 0,
                'longterm_max': 15
            },
            'bull': {
                'position_min': 8,
                'position_max': 15,
                'swing_min': 10,
                'swing_max': 20,
                'longterm_min': 5,
                'longterm_max': 20
            },
            'crash': {
                'position_min': 0,
                'position_max': 0,
                'swing_min': 0,
                'swing_max': 0,
                'longterm_min': 0,
                'longterm_max': 0
            }
        }
    
    def verify_backfill(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """백필 품질 검증"""
        try:
            logger.info(f"백필 검증 시작: {start_date} ~ {end_date}")
            
            # 1. 데이터 로드
            regime_data = self._load_regime_data(start_date, end_date)
            scan_data = self._load_scan_data(start_date, end_date)
            
            # 2. 기본 통계
            basic_stats = self._calculate_basic_stats(regime_data, scan_data)
            
            # 3. 레짐별 후보 수 검증
            regime_validation = self._validate_regime_candidates(regime_data, scan_data)
            
            # 4. 누락 날짜 검증
            missing_dates = self._check_missing_dates(start_date, end_date, regime_data)
            
            # 5. 데이터 품질 검증
            quality_issues = self._check_data_quality(scan_data)
            
            # 6. 종합 평가
            overall_score = self._calculate_overall_score(
                regime_validation, missing_dates, quality_issues
            )
            
            verification_result = {
                'period': f"{start_date} ~ {end_date}",
                'basic_stats': basic_stats,
                'regime_validation': regime_validation,
                'missing_dates': missing_dates,
                'quality_issues': quality_issues,
                'overall_score': overall_score,
                'status': 'PASS' if overall_score >= 80 else 'FAIL'
            }
            
            self._print_verification_report(verification_result)
            
            return verification_result
            
        except Exception as e:
            logger.error(f"백필 검증 실패: {e}")
            raise
    
    def _load_regime_data(self, start_date: str, end_date: str) -> pd.DataFrame:
        """레짐 데이터 로드"""
        try:
            with db_manager.get_cursor(commit=False) as cur:
                cur.execute("""
                    SELECT date, final_regime, us_metrics, kr_metrics
                    FROM market_regime_daily
                    WHERE date BETWEEN %s AND %s
                    ORDER BY date
                """, (start_date, end_date))
                
                rows = cur.fetchall()
                
            if not rows:
                return pd.DataFrame()
            
            df = pd.DataFrame(rows)
            df['date'] = pd.to_datetime(df['date'])
            
            return df
        except Exception as e:
            logger.error(f"레짐 데이터 로드 실패: {e}")
            return pd.DataFrame()
    
    def _load_scan_data(self, start_date: str, end_date: str) -> pd.DataFrame:
        """스캔 데이터 로드"""
        try:
            with db_manager.get_cursor(commit=False) as cur:
                cur.execute("""
                    SELECT date, horizon, code, score, price, volume
                    FROM scan_daily
                    WHERE date BETWEEN %s AND %s
                    AND version = 'backfill-v1'
                    ORDER BY date, horizon, score DESC
                """, (start_date, end_date))
                
                rows = cur.fetchall()
                
            if not rows:
                return pd.DataFrame()
            
            df = pd.DataFrame(rows)
            df['date'] = pd.to_datetime(df['date'])
            
            return df
        except Exception as e:
            logger.error(f"스캔 데이터 로드 실패: {e}")
            return pd.DataFrame()
    
    def _calculate_basic_stats(self, regime_data: pd.DataFrame, scan_data: pd.DataFrame) -> Dict[str, Any]:
        """기본 통계 계산"""
        stats = {}
        
        if not regime_data.empty:
            # 레짐 분포
            regime_counts = regime_data['final_regime'].value_counts().to_dict()
            stats['regime_distribution'] = regime_counts
            stats['total_days'] = len(regime_data)
        else:
            stats['regime_distribution'] = {}
            stats['total_days'] = 0
        
        if not scan_data.empty:
            # 일별 후보 수 통계
            daily_counts = scan_data.groupby(['date', 'horizon']).size().unstack(fill_value=0)
            
            stats['avg_candidates'] = {
                'swing': daily_counts.get('swing', pd.Series()).mean(),
                'position': daily_counts.get('position', pd.Series()).mean(),
                'longterm': daily_counts.get('longterm', pd.Series()).mean()
            }
            
            stats['total_candidates'] = len(scan_data)
        else:
            stats['avg_candidates'] = {'swing': 0, 'position': 0, 'longterm': 0}
            stats['total_candidates'] = 0
        
        return stats
    
    def _validate_regime_candidates(self, regime_data: pd.DataFrame, scan_data: pd.DataFrame) -> Dict[str, Any]:
        """레짐별 후보 수 검증"""
        validation_results = {}
        
        if regime_data.empty or scan_data.empty:
            return {'status': 'NO_DATA', 'details': {}}
        
        # 날짜별 레짐과 후보 수 매칭
        regime_dict = regime_data.set_index('date')['final_regime'].to_dict()
        
        # 날짜별 horizon 후보 수 계산
        daily_counts = scan_data.groupby(['date', 'horizon']).size().unstack(fill_value=0)
        
        violations = []
        regime_stats = {}
        
        for date, row in daily_counts.iterrows():
            regime = regime_dict.get(date, 'neutral')
            criteria = self.validation_criteria.get(regime, self.validation_criteria['neutral'])
            
            if regime not in regime_stats:
                regime_stats[regime] = {'dates': 0, 'violations': 0}
            
            regime_stats[regime]['dates'] += 1
            
            # 각 horizon 검증
            for horizon in ['swing', 'position', 'longterm']:
                count = row.get(horizon, 0)
                min_val = criteria[f'{horizon}_min']
                max_val = criteria[f'{horizon}_max']
                
                if not (min_val <= count <= max_val):
                    violations.append({
                        'date': date.strftime('%Y-%m-%d'),
                        'regime': regime,
                        'horizon': horizon,
                        'count': count,
                        'expected_range': f"{min_val}-{max_val}"
                    })
                    regime_stats[regime]['violations'] += 1
        
        # 검증 점수 계산
        total_checks = sum(stats['dates'] for stats in regime_stats.values()) * 3  # 3 horizons
        violation_count = len(violations)
        validation_score = max(0, 100 - (violation_count / total_checks * 100)) if total_checks > 0 else 0
        
        validation_results = {
            'status': 'PASS' if validation_score >= 80 else 'FAIL',
            'score': validation_score,
            'total_checks': total_checks,
            'violations': violation_count,
            'regime_stats': regime_stats,
            'violation_details': violations[:10]  # 최대 10개만 표시
        }
        
        return validation_results
    
    def _check_missing_dates(self, start_date: str, end_date: str, regime_data: pd.DataFrame) -> List[str]:
        """누락 날짜 검증"""
        if regime_data.empty:
            return []
        
        # 예상 거래일 생성 (주말 제외)
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        expected_dates = []
        current_dt = start_dt
        
        while current_dt <= end_dt:
            if current_dt.weekday() < 5:  # 월-금만
                expected_dates.append(current_dt.date())
            current_dt += timedelta(days=1)
        
        # 실제 데이터 날짜
        actual_dates = set(regime_data['date'].dt.date)
        
        # 누락 날짜 찾기
        missing_dates = [date.strftime('%Y-%m-%d') for date in expected_dates if date not in actual_dates]
        
        return missing_dates
    
    def _check_data_quality(self, scan_data: pd.DataFrame) -> List[Dict[str, Any]]:
        """데이터 품질 검증"""
        issues = []
        
        if scan_data.empty:
            issues.append({
                'type': 'NO_SCAN_DATA',
                'description': '스캔 데이터가 없습니다',
                'severity': 'HIGH'
            })
            return issues
        
        # 1. 점수 범위 검증
        invalid_scores = scan_data[(scan_data['score'] < 0) | (scan_data['score'] > 15)]
        if not invalid_scores.empty:
            issues.append({
                'type': 'INVALID_SCORE_RANGE',
                'description': f'점수 범위 오류: {len(invalid_scores)}개 레코드',
                'severity': 'MEDIUM'
            })
        
        # 2. 가격 검증
        invalid_prices = scan_data[(scan_data['price'] <= 0) | (scan_data['price'] > 1000000)]
        if not invalid_prices.empty:
            issues.append({
                'type': 'INVALID_PRICE_RANGE',
                'description': f'가격 범위 오류: {len(invalid_prices)}개 레코드',
                'severity': 'HIGH'
            })
        
        # 3. 거래량 검증
        invalid_volumes = scan_data[scan_data['volume'] <= 0]
        if not invalid_volumes.empty:
            issues.append({
                'type': 'INVALID_VOLUME',
                'description': f'거래량 오류: {len(invalid_volumes)}개 레코드',
                'severity': 'MEDIUM'
            })
        
        # 4. 중복 데이터 검증
        duplicates = scan_data.duplicated(subset=['date', 'horizon', 'code'])
        if duplicates.any():
            issues.append({
                'type': 'DUPLICATE_RECORDS',
                'description': f'중복 레코드: {duplicates.sum()}개',
                'severity': 'HIGH'
            })
        
        return issues
    
    def _calculate_overall_score(self, regime_validation: Dict[str, Any], 
                                missing_dates: List[str], quality_issues: List[Dict[str, Any]]) -> float:
        """종합 점수 계산"""
        score = 100.0
        
        # 레짐 검증 점수 (50% 가중치)
        regime_score = regime_validation.get('score', 0)
        score = score * 0.5 + regime_score * 0.5
        
        # 누락 날짜 페널티 (20% 가중치)
        if missing_dates:
            missing_penalty = min(len(missing_dates) * 5, 50)  # 최대 50점 감점
            score -= missing_penalty * 0.2
        
        # 품질 이슈 페널티 (30% 가중치)
        quality_penalty = 0
        for issue in quality_issues:
            if issue['severity'] == 'HIGH':
                quality_penalty += 20
            elif issue['severity'] == 'MEDIUM':
                quality_penalty += 10
            else:
                quality_penalty += 5
        
        score -= min(quality_penalty, 100) * 0.3
        
        return max(0, score)
    
    def _print_verification_report(self, result: Dict[str, Any]) -> None:
        """검증 리포트 출력"""
        print("\n" + "="*60)
        print("📊 백필 품질 검증 리포트")
        print("="*60)
        
        print(f"📅 검증 기간: {result['period']}")
        print(f"🎯 종합 점수: {result['overall_score']:.1f}/100")
        print(f"✅ 검증 상태: {result['status']}")
        
        # 기본 통계
        stats = result['basic_stats']
        print(f"\n📈 기본 통계:")
        print(f"  - 총 거래일: {stats['total_days']}일")
        print(f"  - 총 후보 수: {stats['total_candidates']}개")
        print(f"  - 레짐 분포: {stats['regime_distribution']}")
        
        # 평균 후보 수
        avg_candidates = stats['avg_candidates']
        print(f"  - 평균 후보 수:")
        print(f"    * swing: {avg_candidates['swing']:.1f}개")
        print(f"    * position: {avg_candidates['position']:.1f}개")
        print(f"    * longterm: {avg_candidates['longterm']:.1f}개")
        
        # 레짐 검증
        regime_val = result['regime_validation']
        print(f"\n🎯 레짐별 후보 수 검증:")
        print(f"  - 검증 점수: {regime_val.get('score', 0):.1f}/100")
        print(f"  - 총 검증: {regime_val.get('total_checks', 0)}회")
        print(f"  - 위반 사항: {regime_val.get('violations', 0)}개")
        
        # 누락 날짜
        missing = result['missing_dates']
        if missing:
            print(f"\n⚠️ 누락 날짜: {len(missing)}개")
            if len(missing) <= 10:
                print(f"  - {', '.join(missing)}")
            else:
                print(f"  - {', '.join(missing[:10])} ... (총 {len(missing)}개)")
        else:
            print(f"\n✅ 누락 날짜: 없음")
        
        # 품질 이슈
        quality = result['quality_issues']
        if quality:
            print(f"\n🔍 품질 이슈: {len(quality)}개")
            for issue in quality:
                print(f"  - [{issue['severity']}] {issue['type']}: {issue['description']}")
        else:
            print(f"\n✅ 품질 이슈: 없음")
        
        print("\n" + "="*60)

def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='백필 품질 검증기')
    parser.add_argument('--start', required=True, help='시작 날짜 (YYYY-MM-DD)')
    parser.add_argument('--end', required=True, help='종료 날짜 (YYYY-MM-DD)')
    
    args = parser.parse_args()
    
    try:
        verifier = BackfillVerifier()
        result = verifier.verify_backfill(args.start, args.end)
        
        # 종료 코드 설정
        exit_code = 0 if result['status'] == 'PASS' else 1
        sys.exit(exit_code)
        
    except Exception as e:
        logger.error(f"검증 실행 중 오류: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
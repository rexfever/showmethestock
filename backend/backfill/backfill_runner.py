"""
백필 실행기
- 전체 날짜를 병렬로 처리
- multiprocessing Pool 사용
- DB 저장 (market_regime_daily + scan_daily)
"""
import argparse
import json
import logging
import multiprocessing as mp
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd
import pytz

# Import 처리
try:
    # 패키지로 실행될 때
    from .backfill_market_analyzer_light import backfill_analyzer
    from .backfill_fast_scanner import backfill_scanner
    from ..db_manager import db_manager
except (ImportError, ValueError):
    # 직접 실행 시 fallback
    import os
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from backfill_market_analyzer_light import backfill_analyzer
    from backfill_fast_scanner import backfill_scanner
    from db_manager import db_manager

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 서울 타임존
SEOUL_TZ = pytz.timezone('Asia/Seoul')

class BackfillRunner:
    """백필 실행기"""
    
    def __init__(self):
        self._ensure_scan_daily_table()
    
    def _ensure_scan_daily_table(self) -> None:
        """scan_daily 테이블 생성"""
        try:
            with db_manager.get_cursor(commit=True) as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS scan_daily (
                        date DATE NOT NULL,
                        horizon VARCHAR(20) NOT NULL,
                        code VARCHAR(20) NOT NULL,
                        score DOUBLE PRECISION,
                        price DOUBLE PRECISION,
                        volume BIGINT,
                        version VARCHAR(20) NOT NULL DEFAULT 'backfill-v1',
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (date, horizon, code, version)
                    )
                """)
                
                # 인덱스 생성
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_scan_daily_date_version 
                    ON scan_daily(date, version)
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_scan_daily_horizon 
                    ON scan_daily(horizon)
                """)
                
            logger.info("scan_daily 테이블 준비 완료")
        except Exception as e:
            logger.error(f"scan_daily 테이블 생성 실패: {e}")
            raise
    
    def generate_trading_dates(self, start_date: str, end_date: str) -> List[str]:
        """거래일 생성 (주말 제외)"""
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        dates = []
        current_dt = start_dt
        
        while current_dt <= end_dt:
            # 주말 제외 (월-금만)
            if current_dt.weekday() < 5:
                dates.append(current_dt.strftime('%Y%m%d'))
            current_dt += timedelta(days=1)
        
        return dates
    
    def process_single_date(self, date: str) -> Dict[str, Any]:
        """단일 날짜 처리"""
        try:
            logger.info(f"처리 시작: {date}")
            
            # 1. 레짐 분석
            regime_result = backfill_analyzer.analyze_regime_light(date)
            
            # 2. 스캔 실행
            scan_result = backfill_scanner.scan_fast(date, regime_result['final_regime'])
            
            # 3. DB 저장
            self._save_regime_data(date, regime_result)
            self._save_scan_data(date, scan_result)
            
            # 결과 요약
            total_candidates = sum(len(candidates) for candidates in scan_result.values())
            
            return {
                'date': date,
                'status': 'success',
                'regime': regime_result['final_regime'],
                'total_candidates': total_candidates,
                'swing': len(scan_result['swing']),
                'position': len(scan_result['position']),
                'longterm': len(scan_result['longterm'])
            }
            
        except Exception as e:
            logger.error(f"날짜 {date} 처리 실패: {e}")
            return {
                'date': date,
                'status': 'failed',
                'error': str(e)
            }
    
    def _save_regime_data(self, date: str, regime_data: Dict[str, Any]) -> None:
        """레짐 데이터 저장"""
        try:
            # 날짜 형식 변환 (YYYYMMDD -> YYYY-MM-DD)
            formatted_date = f"{date[:4]}-{date[4:6]}-{date[6:8]}"
            
            with db_manager.get_cursor(commit=True) as cur:
                cur.execute("""
                    INSERT INTO market_regime_daily (
                        date, us_prev_sentiment, kr_sentiment, us_preopen_sentiment,
                        final_regime, us_metrics, kr_metrics, us_preopen_metrics, version
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (date) DO UPDATE SET
                        us_prev_sentiment = EXCLUDED.us_prev_sentiment,
                        kr_sentiment = EXCLUDED.kr_sentiment,
                        us_preopen_sentiment = EXCLUDED.us_preopen_sentiment,
                        final_regime = EXCLUDED.final_regime,
                        us_metrics = EXCLUDED.us_metrics,
                        kr_metrics = EXCLUDED.kr_metrics,
                        us_preopen_metrics = EXCLUDED.us_preopen_metrics,
                        run_timestamp = CURRENT_TIMESTAMP
                """, (
                    formatted_date,
                    'neutral',  # us_prev_sentiment
                    'neutral',  # kr_sentiment
                    'none',     # us_preopen_sentiment
                    regime_data['final_regime'],
                    json.dumps({'final_score': regime_data['final_score']}),
                    json.dumps({'kr_score': regime_data['kr_score']}),
                    json.dumps({'us_preopen_score': regime_data['us_preopen_score']}),
                    regime_data['version']
                ))
        except Exception as e:
            logger.error(f"레짐 데이터 저장 실패 ({date}): {e}")
    
    def _save_scan_data(self, date: str, scan_data: Dict[str, List[Dict[str, Any]]]) -> None:
        """스캔 데이터 저장"""
        try:
            # 날짜 형식 변환 (YYYYMMDD -> YYYY-MM-DD)
            formatted_date = f"{date[:4]}-{date[4:6]}-{date[6:8]}"
            
            with db_manager.get_cursor(commit=True) as cur:
                # 기존 데이터 삭제
                cur.execute("""
                    DELETE FROM scan_daily 
                    WHERE date = %s AND version = 'backfill-v1'
                """, (formatted_date,))
                
                # 새 데이터 삽입
                for horizon, candidates in scan_data.items():
                    if not candidates:
                        continue
                    
                    for candidate in candidates:
                        cur.execute("""
                            INSERT INTO scan_daily (
                                date, horizon, code, score, price, volume, version
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """, (
                            formatted_date,
                            horizon,
                            candidate['code'],
                            candidate['score'],
                            candidate['price'],
                            candidate['volume'],
                            'backfill-v1'
                        ))
        except Exception as e:
            logger.error(f"스캔 데이터 저장 실패 ({date}): {e}")
    
    def run_backfill(self, start_date: str, end_date: str, workers: int = 4) -> None:
        """백필 실행"""
        try:
            # 거래일 생성
            trading_dates = self.generate_trading_dates(start_date, end_date)
            logger.info(f"백필 시작: {len(trading_dates)}개 거래일 ({start_date} ~ {end_date})")
            
            # 병렬 처리
            if workers > 1:
                with mp.Pool(workers) as pool:
                    results = pool.map(self.process_single_date, trading_dates)
            else:
                results = [self.process_single_date(date) for date in trading_dates]
            
            # 결과 집계
            success_count = sum(1 for r in results if r['status'] == 'success')
            failed_count = len(results) - success_count
            
            logger.info(f"백필 완료: 성공 {success_count}개, 실패 {failed_count}개")
            
            # 실패한 날짜 출력
            failed_dates = [r['date'] for r in results if r['status'] == 'failed']
            if failed_dates:
                logger.warning(f"실패한 날짜: {failed_dates}")
            
            # 성공한 결과 요약
            successful_results = [r for r in results if r['status'] == 'success']
            if successful_results:
                regime_counts = {}
                for r in successful_results:
                    regime = r['regime']
                    regime_counts[regime] = regime_counts.get(regime, 0) + 1
                
                logger.info(f"레짐 분포: {regime_counts}")
                
                avg_candidates = sum(r['total_candidates'] for r in successful_results) / len(successful_results)
                logger.info(f"평균 후보 수: {avg_candidates:.1f}개")
            
        except Exception as e:
            logger.error(f"백필 실행 실패: {e}")
            raise

def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='백필 실행기')
    parser.add_argument('--start', required=True, help='시작 날짜 (YYYY-MM-DD)')
    parser.add_argument('--end', required=True, help='종료 날짜 (YYYY-MM-DD)')
    parser.add_argument('--workers', type=int, default=4, help='워커 수 (기본값: 4)')
    
    args = parser.parse_args()
    
    try:
        runner = BackfillRunner()
        runner.run_backfill(args.start, args.end, args.workers)
    except Exception as e:
        logger.error(f"백필 실행 중 오류: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
#!/usr/bin/env python3
"""
누락된 일별 등락률 채우기
- market_regime_daily에는 있지만 market_conditions에 없는 날짜의 일별 등락률 저장
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db_manager import db_manager
from main import create_market_conditions_table
from market_analyzer import market_analyzer
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fill_missing_daily_returns(start_date: str = '2025-11-01', end_date: str = '2025-11-30'):
    """누락된 일별 등락률 채우기"""
    try:
        with db_manager.get_cursor() as cur:
            # 누락된 날짜 찾기
            cur.execute("""
                SELECT r.date, r.final_regime
                FROM market_regime_daily r
                LEFT JOIN market_conditions c ON r.date = c.date
                WHERE r.date >= %s AND r.date <= %s
                AND c.date IS NULL
                ORDER BY r.date
            """, (start_date, end_date))
            
            missing_rows = cur.fetchall()
            
            if not missing_rows:
                logger.info("누락된 일별 등락률이 없습니다")
                return 0
            
            logger.info(f"누락된 날짜: {len(missing_rows)}개")
            
            success_count = 0
            for row in missing_rows:
                date = row[0]
                final_regime = row[1]
                
                # 날짜 형식 변환 (YYYY-MM-DD -> YYYYMMDD)
                if isinstance(date, str):
                    date_str = date.replace('-', '')
                else:
                    date_str = date.strftime('%Y%m%d')
                
                try:
                    # market_condition 생성
                    market_condition = market_analyzer.analyze_market_condition_v4(date_str)
                    
                    # market_conditions 테이블에 저장
                    with db_manager.get_cursor(commit=True) as cur_save:
                        create_market_conditions_table(cur_save)
                        cur_save.execute("""
                            INSERT INTO market_conditions(
                                date, market_sentiment, sentiment_score, kospi_return, volatility, rsi_threshold,
                                sector_rotation, foreign_flow, institution_flow, volume_trend,
                                min_signals, macd_osc_min, vol_ma5_mult, gap_max, ext_from_tema20_max,
                                trend_metrics, breadth_metrics, flow_metrics, sector_metrics, volatility_metrics,
                                foreign_flow_label, institution_flow_label, volume_trend_label, adjusted_params, analysis_notes
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (date) DO UPDATE SET
                                market_sentiment = EXCLUDED.market_sentiment,
                                sentiment_score = EXCLUDED.sentiment_score,
                                kospi_return = EXCLUDED.kospi_return,
                                volatility = EXCLUDED.volatility,
                                rsi_threshold = EXCLUDED.rsi_threshold,
                                sector_rotation = EXCLUDED.sector_rotation,
                                foreign_flow = EXCLUDED.foreign_flow,
                                institution_flow = EXCLUDED.institution_flow,
                                volume_trend = EXCLUDED.volume_trend,
                                min_signals = EXCLUDED.min_signals,
                                macd_osc_min = EXCLUDED.macd_osc_min,
                                vol_ma5_mult = EXCLUDED.vol_ma5_mult,
                                gap_max = EXCLUDED.gap_max,
                                ext_from_tema20_max = EXCLUDED.ext_from_tema20_max,
                                trend_metrics = EXCLUDED.trend_metrics,
                                breadth_metrics = EXCLUDED.breadth_metrics,
                                flow_metrics = EXCLUDED.flow_metrics,
                                sector_metrics = EXCLUDED.sector_metrics,
                                volatility_metrics = EXCLUDED.volatility_metrics,
                                foreign_flow_label = EXCLUDED.foreign_flow_label,
                                institution_flow_label = EXCLUDED.institution_flow_label,
                                volume_trend_label = EXCLUDED.volume_trend_label,
                                adjusted_params = EXCLUDED.adjusted_params,
                                analysis_notes = EXCLUDED.analysis_notes,
                                updated_at = NOW()
                        """, (
                            date if isinstance(date, str) else date.strftime('%Y-%m-%d'),
                            market_condition.market_sentiment,
                            market_condition.sentiment_score,
                            market_condition.kospi_return,
                            market_condition.volatility,
                            market_condition.rsi_threshold,
                            market_condition.sector_rotation,
                            market_condition.foreign_flow,
                            market_condition.institution_flow,
                            market_condition.volume_trend,
                            market_condition.min_signals,
                            market_condition.macd_osc_min,
                            market_condition.vol_ma5_mult,
                            market_condition.gap_max,
                            market_condition.ext_from_tema20_max,
                            json.dumps(market_condition.trend_metrics) if market_condition.trend_metrics else None,
                            json.dumps(market_condition.breadth_metrics) if market_condition.breadth_metrics else None,
                            json.dumps(market_condition.flow_metrics) if market_condition.flow_metrics else None,
                            json.dumps(market_condition.sector_metrics) if market_condition.sector_metrics else None,
                            json.dumps(market_condition.volatility_metrics) if market_condition.volatility_metrics else None,
                            market_condition.foreign_flow_label,
                            market_condition.institution_flow_label,
                            market_condition.volume_trend_label,
                            json.dumps(market_condition.adjusted_params) if market_condition.adjusted_params else None,
                            market_condition.analysis_notes
                        ))
                    
                    logger.info(f"✅ {date_str}: kospi_return {market_condition.kospi_return*100:+.2f}% 저장 완료")
                    success_count += 1
                    
                except Exception as e:
                    logger.error(f"❌ {date_str}: 저장 실패 - {e}")
                    continue
            
            logger.info(f"\n총 {success_count}/{len(missing_rows)}개 저장 완료")
            return success_count
            
    except Exception as e:
        logger.error(f"누락된 일별 등락률 채우기 실패: {e}", exc_info=True)
        return 0

if __name__ == "__main__":
    fill_missing_daily_returns()


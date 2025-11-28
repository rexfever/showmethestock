#!/usr/bin/env python3
"""
과거 레짐 정보를 v4로 재분석하고 업데이트하는 스크립트
캐시를 활용하여 효율적으로 처리
"""
import sys
import json
from datetime import datetime
from db_manager import db_manager
from market_analyzer import market_analyzer
from date_helper import yyyymmdd_to_date

def save_market_condition_to_db(market_condition, date_str):
    """market_condition을 market_conditions 테이블에 저장"""
    try:
        # date를 YYYY-MM-DD 형식으로 변환 (market_conditions.date는 TEXT 타입)
        if len(date_str) == 8 and '-' not in date_str:
            db_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        elif '-' in date_str:
            db_date = date_str
        else:
            db_date = date_str
        
        with db_manager.get_cursor(commit=True) as cur:
            # market_conditions 테이블 생성 확인
            from main import create_market_conditions_table
            create_market_conditions_table(cur)
            
            # JSON 필드 변환
            def to_json_str(value):
                if value is None:
                    return None
                if isinstance(value, dict) or isinstance(value, list):
                    return json.dumps(value, ensure_ascii=False)
                return value
            
            # 실제 테이블에 있는 컬럼만 사용 (institution_flow는 없을 수 있음)
            # 먼저 테이블 스키마 확인
            cur.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'market_conditions'
                ORDER BY ordinal_position
            """)
            existing_columns = {row[0] for row in cur.fetchall()}
            
            # institution_flow가 없으면 제외
            has_institution_flow = 'institution_flow' in existing_columns
            has_institution_flow_label = 'institution_flow_label' in existing_columns
            
            if has_institution_flow and has_institution_flow_label:
                # 전체 컬럼 사용
                cur.execute("""
                    INSERT INTO market_conditions(
                        date, market_sentiment, sentiment_score, kospi_return, volatility, rsi_threshold,
                        sector_rotation, foreign_flow, institution_flow, volume_trend,
                        min_signals, macd_osc_min, vol_ma5_mult, gap_max, ext_from_tema20_max,
                        trend_metrics, breadth_metrics, flow_metrics, sector_metrics, volatility_metrics,
                        foreign_flow_label, institution_flow_label, volume_trend_label, adjusted_params, analysis_notes
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s
                    )
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
                        analysis_notes = EXCLUDED.analysis_notes
                """, (
                    db_date,
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
                    to_json_str(market_condition.trend_metrics),
                    to_json_str(market_condition.breadth_metrics),
                    to_json_str(market_condition.flow_metrics),
                    to_json_str(market_condition.sector_metrics),
                    to_json_str(market_condition.volatility_metrics),
                    market_condition.foreign_flow_label,
                    market_condition.institution_flow_label,
                    market_condition.volume_trend_label,
                    to_json_str(market_condition.adjusted_params),
                    market_condition.analysis_notes
                ))
            else:
                # institution_flow 제외
                cur.execute("""
                    INSERT INTO market_conditions(
                        date, market_sentiment, sentiment_score, kospi_return, volatility, rsi_threshold,
                        sector_rotation, foreign_flow, volume_trend,
                        min_signals, macd_osc_min, vol_ma5_mult, gap_max, ext_from_tema20_max,
                        trend_metrics, breadth_metrics, flow_metrics, sector_metrics, volatility_metrics,
                        foreign_flow_label, volume_trend_label, adjusted_params, analysis_notes
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s
                    )
                    ON CONFLICT (date) DO UPDATE SET
                        market_sentiment = EXCLUDED.market_sentiment,
                        sentiment_score = EXCLUDED.sentiment_score,
                        kospi_return = EXCLUDED.kospi_return,
                        volatility = EXCLUDED.volatility,
                        rsi_threshold = EXCLUDED.rsi_threshold,
                        sector_rotation = EXCLUDED.sector_rotation,
                        foreign_flow = EXCLUDED.foreign_flow,
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
                        volume_trend_label = EXCLUDED.volume_trend_label,
                        adjusted_params = EXCLUDED.adjusted_params,
                        analysis_notes = EXCLUDED.analysis_notes
                """, (
                    db_date,
                    market_condition.market_sentiment,
                    market_condition.sentiment_score,
                    market_condition.kospi_return,
                    market_condition.volatility,
                    market_condition.rsi_threshold,
                    market_condition.sector_rotation,
                    market_condition.foreign_flow,
                    market_condition.volume_trend,
                    market_condition.min_signals,
                    market_condition.macd_osc_min,
                    market_condition.vol_ma5_mult,
                    market_condition.gap_max,
                    market_condition.ext_from_tema20_max,
                    to_json_str(market_condition.trend_metrics),
                    to_json_str(market_condition.breadth_metrics),
                    to_json_str(market_condition.flow_metrics),
                    to_json_str(market_condition.sector_metrics),
                    to_json_str(market_condition.volatility_metrics),
                    market_condition.foreign_flow_label,
                    market_condition.volume_trend_label,
                    to_json_str(market_condition.adjusted_params),
                    market_condition.analysis_notes
                ))
        
        return True
    except Exception as e:
        print(f"  ❌ DB 저장 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def update_regime_v4_for_dates(dates, use_cache=True, batch_size=10):
    """과거 날짜들의 레짐 정보를 v4로 업데이트"""
    total = len(dates)
    success_count = 0
    error_count = 0
    skipped_count = 0
    
    print(f"📊 총 {total}개 날짜의 레짐 정보를 v4로 업데이트 시작...")
    print(f"캐시 사용: {'예' if use_cache else '아니오'}")
    print(f"배치 크기: {batch_size}\n")
    
    if not use_cache:
        market_analyzer.clear_cache()
    
    for idx, date_row in enumerate(dates, 1):
        date_val = date_row[0]
        
        # DATE 타입을 YYYYMMDD 문자열로 변환
        if hasattr(date_val, 'strftime'):
            date_str = date_val.strftime('%Y%m%d')
        else:
            # 이미 문자열인 경우
            date_str = str(date_val).replace('-', '')
            if len(date_str) == 10:  # YYYY-MM-DD 형식
                date_str = date_str.replace('-', '')
        
        try:
            print(f"[{idx}/{total}] {date_str} 분석 중...", end=' ', flush=True)
            
            # v4 레짐 분석 (캐시 활용)
            try:
                market_condition = market_analyzer.analyze_market_condition(
                    date_str,
                    regime_version='v4'
                )
            except Exception as analyze_error:
                print(f"❌ 분석 실패: {analyze_error}")
                error_count += 1
                continue
            
            # 버전 확인
            if hasattr(market_condition, 'version'):
                version = market_condition.version
                if version == 'regime_v4':
                    regime_info = f"{market_condition.final_regime} (trend: {market_condition.global_trend_score:.2f}, risk: {market_condition.global_risk_score:.2f})"
                elif version == 'regime_v3':
                    regime_info = f"{market_condition.final_regime} (점수: {market_condition.final_score:.2f})"
                else:
                    regime_info = f"{market_condition.market_sentiment}"
            else:
                regime_info = f"{market_condition.market_sentiment}"
            
            # DB 저장
            try:
                if save_market_condition_to_db(market_condition, date_str):
                    print(f"✅ {regime_info}")
                    success_count += 1
                else:
                    print(f"❌ 저장 실패")
                    error_count += 1
            except Exception as save_error:
                print(f"❌ 저장 오류: {save_error}")
                error_count += 1
                
            # 배치마다 진행 상황 출력
            if idx % batch_size == 0:
                print(f"\n  진행 상황: {idx}/{total} (성공: {success_count}, 실패: {error_count}, 건너뜀: {skipped_count})\n")
                
        except KeyboardInterrupt:
            print(f"\n\n⚠️ 사용자에 의해 중단됨")
            print(f"진행 상황: {idx-1}/{total} (성공: {success_count}, 실패: {error_count})")
            break
        except Exception as e:
            print(f"❌ 예상치 못한 오류: {e}")
            error_count += 1
            # 치명적 오류가 아니면 계속 진행
            import traceback
            traceback.print_exc()
    
    print(f"\n📊 완료: 성공 {success_count}개, 실패 {error_count}개, 건너뜀 {skipped_count}개")

def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='과거 레짐 정보를 v4로 업데이트')
    parser.add_argument('--limit', type=int, default=None, help='처리할 날짜 수 제한')
    parser.add_argument('--no-cache', action='store_true', help='캐시 사용 안 함')
    parser.add_argument('--from-date', type=str, help='시작 날짜 (YYYYMMDD)')
    parser.add_argument('--to-date', type=str, help='종료 날짜 (YYYYMMDD)')
    parser.add_argument('--batch-size', type=int, default=10, help='배치 크기 (진행 상황 출력 주기)')
    
    args = parser.parse_args()
    
    # 스캔된 날짜 목록 가져오기
    with db_manager.get_cursor(commit=False) as cur:
        query = """
            SELECT DISTINCT date
            FROM scan_rank
            WHERE scanner_version = 'v2'
        """
        conditions = []
        params = []
        
        if args.from_date:
            conditions.append("date >= %s")
            params.append(args.from_date.replace('-', ''))
        if args.to_date:
            conditions.append("date <= %s")
            params.append(args.to_date.replace('-', ''))
        
        if conditions:
            query += " AND " + " AND ".join(conditions)
        
        query += " ORDER BY date DESC"
        
        if args.limit:
            query += f" LIMIT {args.limit}"
        
        cur.execute(query, params)
        dates = cur.fetchall()
    
    if not dates:
        print("❌ 처리할 날짜가 없습니다.")
        return
    
    print(f"📅 총 {len(dates)}개 날짜를 처리합니다.\n")
    
    # 업데이트 실행
    update_regime_v4_for_dates(dates, use_cache=not args.no_cache, batch_size=args.batch_size)

if __name__ == '__main__':
    main()


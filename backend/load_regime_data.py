#!/usr/bin/env python3
"""
레짐 데이터 로드 스크립트
덤프된 JSON 파일을 서버 DB에 업로드합니다.
"""
import sys
import json
import os
from pathlib import Path
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

from db_manager import db_manager

def load_market_conditions(input_file: str, dry_run: bool = False):
    """market_conditions 테이블 데이터 로드"""
    print(f"📊 market_conditions 데이터 로드 중...")
    
    if not os.path.exists(input_file):
        print(f"❌ 파일이 없습니다: {input_file}")
        return 0
    
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if not data:
        print("⚠️ 로드할 데이터가 없습니다.")
        return 0
    
    print(f"   로드할 레코드 수: {len(data)}개")
    
    if dry_run:
        print("   [DRY RUN] 실제로 저장하지 않습니다.")
        return len(data)
    
    success_count = 0
    error_count = 0
    
    with db_manager.get_cursor(commit=True) as cur:
        for i, record in enumerate(data, 1):
            try:
                # JSON 필드 변환
                def to_json_str(value):
                    if value is None:
                        return None
                    if isinstance(value, dict) or isinstance(value, list):
                        return json.dumps(value, ensure_ascii=False)
                    return value
                
                # UPSERT 쿼리
                cur.execute("""
                    INSERT INTO market_conditions (
                        date, market_sentiment, sentiment_score, kospi_return, volatility, rsi_threshold,
                        sector_rotation, foreign_flow, volume_trend,
                        min_signals, macd_osc_min, vol_ma5_mult, gap_max, ext_from_tema20_max,
                        trend_metrics, breadth_metrics, flow_metrics, sector_metrics, volatility_metrics,
                        foreign_flow_label, volume_trend_label, adjusted_params, analysis_notes
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s
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
                        analysis_notes = EXCLUDED.analysis_notes,
                        updated_at = CURRENT_TIMESTAMP
                """, (
                    record.get('date'),
                    record.get('market_sentiment'),
                    record.get('sentiment_score'),
                    record.get('kospi_return'),
                    record.get('volatility'),
                    record.get('rsi_threshold'),
                    record.get('sector_rotation'),
                    record.get('foreign_flow'),
                    record.get('volume_trend'),
                    record.get('min_signals'),
                    record.get('macd_osc_min'),
                    record.get('vol_ma5_mult'),
                    record.get('gap_max'),
                    record.get('ext_from_tema20_max'),
                    to_json_str(record.get('trend_metrics')),
                    to_json_str(record.get('breadth_metrics')),
                    to_json_str(record.get('flow_metrics')),
                    to_json_str(record.get('sector_metrics')),
                    to_json_str(record.get('volatility_metrics')),
                    record.get('foreign_flow_label'),
                    record.get('volume_trend_label'),
                    to_json_str(record.get('adjusted_params')),
                    record.get('analysis_notes')
                ))
                success_count += 1
                
                if i % 50 == 0:
                    print(f"   진행: {i}/{len(data)} ({success_count}개 성공)")
            except Exception as e:
                error_count += 1
                print(f"   ❌ 오류 ({record.get('date')}): {e}")
    
    print(f"✅ market_conditions 로드 완료: {success_count}개 성공, {error_count}개 실패")
    return success_count

def load_market_regime_daily(input_file: str, dry_run: bool = False):
    """market_regime_daily 테이블 데이터 로드"""
    print(f"📊 market_regime_daily 데이터 로드 중...")
    
    if not os.path.exists(input_file):
        print(f"⚠️ 파일이 없습니다: {input_file} (건너뜁니다)")
        return 0
    
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if not data:
        print("⚠️ 로드할 데이터가 없습니다.")
        return 0
    
    print(f"   로드할 레코드 수: {len(data)}개")
    
    if dry_run:
        print("   [DRY RUN] 실제로 저장하지 않습니다.")
        return len(data)
    
    # 테이블 존재 확인
    with db_manager.get_cursor(commit=False) as cur:
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'market_regime_daily'
            )
        """)
        exists = cur.fetchone()[0]
        
        if not exists:
            print("⚠️ market_regime_daily 테이블이 없습니다. 건너뜁니다.")
            return 0
    
    success_count = 0
    error_count = 0
    
    with db_manager.get_cursor(commit=True) as cur:
        for i, record in enumerate(data, 1):
            try:
                # JSON 필드 변환
                def to_json_str(value):
                    if value is None:
                        return None
                    if isinstance(value, dict) or isinstance(value, list):
                        return json.dumps(value, ensure_ascii=False)
                    return value
                
                # v4 필드 확인
                has_v4_fields = 'us_futures_score' in record
                
                if has_v4_fields:
                    # v4 필드 포함 UPSERT
                    cur.execute("""
                        INSERT INTO market_regime_daily (
                            date, us_prev_sentiment, kr_sentiment, us_preopen_sentiment,
                            final_regime, us_metrics, kr_metrics, us_preopen_metrics,
                            version, us_futures_score, us_futures_regime, dxy
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (date) DO UPDATE SET
                            us_prev_sentiment = EXCLUDED.us_prev_sentiment,
                            kr_sentiment = EXCLUDED.kr_sentiment,
                            us_preopen_sentiment = EXCLUDED.us_preopen_sentiment,
                            final_regime = EXCLUDED.final_regime,
                            us_metrics = EXCLUDED.us_metrics,
                            kr_metrics = EXCLUDED.kr_metrics,
                            us_preopen_metrics = EXCLUDED.us_preopen_metrics,
                            version = EXCLUDED.version,
                            us_futures_score = EXCLUDED.us_futures_score,
                            us_futures_regime = EXCLUDED.us_futures_regime,
                            dxy = EXCLUDED.dxy,
                            updated_at = CURRENT_TIMESTAMP
                    """, (
                        record.get('date'),
                        record.get('us_prev_sentiment', 'neutral'),
                        record.get('kr_sentiment', 'neutral'),
                        record.get('us_preopen_sentiment', 'none'),
                        record.get('final_regime', 'neutral'),
                        to_json_str(record.get('us_metrics')),
                        to_json_str(record.get('kr_metrics')),
                        to_json_str(record.get('us_preopen_metrics')),
                        record.get('version', 'regime_v3'),
                        record.get('us_futures_score', 0.0),
                        record.get('us_futures_regime', 'neutral'),
                        record.get('dxy', 0.0)
                    ))
                else:
                    # v3 필드만 UPSERT
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
                            version = EXCLUDED.version,
                            run_timestamp = CURRENT_TIMESTAMP
                    """, (
                        record.get('date'),
                        record.get('us_prev_sentiment', 'neutral'),
                        record.get('kr_sentiment', 'neutral'),
                        record.get('us_preopen_sentiment', 'none'),
                        record.get('final_regime', 'neutral'),
                        to_json_str(record.get('us_metrics')),
                        to_json_str(record.get('kr_metrics')),
                        to_json_str(record.get('us_preopen_metrics')),
                        record.get('version', 'regime_v3')
                    ))
                
                success_count += 1
                
                if i % 50 == 0:
                    print(f"   진행: {i}/{len(data)} ({success_count}개 성공)")
            except Exception as e:
                error_count += 1
                print(f"   ❌ 오류 ({record.get('date')}): {e}")
    
    print(f"✅ market_regime_daily 로드 완료: {success_count}개 성공, {error_count}개 실패")
    return success_count

def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='레짐 데이터 로드 스크립트')
    parser.add_argument('--market-conditions', type=str, help='market_conditions JSON 파일 경로')
    parser.add_argument('--market-regime-daily', type=str, help='market_regime_daily JSON 파일 경로')
    parser.add_argument('--metadata', type=str, help='메타데이터 JSON 파일 경로 (선택적)')
    parser.add_argument('--dry-run', action='store_true', help='실제로 저장하지 않고 테스트만 수행')
    
    args = parser.parse_args()
    
    # 메타데이터 파일이 있으면 사용
    if args.metadata and os.path.exists(args.metadata):
        with open(args.metadata, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        if not args.market_conditions:
            args.market_conditions = metadata.get('market_conditions', {}).get('file')
        if not args.market_regime_daily:
            args.market_regime_daily = metadata.get('market_regime_daily', {}).get('file')
    
    if not args.market_conditions and not args.market_regime_daily:
        print("❌ 로드할 파일을 지정해주세요.")
        print("   --market-conditions <파일> 또는 --market-regime-daily <파일>")
        print("   또는 --metadata <메타데이터 파일>")
        sys.exit(1)
    
    print(f"🚀 레짐 데이터 로드 시작...")
    if args.dry_run:
        print("⚠️ DRY RUN 모드: 실제로 저장하지 않습니다.")
    print()
    
    total_success = 0
    
    if args.market_conditions:
        count = load_market_conditions(args.market_conditions, args.dry_run)
        total_success += count
        print()
    
    if args.market_regime_daily:
        count = load_market_regime_daily(args.market_regime_daily, args.dry_run)
        total_success += count
        print()
    
    print(f"✅ 전체 로드 완료: {total_success}개 레코드 처리")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


#!/usr/bin/env python3
"""
레짐 데이터 덤프 스크립트
로컬 DB의 market_conditions와 market_regime_daily 데이터를 JSON 파일로 덤프합니다.
"""
import sys
import json
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

from db_manager import db_manager

def dump_market_conditions(output_file: str):
    """market_conditions 테이블 데이터 덤프"""
    print(f"📊 market_conditions 테이블 덤프 중...")
    
    with db_manager.get_cursor(commit=False) as cur:
        # 모든 컬럼 조회 (실제 테이블 스키마에 맞게)
        cur.execute("""
            SELECT 
                date, market_sentiment, kospi_return, volatility, rsi_threshold,
                sector_rotation, foreign_flow, volume_trend,
                min_signals, macd_osc_min, vol_ma5_mult, gap_max, ext_from_tema20_max,
                created_at
            FROM market_conditions
            ORDER BY date DESC
        """)
        
        rows = cur.fetchall()
        columns = [desc.name for desc in cur.description]
        
        data = []
        for row in rows:
            record = {}
            for i, col in enumerate(columns):
                value = row[i]
                # JSONB 필드는 이미 dict/list이거나 None (현재 테이블에는 JSONB 필드 없음)
                record[col] = value
            data.append(record)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"✅ market_conditions 덤프 완료: {len(data)}개 레코드 -> {output_file}")
    return len(data)

def dump_market_regime_daily(output_file: str):
    """market_regime_daily 테이블 데이터 덤프"""
    print(f"📊 market_regime_daily 테이블 덤프 중...")
    
    try:
        with db_manager.get_cursor(commit=False) as cur:
            # 테이블 존재 확인
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
            
            # 모든 컬럼 조회
            cur.execute("""
                SELECT 
                    date, us_prev_sentiment, kr_sentiment, us_preopen_sentiment,
                    final_regime, us_metrics, kr_metrics, us_preopen_metrics,
                    run_timestamp, version,
                    us_futures_score, us_futures_regime, dxy, updated_at
                FROM market_regime_daily
                ORDER BY date DESC
            """)
            
            rows = cur.fetchall()
            columns = [desc.name for desc in cur.description]
            
            data = []
            for row in rows:
                record = {}
                for i, col in enumerate(columns):
                    value = row[i]
                    # JSONB 필드는 이미 dict/list이거나 None
                    if value is not None and col in ['us_metrics', 'kr_metrics', 'us_preopen_metrics']:
                        if isinstance(value, str):
                            try:
                                value = json.loads(value)
                            except:
                                pass
                    record[col] = value
                data.append(record)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"✅ market_regime_daily 덤프 완료: {len(data)}개 레코드 -> {output_file}")
        return len(data)
    except Exception as e:
        print(f"⚠️ market_regime_daily 덤프 실패: {e}")
        return 0

def main():
    """메인 함수"""
    # 출력 디렉토리 생성
    output_dir = Path(__file__).parent / "regime_dumps"
    output_dir.mkdir(exist_ok=True)
    
    # 타임스탬프 생성
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 출력 파일 경로
    market_conditions_file = output_dir / f"market_conditions_{timestamp}.json"
    market_regime_daily_file = output_dir / f"market_regime_daily_{timestamp}.json"
    metadata_file = output_dir / f"regime_dump_metadata_{timestamp}.json"
    
    print(f"🚀 레짐 데이터 덤프 시작...")
    print(f"출력 디렉토리: {output_dir}")
    print()
    
    # 덤프 실행
    mc_count = dump_market_conditions(str(market_conditions_file))
    mrd_count = dump_market_regime_daily(str(market_regime_daily_file))
    
    # 메타데이터 생성
    metadata = {
        "dump_timestamp": timestamp,
        "dump_date": datetime.now().isoformat(),
        "market_conditions": {
            "file": str(market_conditions_file.name),
            "record_count": mc_count
        },
        "market_regime_daily": {
            "file": str(market_regime_daily_file.name),
            "record_count": mrd_count
        }
    }
    
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    print()
    print(f"✅ 덤프 완료!")
    print(f"📁 덤프 파일:")
    print(f"   - {market_conditions_file.name} ({mc_count}개 레코드)")
    print(f"   - {market_regime_daily_file.name} ({mrd_count}개 레코드)")
    print(f"   - {metadata_file.name}")
    print()
    print(f"💡 서버에 업로드하려면:")
    print(f"   scp {output_dir}/*_{timestamp}.* ubuntu@your-server:/path/to/backend/regime_dumps/")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


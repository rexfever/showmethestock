"""
장세 분석 데이터 확정 시점 검증 스크립트
15:31부터 15:40까지 매분마다 실행하여 데이터 수집
"""
from datetime import datetime, date
from kiwoom_api import api
from db_manager import db_manager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def validate_market_data():
    """현재 시점의 시장 데이터 확정 여부 검증"""
    
    now = datetime.now()
    analysis_date = now.date()
    analysis_time = now.time()
    today_str = now.strftime('%Y%m%d')
    
    logger.info(f"📊 장세 데이터 검증 시작: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    
    kospi_return = None
    kospi_close = None
    kospi_prev_close = None
    samsung_return = None
    samsung_close = None
    samsung_prev_close = None
    data_available = False
    data_complete = False
    error_message = None
    
    try:
        # 1. KOSPI 지수 조회
        try:
            kospi_df = api.get_ohlcv('^KS11', 2, today_str)
            
            if not kospi_df.empty and len(kospi_df) >= 2:
                kospi_prev_close = float(kospi_df.iloc[-2]['close'])
                kospi_close = float(kospi_df.iloc[-1]['close'])
                kospi_return = (kospi_close / kospi_prev_close - 1) if kospi_prev_close > 0 else 0
                
                # 당일 데이터 날짜 확인
                last_date = str(kospi_df.iloc[-1]['date'])
                if last_date == today_str:
                    data_complete = True
                    logger.info(f"✅ KOSPI 당일 데이터 확인: {last_date}")
                else:
                    logger.warning(f"⚠️ KOSPI 데이터가 전일 것: {last_date} (기대: {today_str})")
                
                data_available = True
            else:
                error_message = "KOSPI 데이터 부족"
                logger.warning(f"⚠️ {error_message}")
                
        except Exception as e:
            error_message = f"KOSPI 조회 실패: {str(e)}"
            logger.error(f"❌ {error_message}")
        
        # 2. 삼성전자 조회 (대표 종목)
        try:
            samsung_df = api.get_ohlcv('005930', 2, today_str)
            
            if not samsung_df.empty and len(samsung_df) >= 2:
                samsung_prev_close = float(samsung_df.iloc[-2]['close'])
                samsung_close = float(samsung_df.iloc[-1]['close'])
                samsung_return = (samsung_close / samsung_prev_close - 1) if samsung_prev_close > 0 else 0
                
                # 당일 데이터 날짜 확인
                last_date = str(samsung_df.iloc[-1]['date'])
                if last_date == today_str:
                    logger.info(f"✅ 삼성전자 당일 데이터 확인: {last_date}")
                else:
                    data_complete = False
                    logger.warning(f"⚠️ 삼성전자 데이터가 전일 것: {last_date} (기대: {today_str})")
                    
        except Exception as e:
            logger.error(f"❌ 삼성전자 조회 실패: {str(e)}")
            if error_message:
                error_message += f" | 삼성전자: {str(e)}"
            else:
                error_message = f"삼성전자 조회 실패: {str(e)}"
        
        # 3. DB에 저장
        with db_manager.get_cursor(commit=True) as cur:
            cur.execute("""
                INSERT INTO market_analysis_validation (
                    analysis_date, analysis_time,
                    kospi_return, kospi_close, kospi_prev_close,
                    samsung_return, samsung_close, samsung_prev_close,
                    data_available, data_complete, error_message
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (analysis_date, analysis_time) DO UPDATE SET
                    kospi_return = EXCLUDED.kospi_return,
                    kospi_close = EXCLUDED.kospi_close,
                    kospi_prev_close = EXCLUDED.kospi_prev_close,
                    samsung_return = EXCLUDED.samsung_return,
                    samsung_close = EXCLUDED.samsung_close,
                    samsung_prev_close = EXCLUDED.samsung_prev_close,
                    data_available = EXCLUDED.data_available,
                    data_complete = EXCLUDED.data_complete,
                    error_message = EXCLUDED.error_message,
                    created_at = NOW()
            """, (
                analysis_date, analysis_time,
                kospi_return, kospi_close, kospi_prev_close,
                samsung_return, samsung_close, samsung_prev_close,
                data_available, data_complete, error_message
            ))
        
        logger.info(f"✅ 검증 데이터 저장 완료")
        logger.info(f"   - KOSPI: {kospi_return*100:.2f}% ({kospi_close:,.0f})" if kospi_return else "   - KOSPI: N/A")
        logger.info(f"   - 삼성전자: {samsung_return*100:.2f}% ({samsung_close:,.0f}원)" if samsung_return else "   - 삼성전자: N/A")
        logger.info(f"   - 데이터 가용: {data_available}, 완전성: {data_complete}")
        
    except Exception as e:
        logger.error(f"❌ 검증 프로세스 오류: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    validate_market_data()


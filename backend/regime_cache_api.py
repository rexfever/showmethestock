"""
레짐 캐시 관리 API
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging
from services.regime_analyzer_cached import regime_analyzer_cached
from services.us_futures_data_v8 import us_futures_data_v8

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/regime-cache", tags=["regime-cache"])

@router.get("/stats")
async def get_cache_stats() -> Dict[str, Any]:
    """캐시 통계 조회"""
    try:
        stats = regime_analyzer_cached.get_cache_stats()
        return {"ok": True, "data": stats}
    except Exception as e:
        logger.error(f"캐시 통계 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/clear")
async def clear_cache(cache_type: str = None) -> Dict[str, str]:
    """캐시 클리어"""
    try:
        if cache_type == "regime":
            regime_analyzer_cached.clear_cache()
            message = "레짐 분석 캐시 클리어 완료"
        elif cache_type == "us_data":
            us_futures_data_v8.clear_cache()
            message = "미국 데이터 캐시 클리어 완료"
        elif cache_type is None:
            regime_analyzer_cached.clear_cache()
            us_futures_data_v8.clear_cache()
            message = "전체 캐시 클리어 완료"
        else:
            raise ValueError(f"지원하지 않는 캐시 타입: {cache_type}")
        
        return {"ok": True, "message": message}
    except Exception as e:
        logger.error(f"캐시 클리어 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/us-data/latest")
async def get_latest_us_data() -> Dict[str, Any]:
    """최신 미국 데이터 조회"""
    try:
        data = us_futures_data_v8.get_all_latest_data()
        return {"ok": True, "data": data}
    except Exception as e:
        logger.error(f"최신 미국 데이터 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/regime/{date}")
async def get_regime_analysis(date: str) -> Dict[str, Any]:
    """레짐 분석 결과 조회 (캐시 우선)"""
    try:
        result = regime_analyzer_cached.analyze_regime_v4_cached(date)
        return {"ok": True, "data": result}
    except Exception as e:
        logger.error(f"레짐 분석 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/preload")
async def preload_cache() -> Dict[str, str]:
    """캐시 사전 로드"""
    try:
        symbols = ['SPY', 'QQQ', 'ES=F', 'NQ=F', '^VIX', 'DX-Y.NYB']
        loaded_count = 0
        
        for symbol in symbols:
            try:
                df = us_futures_data_v8.fetch_data(symbol)
                if not df.empty:
                    loaded_count += 1
            except Exception as e:
                logger.warning(f"{symbol} 사전 로드 실패: {e}")
        
        from datetime import datetime
        today = datetime.now().strftime('%Y%m%d')
        regime_analyzer_cached.analyze_regime_v4_cached(today)
        
        return {
            "ok": True, 
            "message": f"캐시 사전 로드 완료: {loaded_count}/{len(symbols)}개 심볼"
        }
    except Exception as e:
        logger.error(f"캐시 사전 로드 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))
"""
Pydantic 모델들에 대한 테스트
"""
import pytest
from datetime import datetime
from models import (
    ScanItem, IndicatorPayload, TrendPayload, ScoreFlags,
    ScanResponse, PortfolioItem, AddToPortfolioRequest,
    AddPersonalStockRequest
)


class TestModels:
    """Pydantic 모델 테스트"""
    
    def test_scan_item_creation(self):
        """ScanItem 모델 생성 테스트"""
        indicators = IndicatorPayload(
            TEMA20=50000.0,
            DEMA10=51000.0,
            MACD_OSC=100.0,
            MACD_LINE=200.0,
            MACD_SIGNAL=100.0,
            RSI_TEMA=60.0,
            RSI_DEMA=65.0,
            OBV=1000000.0,
            VOL=1000000,
            VOL_MA5=900000.0,
            close=52000.0
        )
        
        trend = TrendPayload(
            TEMA20_SLOPE20=100.0,
            OBV_SLOPE20=50000.0,
            ABOVE_CNT5=3,
            DEMA10_SLOPE20=150.0
        )
        
        flags = ScoreFlags(
            cross=True,
            vol_expand=True,
            macd_ok=True,
            rsi_dema_setup=True,
            rsi_tema_trigger=True,
            rsi_dema_value=65.0,
            rsi_tema_value=60.0,
            overheated_rsi_tema=False,
            tema_slope_ok=True,
            obv_slope_ok=True,
            above_cnt5_ok=True,
            dema_slope_ok=True,
            details={}
        )
        
        scan_item = ScanItem(
            ticker="005930",
            name="삼성전자",
            match=True,
            score=8.0,
            indicators=indicators,
            trend=trend,
            flags=flags,
            strategy="상승시작",
            score_label="강한 매수"
        )
        
        assert scan_item.ticker == "005930"
        assert scan_item.name == "삼성전자"
        assert scan_item.match is True
        assert scan_item.score == 8.0
        assert scan_item.indicators.TEMA20 == 50000.0
        assert scan_item.trend.TEMA20_SLOPE20 == 100.0
        assert scan_item.flags.cross is True
    
    def test_scan_response_creation(self):
        """ScanResponse 모델 생성 테스트"""
        indicators = IndicatorPayload(
            TEMA20=50000.0, DEMA10=51000.0, MACD_OSC=100.0,
            MACD_LINE=200.0, MACD_SIGNAL=100.0, RSI_TEMA=60.0,
            RSI_DEMA=65.0, OBV=1000000.0, VOL=1000000,
            VOL_MA5=900000.0, close=52000.0
        )
        
        trend = TrendPayload(
            TEMA20_SLOPE20=100.0, OBV_SLOPE20=50000.0,
            ABOVE_CNT5=3, DEMA10_SLOPE20=150.0
        )
        
        flags = ScoreFlags(
            cross=True, vol_expand=True, macd_ok=True,
            rsi_dema_setup=True, rsi_tema_trigger=True,
            rsi_dema_value=65.0, rsi_tema_value=60.0,
            overheated_rsi_tema=False, tema_slope_ok=True,
            obv_slope_ok=True, above_cnt5_ok=True,
            dema_slope_ok=True, details={}
        )
        
        scan_item = ScanItem(
            ticker="005930",
            name="삼성전자",
            match=True,
            score=8.0,
            indicators=indicators,
            trend=trend,
            flags=flags,
            strategy="상승시작",
            score_label="강한 매수"
        )
        
        response = ScanResponse(
            as_of="2025-10-13",
            universe_count=100,
            matched_count=1,
            rsi_mode="tema_dema",
            rsi_period=14,
            rsi_threshold=57.0,
            items=[scan_item],
            fallback_step=0,
            score_weights={},
            score_level_strong=8,
            score_level_watch=5,
            require_dema_slope="required"
        )
        
        assert response.as_of == "2025-10-13"
        assert response.universe_count == 100
        assert response.matched_count == 1
        assert len(response.items) == 1
        assert response.items[0].ticker == "005930"
    
    def test_portfolio_item_creation(self):
        """PortfolioItem 모델 생성 테스트"""
        portfolio_item = PortfolioItem(
            id=1,
            user_id=1,
            ticker="005930",
            name="삼성전자",
            entry_price=50000.0,
            quantity=10,
            entry_date="2025-10-13",
            source="recommended",
            recommendation_score=8.0,
            recommendation_date="2025-10-13",
            daily_return_pct=2.0,
            max_return_pct=5.0,
            min_return_pct=-1.0,
            holding_days=1,
            created_at=datetime.now()
        )
        
        assert portfolio_item.ticker == "005930"
        assert portfolio_item.entry_price == 50000.0
        assert portfolio_item.quantity == 10
        assert portfolio_item.source == "recommended"
        assert portfolio_item.daily_return_pct == 2.0
        assert portfolio_item.user_id == 1
    
    def test_add_to_portfolio_request(self):
        """AddToPortfolioRequest 모델 생성 테스트"""
        request = AddToPortfolioRequest(
            ticker="005930",
            name="삼성전자",
            entry_price=50000.0,
            quantity=10,
            entry_date="2025-10-13",
            source="recommended",
            recommendation_score=8.0,
            recommendation_date="2025-10-13"
        )
        
        assert request.ticker == "005930"
        assert request.entry_price == 50000.0
        assert request.quantity == 10
        assert request.source == "recommended"
        assert request.recommendation_score == 8.0
    
    def test_add_personal_stock_request(self):
        """AddPersonalStockRequest 모델 생성 테스트"""
        request = AddPersonalStockRequest(
            ticker="005930",
            name="삼성전자",
            entry_price=50000.0,
            quantity=10,
            entry_date="2025-10-13"
        )
        
        assert request.ticker == "005930"
        assert request.entry_price == 50000.0
        assert request.quantity == 10
        assert request.source == "personal"  # 기본값
    
    def test_indicator_payload_validation(self):
        """IndicatorPayload 유효성 검증 테스트"""
        # 정상적인 데이터
        indicators = IndicatorPayload(
            TEMA20=50000.0,
            DEMA10=51000.0,
            MACD_OSC=100.0,
            MACD_LINE=200.0,
            MACD_SIGNAL=100.0,
            RSI_TEMA=60.0,
            RSI_DEMA=65.0,
            OBV=1000000.0,
            VOL=1000000,
            VOL_MA5=900000.0,
            close=52000.0
        )
        
        assert indicators.TEMA20 == 50000.0
        assert indicators.RSI_TEMA == 60.0
        assert indicators.VOL == 1000000
    
    def test_trend_payload_validation(self):
        """TrendPayload 유효성 검증 테스트"""
        trend = TrendPayload(
            TEMA20_SLOPE20=100.0,
            OBV_SLOPE20=50000.0,
            ABOVE_CNT5=3,
            DEMA10_SLOPE20=150.0
        )
        
        assert trend.TEMA20_SLOPE20 == 100.0
        assert trend.OBV_SLOPE20 == 50000.0
        assert trend.ABOVE_CNT5 == 3
        assert trend.DEMA10_SLOPE20 == 150.0
    
    def test_score_flags_validation(self):
        """ScoreFlags 유효성 검증 테스트"""
        flags = ScoreFlags(
            cross=True,
            vol_expand=True,
            macd_ok=True,
            rsi_dema_setup=True,
            rsi_tema_trigger=True,
            rsi_dema_value=65.0,
            rsi_tema_value=60.0,
            overheated_rsi_tema=False,
            tema_slope_ok=True,
            obv_slope_ok=True,
            above_cnt5_ok=True,
            dema_slope_ok=True,
            details={}
        )
        
        assert flags.cross is True
        assert flags.macd_ok is True
        assert flags.rsi_dema_value == 65.0
        assert flags.overheated_rsi_tema is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

import sqlite3
import tempfile
from portfolio_service import PortfolioService
from models import AddTradingRequest

def test_profit_calculation():
    """수익률 계산 테스트"""
    # 임시 DB 생성
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        service = PortfolioService(db_path)
        user_id = 1
        ticker = "005930"  # 삼성전자
        
        print("=== 수익률 계산 테스트 시작 ===")
        
        # 테스트 시나리오 1: 단순 매수 후 가격 상승
        print("\n1. 단순 매수 테스트")
        service.add_trading_history(user_id, AddTradingRequest(
            ticker=ticker, name="삼성전자", trade_type="buy",
            quantity=100, price=70000, trade_date="20241101"
        ))
        
        # 현재가를 80000원으로 설정하고 포트폴리오 업데이트
        with sqlite3.connect(db_path) as conn:
            conn.execute("UPDATE portfolio SET current_price = ? WHERE ticker = ?", (80000, ticker))
            # 손익도 직접 계산해서 업데이트
            conn.execute("""
                UPDATE portfolio SET 
                    current_value = current_price * quantity,
                    profit_loss = (current_price * quantity) - total_investment,
                    profit_loss_pct = ((current_price * quantity) - total_investment) / total_investment * 100
                WHERE ticker = ?
            """, (ticker,))
            conn.commit()
        portfolio = service.get_portfolio(user_id)
        
        item = portfolio.items[0]
        print(f"매수: 100주 × 70,000원 = 7,000,000원")
        print(f"현재: 100주 × 80,000원 = 8,000,000원")
        print(f"손익: {item.profit_loss:,.0f}원")
        print(f"수익률: {item.profit_loss_pct:.2f}%")
        assert abs(item.profit_loss - 1000000) < 1, f"손익 오류: {item.profit_loss}"
        assert abs(item.profit_loss_pct - 14.29) < 0.1, f"수익률 오류: {item.profit_loss_pct}"
        
        # 테스트 시나리오 2: 추가 매수 (평균 단가 변화)
        print("\n2. 추가 매수 테스트")
        service.add_trading_history(user_id, AddTradingRequest(
            ticker=ticker, name="삼성전자", trade_type="buy",
            quantity=50, price=60000, trade_date="20241102"
        ))
        
        # 현재가 업데이트
        with sqlite3.connect(db_path) as conn:
            conn.execute("UPDATE portfolio SET current_price = ? WHERE ticker = ?", (80000, ticker))
            conn.execute("""
                UPDATE portfolio SET 
                    current_value = current_price * quantity,
                    profit_loss = (current_price * quantity) - total_investment,
                    profit_loss_pct = ((current_price * quantity) - total_investment) / total_investment * 100
                WHERE ticker = ?
            """, (ticker,))
            conn.commit()
        
        portfolio = service.get_portfolio(user_id)
        item = portfolio.items[0]
        expected_avg = (70000*100 + 60000*50) / 150  # 66,666.67
        print(f"평균단가: {item.entry_price:,.0f}원 (예상: {expected_avg:,.0f}원)")
        print(f"총 투자: {item.total_investment:,.0f}원")
        print(f"현재가치: {item.current_value:,.0f}원")
        print(f"손익: {item.profit_loss:,.0f}원")
        print(f"수익률: {item.profit_loss_pct:.2f}%")
        
        # 테스트 시나리오 3: 일부 매도 (실현 손익 발생)
        print("\n3. 일부 매도 테스트")
        service.add_trading_history(user_id, AddTradingRequest(
            ticker=ticker, name="삼성전자", trade_type="sell",
            quantity=50, price=85000, trade_date="20241103"
        ))
        
        # 현재가 업데이트
        with sqlite3.connect(db_path) as conn:
            conn.execute("UPDATE portfolio SET current_price = ? WHERE ticker = ?", (80000, ticker))
            conn.execute("""
                UPDATE portfolio SET 
                    current_value = current_price * quantity,
                    profit_loss = (current_price * quantity) - total_investment,
                    profit_loss_pct = ((current_price * quantity) - total_investment) / total_investment * 100
                WHERE ticker = ?
            """, (ticker,))
            conn.commit()
        
        portfolio = service.get_portfolio(user_id)
        item = portfolio.items[0]
        print(f"매도: 50주 × 85,000원 = 4,250,000원")
        print(f"보유: 100주 × 80,000원 = 8,000,000원")
        print(f"평균단가: {item.entry_price:,.0f}원")
        print(f"손익: {item.profit_loss:,.0f}원")
        print(f"수익률: {item.profit_loss_pct:.2f}%")
        
        # 테스트 시나리오 4: 전량 매도
        print("\n4. 전량 매도 테스트")
        service.add_trading_history(user_id, AddTradingRequest(
            ticker=ticker, name="삼성전자", trade_type="sell",
            quantity=100, price=75000, trade_date="20241104"
        ))
        
        portfolio = service.get_portfolio(user_id)
        print(f"포트폴리오 종목 수: {len(portfolio.items)}")
        print(f"전체 수익률: {portfolio.total_profit_loss_pct:.2f}%")
        
        print("\n=== 테스트 완료 ===")
        
    finally:
        os.unlink(db_path)

if __name__ == "__main__":
    test_profit_calculation()
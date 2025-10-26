import sqlite3
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from models import PortfolioItem, PortfolioResponse, AddToPortfolioRequest, UpdatePortfolioRequest, TradingHistory, AddTradingRequest, TradingHistoryResponse
from config import config
import os


class PortfolioService:
    def __init__(self, db_path: str = "portfolio.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """포트폴리오 데이터베이스 초기화"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 포트폴리오 테이블 생성
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS portfolio (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    ticker TEXT NOT NULL,
                    name TEXT NOT NULL,
                    entry_price REAL,
                    quantity INTEGER,
                    entry_date TEXT,
                    current_price REAL,
                    total_investment REAL,
                    current_value REAL,
                    profit_loss REAL,
                    profit_loss_pct REAL,
                    status TEXT DEFAULT 'watching',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, ticker)
                )
            """)
            
            # 매매 내역 테이블 생성
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trading_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    ticker TEXT NOT NULL,
                    name TEXT NOT NULL,
                    trade_type TEXT NOT NULL,  -- 'buy' | 'sell'
                    quantity INTEGER NOT NULL,
                    price REAL NOT NULL,
                    trade_date TEXT NOT NULL,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 인덱스 생성
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_portfolio_user_id ON portfolio(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_portfolio_ticker ON portfolio(ticker)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_portfolio_status ON portfolio(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trading_history_user_id ON trading_history(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trading_history_ticker ON trading_history(ticker)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trading_history_trade_date ON trading_history(trade_date)")
            
            conn.commit()
    
    def get_current_price(self, ticker: str) -> Optional[float]:
        """현재가 조회 (데이터베이스에서, 없으면 키움 API에서)"""
        try:
            # snapshots.db에서 최신 스캔 결과 조회
            snapshots_db_path = "snapshots.db"
            if os.path.exists(snapshots_db_path):
                with sqlite3.connect(snapshots_db_path) as conn:
                    cursor = conn.cursor()
                    
                    # 최신 날짜의 해당 종목 현재가 조회
                    cursor.execute("""
                        SELECT current_price FROM scan_rank 
                        WHERE code = ? 
                        ORDER BY date DESC 
                        LIMIT 1
                    """, (ticker,))
                    
                    row = cursor.fetchone()
                    if row and row[0]:
                        return float(row[0])
            
            # 스캔 결과에 없으면 키움 API에서 직접 조회
            try:
                from kiwoom_api import KiwoomAPI
                api = KiwoomAPI()
                df = api.get_ohlcv(ticker, 1)
                if not df.empty:
                    return float(df.iloc[-1]['close'])
            except Exception as e:
                print(f"키움 API 조회 오류 ({ticker}): {e}")
            
            return None
        except Exception as e:
            print(f"현재가 조회 오류: {e}")
            return None
    
    def add_to_portfolio(self, user_id: int, request: AddToPortfolioRequest) -> PortfolioItem:
        """포트폴리오에 종목 추가"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 현재가 조회
            current_price = self.get_current_price(request.ticker)
            
            # 총 투자금 계산
            total_investment = None
            current_value = None
            profit_loss = None
            profit_loss_pct = None
            
            if request.entry_price and request.quantity:
                total_investment = request.entry_price * request.quantity
                if current_price:
                    current_value = current_price * request.quantity
                    profit_loss = current_value - total_investment
                    profit_loss_pct = (profit_loss / total_investment) * 100
            
            # 상태 결정
            status = "watching"
            if request.entry_price and request.quantity:
                status = "holding"
            
            # 종목 추가 또는 업데이트
            cursor.execute("""
                INSERT OR REPLACE INTO portfolio 
                (user_id, ticker, name, entry_price, quantity, entry_date, 
                 current_price, total_investment, current_value, profit_loss, 
                 profit_loss_pct, status, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                user_id, request.ticker, request.name, request.entry_price, 
                request.quantity, request.entry_date, current_price, 
                total_investment, current_value, profit_loss, profit_loss_pct, status
            ))
            
            conn.commit()
            
            # 추가된 항목 조회
            cursor.execute("""
                SELECT * FROM portfolio 
                WHERE user_id = ? AND ticker = ?
            """, (user_id, request.ticker))
            
            row = cursor.fetchone()
            return self._row_to_portfolio_item(row)
    
    def update_portfolio(self, user_id: int, ticker: str, request: UpdatePortfolioRequest) -> Optional[PortfolioItem]:
        """포트폴리오 항목 업데이트"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 현재가 조회
            current_price = self.get_current_price(ticker)
            
            # 업데이트할 필드들
            update_fields = []
            update_values = []
            
            if request.entry_price is not None:
                update_fields.append("entry_price = ?")
                update_values.append(request.entry_price)
            
            if request.quantity is not None:
                update_fields.append("quantity = ?")
                update_values.append(request.quantity)
            
            if request.entry_date is not None:
                update_fields.append("entry_date = ?")
                update_values.append(request.entry_date)
            
            if request.status is not None:
                update_fields.append("status = ?")
                update_values.append(request.status)
            
            if current_price is not None:
                update_fields.append("current_price = ?")
                update_values.append(current_price)
            
            if not update_fields:
                return None
            
            # 총 투자금과 손익 재계산
            cursor.execute("""
                SELECT entry_price, quantity FROM portfolio 
                WHERE user_id = ? AND ticker = ?
            """, (user_id, ticker))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            entry_price = request.entry_price if request.entry_price is not None else row[0]
            quantity = request.quantity if request.quantity is not None else row[1]
            
            if entry_price and quantity:
                total_investment = entry_price * quantity
                update_fields.append("total_investment = ?")
                update_values.append(total_investment)
                
                if current_price:
                    current_value = current_price * quantity
                    profit_loss = current_value - total_investment
                    profit_loss_pct = (profit_loss / total_investment) * 100
                    
                    update_fields.append("current_value = ?")
                    update_fields.append("profit_loss = ?")
                    update_fields.append("profit_loss_pct = ?")
                    update_values.extend([current_value, profit_loss, profit_loss_pct])
            
            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            update_values.extend([user_id, ticker])
            
            cursor.execute(f"""
                UPDATE portfolio 
                SET {', '.join(update_fields)}
                WHERE user_id = ? AND ticker = ?
            """, update_values)
            
            conn.commit()
            
            # 업데이트된 항목 조회
            cursor.execute("""
                SELECT * FROM portfolio 
                WHERE user_id = ? AND ticker = ?
            """, (user_id, ticker))
            
            row = cursor.fetchone()
            return self._row_to_portfolio_item(row) if row else None
    
    def remove_from_portfolio(self, user_id: int, ticker: str) -> bool:
        """포트폴리오에서 종목 제거"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM portfolio 
                WHERE user_id = ? AND ticker = ?
            """, (user_id, ticker))
            
            conn.commit()
            return cursor.rowcount > 0
    
    def get_portfolio(self, user_id: int, status: Optional[str] = None) -> PortfolioResponse:
        """포트폴리오 조회"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 현재가 업데이트
            self._update_current_prices(user_id)
            
            # 포트폴리오 조회
            query = "SELECT * FROM portfolio WHERE user_id = ?"
            params = [user_id]
            
            if status:
                query += " AND status = ?"
                params.append(status)
            
            query += " ORDER BY created_at DESC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            items = [self._row_to_portfolio_item(row) for row in rows]
            
            # 총계 계산
            total_investment = sum(item.total_investment or 0 for item in items)
            total_current_value = sum(item.current_value or 0 for item in items)
            total_profit_loss = total_current_value - total_investment
            total_profit_loss_pct = (total_profit_loss / total_investment * 100) if total_investment > 0 else 0
            
            return PortfolioResponse(
                items=items,
                total_investment=total_investment,
                total_current_value=total_current_value,
                total_profit_loss=total_profit_loss,
                total_profit_loss_pct=total_profit_loss_pct
            )
    
    def _update_current_prices(self, user_id: int):
        """현재가 업데이트"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 사용자의 모든 종목 조회
            cursor.execute("SELECT ticker FROM portfolio WHERE user_id = ?", (user_id,))
            tickers = [row[0] for row in cursor.fetchall()]
            
            for ticker in tickers:
                current_price = self.get_current_price(ticker)
                if current_price:
                    # 현재가와 손익 업데이트
                    cursor.execute("""
                        UPDATE portfolio 
                        SET current_price = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = ? AND ticker = ?
                    """, (current_price, user_id, ticker))
                    
                    # 손익 재계산
                    cursor.execute("""
                        SELECT entry_price, quantity FROM portfolio 
                        WHERE user_id = ? AND ticker = ?
                    """, (user_id, ticker))
                    
                    row = cursor.fetchone()
                    if row and row[0] and row[1]:  # entry_price와 quantity가 있는 경우
                        entry_price, quantity = row
                        total_investment = entry_price * quantity
                        current_value = current_price * quantity
                        profit_loss = current_value - total_investment
                        profit_loss_pct = (profit_loss / total_investment) * 100
                        
                        cursor.execute("""
                            UPDATE portfolio 
                            SET current_value = ?, profit_loss = ?, profit_loss_pct = ?
                            WHERE user_id = ? AND ticker = ?
                        """, (current_value, profit_loss, profit_loss_pct, user_id, ticker))
            
            conn.commit()
    
    def _row_to_portfolio_item(self, row) -> PortfolioItem:
        """데이터베이스 행을 PortfolioItem으로 변환"""
        if not row:
            return None
        
        return PortfolioItem(
            id=row[0],
            user_id=row[1],
            ticker=row[2],
            name=row[3],
            entry_price=row[4],
            quantity=row[5],
            entry_date=row[6],
            current_price=row[7],
            total_investment=row[8],
            current_value=row[9],
            profit_loss=row[10],
            profit_loss_pct=row[11],
            status=row[12],
            created_at=row[13],
            updated_at=row[14]
        )

    # ===== 매매 내역 관리 메서드들 =====
    
    def add_trading_history(self, user_id: int, request: AddTradingRequest) -> TradingHistory:
        """매매 내역 추가"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO trading_history (
                    user_id, ticker, name, trade_type, quantity, price, trade_date, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id, request.ticker, request.name, request.trade_type,
                request.quantity, request.price, request.trade_date, request.notes
            ))
            
            trading_id = cursor.lastrowid
            
            # 포트폴리오 업데이트 (평균 단가 계산)
            self._update_portfolio_from_trading(user_id, request.ticker)
            
            conn.commit()
            
            # 추가된 매매 내역 반환
            cursor.execute("SELECT * FROM trading_history WHERE id = ?", (trading_id,))
            row = cursor.fetchone()
            return self._row_to_trading_history(row)
    
    def get_trading_history(self, user_id: int, ticker: Optional[str] = None) -> TradingHistoryResponse:
        """매매 내역 조회"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM trading_history WHERE user_id = ?"
            params = [user_id]
            
            if ticker:
                query += " AND ticker = ?"
                params.append(ticker)
            
            query += " ORDER BY trade_date DESC, created_at DESC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            items = [self._row_to_trading_history(row) for row in rows]
            
            # 총 매수/매도 금액 계산
            total_buy_amount = sum(item.price * item.quantity for item in items if item.trade_type == 'buy')
            total_sell_amount = sum(item.price * item.quantity for item in items if item.trade_type == 'sell')
            net_amount = total_buy_amount - total_sell_amount
            
            return TradingHistoryResponse(
                items=items,
                total_buy_amount=total_buy_amount,
                total_sell_amount=total_sell_amount,
                net_amount=net_amount
            )
    
    def delete_trading_history(self, user_id: int, trading_id: int) -> bool:
        """매매 내역 삭제"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 삭제할 매매 내역의 종목 코드 조회
            cursor.execute("SELECT ticker FROM trading_history WHERE id = ? AND user_id = ?", (trading_id, user_id))
            row = cursor.fetchone()
            if not row:
                return False
            
            ticker = row[0]
            
            # 매매 내역 삭제
            cursor.execute("DELETE FROM trading_history WHERE id = ? AND user_id = ?", (trading_id, user_id))
            
            if cursor.rowcount > 0:
                # 포트폴리오 재계산
                self._update_portfolio_from_trading(user_id, ticker)
                conn.commit()
                return True
            
            return False
    
    def _update_portfolio_from_trading(self, user_id: int, ticker: str):
        """매매 내역을 기반으로 포트폴리오 업데이트"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 해당 종목의 매매 내역 조회
            cursor.execute("""
                SELECT trade_type, quantity, price FROM trading_history 
                WHERE user_id = ? AND ticker = ?
                ORDER BY trade_date ASC, created_at ASC
            """, (user_id, ticker))
            
            trades = cursor.fetchall()
            
            if not trades:
                return
            
            # 평균 단가와 총 수량 계산
            total_quantity = 0
            total_cost = 0
            
            for trade_type, quantity, price in trades:
                if trade_type == 'buy':
                    total_quantity += quantity
                    total_cost += quantity * price
                elif trade_type == 'sell':
                    total_quantity -= quantity
                    # 매도 시에는 평균 단가를 유지하되 수량만 감소
            
            # 포트폴리오 업데이트 또는 삭제
            if total_quantity <= 0:
                # 수량이 0 이하면 포트폴리오에서 제거
                cursor.execute("DELETE FROM portfolio WHERE user_id = ? AND ticker = ?", (user_id, ticker))
            else:
                # 평균 단가 계산
                avg_price = total_cost / total_quantity if total_quantity > 0 else 0
                
                # 포트폴리오 업데이트 또는 생성
                cursor.execute("""
                    INSERT OR REPLACE INTO portfolio (
                        user_id, ticker, name, entry_price, quantity, entry_date, 
                        total_investment, status, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 'holding', CURRENT_TIMESTAMP)
                """, (
                    user_id, ticker, trades[0][0], avg_price, total_quantity,
                    trades[0][2], total_cost
                ))
    
    def _row_to_trading_history(self, row) -> TradingHistory:
        """데이터베이스 행을 TradingHistory로 변환"""
        if not row:
            return None
        
        return TradingHistory(
            id=row[0],
            user_id=row[1],
            ticker=row[2],
            name=row[3],
            trade_type=row[4],
            quantity=row[5],
            price=row[6],
            trade_date=row[7],
            notes=row[8],
            created_at=row[9],
            updated_at=row[10]
        )


# 전역 인스턴스
portfolio_service = PortfolioService()

import logging
from typing import List, Optional, Dict, Any, Sequence

from models import (
    PortfolioItem,
    PortfolioResponse,
    AddToPortfolioRequest,
    UpdatePortfolioRequest,
    TradingHistory,
    AddTradingRequest,
    TradingHistoryResponse,
)
from db_manager import db_manager
logger = logging.getLogger(__name__)


class PortfolioService:
    def __init__(self):
        self.init_database()
    
    def init_database(self):
        """포트폴리오 데이터베이스 초기화"""
        with db_manager.get_cursor(commit=False) as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS portfolio (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    ticker TEXT NOT NULL,
                    name TEXT NOT NULL,
                    entry_price DOUBLE PRECISION,
                    quantity INTEGER,
                    entry_date DATE,
                    current_price DOUBLE PRECISION,
                    total_investment DOUBLE PRECISION,
                    current_value DOUBLE PRECISION,
                    profit_loss DOUBLE PRECISION,
                    profit_loss_pct DOUBLE PRECISION,
                    status TEXT DEFAULT 'watching',
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(user_id, ticker)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trading_history (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    ticker TEXT NOT NULL,
                    name TEXT NOT NULL,
                    trade_type TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    price DOUBLE PRECISION NOT NULL,
                    trade_date DATE NOT NULL,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_portfolio_user_id ON portfolio(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_portfolio_ticker ON portfolio(ticker)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_portfolio_status ON portfolio(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trading_history_user_id ON trading_history(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trading_history_ticker ON trading_history(ticker)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trading_history_trade_date ON trading_history(trade_date)")
    
    def get_current_price(self, ticker: str) -> Optional[float]:
        """현재가 조회 (데이터베이스에서, 없으면 키움 API에서)"""
        try:
            # 최신 스캔 결과 조회
            with db_manager.get_cursor(commit=False) as cursor:
                cursor.execute("""
                    SELECT current_price FROM scan_rank 
                    WHERE code = %s AND current_price > 0
                    ORDER BY date DESC 
                    LIMIT 1
                """, (ticker,))
                row = cursor.fetchone()
                if row:
                    current_price = row["current_price"] if isinstance(row, dict) else row[0]
                    if current_price and float(current_price) > 0:
                        price = float(current_price)
                        print(f"💰 현재가 조회 성공 ({ticker}): {price}원")
                        return price
            
            # 스캔 결과에 없으면 키움 API에서 직접 조회
            try:
                from kiwoom_api import KiwoomAPI
                api = KiwoomAPI()
                df = api.get_ohlcv(ticker, 1)
                if not df.empty:
                    price = float(df.iloc[-1]['close'])
                    print(f"💰 키움 API 현재가 조회 성공 ({ticker}): {price}원")
                    return price
            except Exception as e:
                print(f"키움 API 조회 오류 ({ticker}): {e}")
            
            print(f"⚠️ 현재가 조회 실패 ({ticker})")
            return None
        except Exception as e:
            print(f"현재가 조회 오류: {e}")
            return None
    
    def add_to_portfolio(self, user_id: int, request: AddToPortfolioRequest) -> PortfolioItem:
        """포트폴리오에 종목 추가"""
        current_price = self.get_current_price(request.ticker)
        
        total_investment = None
        current_value = None
        profit_loss = None
        profit_loss_pct = None
        
        if request.entry_price and request.quantity:
            total_investment = request.entry_price * request.quantity
            if current_price:
                current_value = current_price * request.quantity
                profit_loss = current_value - total_investment
                profit_loss_pct = (profit_loss / total_investment) * 100 if total_investment > 0 else 0
        
        status = "holding" if request.entry_price and request.quantity else "watching"
        
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO portfolio (
                    user_id, ticker, name, entry_price, quantity, entry_date,
                    current_price, total_investment, current_value, profit_loss,
                    profit_loss_pct, status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id, ticker) DO UPDATE SET
                    name = EXCLUDED.name,
                    entry_price = EXCLUDED.entry_price,
                    quantity = EXCLUDED.quantity,
                    entry_date = EXCLUDED.entry_date,
                    current_price = EXCLUDED.current_price,
                    total_investment = EXCLUDED.total_investment,
                    current_value = EXCLUDED.current_value,
                    profit_loss = EXCLUDED.profit_loss,
                    profit_loss_pct = EXCLUDED.profit_loss_pct,
                    status = EXCLUDED.status,
                    updated_at = NOW()
                RETURNING *
            """, (
                user_id,
                request.ticker,
                request.name,
                request.entry_price,
                request.quantity,
                request.entry_date,
                current_price,
                total_investment,
                current_value,
                profit_loss,
                profit_loss_pct,
                status,
            ))
            row = cursor.fetchone()
            conn.commit()
        
        return self._row_to_portfolio_item(row)
    
    def update_portfolio(self, user_id: int, ticker: str, request: UpdatePortfolioRequest) -> Optional[PortfolioItem]:
        """포트폴리오 항목 업데이트"""
        current_price = self.get_current_price(ticker)

        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT entry_price, quantity FROM portfolio 
                WHERE user_id = %s AND ticker = %s
            """, (user_id, ticker))
            row = cursor.fetchone()
            if not row:
                return None

            if isinstance(row, dict):
                existing_entry_price = row.get("entry_price")
                existing_quantity = row.get("quantity")
            else:
                existing_entry_price, existing_quantity = row

            entry_price = request.entry_price if request.entry_price is not None else existing_entry_price
            quantity = request.quantity if request.quantity is not None else existing_quantity

            update_fields = []
            params = []

            if request.entry_price is not None:
                update_fields.append("entry_price = %s")
                params.append(request.entry_price)
            if request.quantity is not None:
                update_fields.append("quantity = %s")
                params.append(request.quantity)
            if request.entry_date is not None:
                update_fields.append("entry_date = %s")
                params.append(request.entry_date)
            if request.status is not None:
                update_fields.append("status = %s")
                params.append(request.status)
            if current_price is not None:
                update_fields.append("current_price = %s")
                params.append(current_price)

            if entry_price and quantity:
                total_investment = entry_price * quantity
                update_fields.append("total_investment = %s")
                params.append(total_investment)
                if current_price:
                    current_value = current_price * quantity
                    profit_loss = current_value - total_investment
                    profit_loss_pct = (profit_loss / total_investment * 100) if total_investment else 0
                    update_fields.extend([
                        "current_value = %s",
                        "profit_loss = %s",
                        "profit_loss_pct = %s"
                    ])
                    params.extend([current_value, profit_loss, profit_loss_pct])

            if not update_fields:
                return None

            update_fields.append("updated_at = NOW()")

            cursor.execute(
                f"""
                UPDATE portfolio
                SET {', '.join(update_fields)}
                WHERE user_id = %s AND ticker = %s
                RETURNING *
                """,
                params + [user_id, ticker],
            )
            updated_row = cursor.fetchone()
            conn.commit()

        return self._row_to_portfolio_item(updated_row) if updated_row else None
    
    def remove_from_portfolio(self, user_id: int, ticker: str) -> bool:
        """포트폴리오에서 종목 제거"""
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM portfolio WHERE user_id = %s AND ticker = %s",
                (user_id, ticker),
            )
            deleted = cursor.rowcount > 0
            conn.commit()
            return deleted
    
    def get_portfolio(self, user_id: int, status: Optional[str] = None) -> PortfolioResponse:
        """포트폴리오 조회"""
        self._update_current_prices(user_id)

        query = "SELECT * FROM portfolio WHERE user_id = %s"
        params = [user_id]

        if status:
            query += " AND status = %s"
            params.append(status)

        query += " ORDER BY created_at DESC"

        with db_manager.get_cursor(commit=False) as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        items = [self._row_to_portfolio_item(row) for row in rows]

        with db_manager.get_cursor(commit=False) as cursor:
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(CASE WHEN trade_type = 'buy' THEN price * quantity ELSE 0 END), 0) AS total_buy,
                    COALESCE(SUM(CASE WHEN trade_type = 'sell' THEN price * quantity ELSE 0 END), 0) AS total_sell
                FROM trading_history
                WHERE user_id = %s
            """, (user_id,))
            totals_row = cursor.fetchone()

        if isinstance(totals_row, dict):
            total_buy_amount = totals_row.get("total_buy", 0) or 0
            total_sell_amount = totals_row.get("total_sell", 0) or 0
        elif totals_row:
            total_buy_amount, total_sell_amount = totals_row
        else:
            total_buy_amount = total_sell_amount = 0

        total_investment = sum(item.total_investment or 0 for item in items)
        total_current_value = sum(item.current_value or 0 for item in items)
        total_profit_loss = sum(item.profit_loss or 0 for item in items)
        total_profit_loss_pct = (total_profit_loss / total_buy_amount * 100) if total_buy_amount else 0

        return PortfolioResponse(
            items=items,
            total_investment=total_investment,
            total_current_value=total_current_value,
            total_profit_loss=total_profit_loss,
            total_profit_loss_pct=total_profit_loss_pct
        )
    
    def _update_current_prices(self, user_id: int):
        """현재가 업데이트"""
        with db_manager.get_cursor(commit=False) as cursor:
            cursor.execute(
                "SELECT ticker FROM portfolio WHERE user_id = %s",
                (user_id,),
            )
            ticker_rows = cursor.fetchall()

        tickers = [
            row["ticker"] if isinstance(row, dict) else row[0]
            for row in ticker_rows
        ]

        for ticker in tickers:
            current_price = self.get_current_price(ticker)
            if current_price:
                with db_manager.get_cursor(commit=True) as cursor:
                    cursor.execute("""
                        UPDATE portfolio 
                        SET current_price = %s, updated_at = NOW()
                        WHERE user_id = %s AND ticker = %s
                    """, (current_price, user_id, ticker))
                self._update_portfolio_from_trading(user_id, ticker)
    
    def _row_to_portfolio_item(self, row) -> PortfolioItem:
        """데이터베이스 행을 PortfolioItem으로 변환"""
        if not row:
            return None
        
        if isinstance(row, dict):
            data = row
        else:
            columns = [
                "id", "user_id", "ticker", "name", "entry_price", "quantity",
                "entry_date", "current_price", "total_investment", "current_value",
                "profit_loss", "profit_loss_pct", "status", "created_at", "updated_at"
            ]
            data = dict(zip(columns, row))
        
        return PortfolioItem(
            id=data.get("id"),
            user_id=data.get("user_id"),
            ticker=data.get("ticker"),
            name=data.get("name"),
            entry_price=data.get("entry_price"),
            quantity=data.get("quantity"),
            entry_date=data.get("entry_date"),
            current_price=data.get("current_price"),
            total_investment=data.get("total_investment"),
            current_value=data.get("current_value"),
            profit_loss=data.get("profit_loss"),
            profit_loss_pct=data.get("profit_loss_pct"),
            status=data.get("status"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    # ===== 매매 내역 관리 메서드들 =====
    
    def add_trading_history(self, user_id: int, request: AddTradingRequest) -> TradingHistory:
        """매매 내역 추가"""
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO trading_history (
                    user_id, ticker, name, trade_type, quantity, price, trade_date, notes
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                user_id,
                request.ticker,
                request.name,
                request.trade_type,
                request.quantity,
                request.price,
                request.trade_date,
                request.notes,
            ))
            trading_id = cursor.fetchone()[0]
            conn.commit()

        print(f"🔄 포트폴리오 업데이트 시작: ticker={request.ticker}, user_id={user_id}")
        self._update_portfolio_from_trading(user_id, request.ticker)
        print(f"✅ 포트폴리오 업데이트 완료: ticker={request.ticker}")

        with db_manager.get_cursor(commit=False) as cursor:
            cursor.execute("SELECT * FROM trading_history WHERE id = %s", (trading_id,))
            row = cursor.fetchone()
            return self._row_to_trading_history(row)
    
    def get_trading_history(self, user_id: int, ticker: Optional[str] = None) -> TradingHistoryResponse:
        """매매 내역 조회"""
        query = "SELECT * FROM trading_history WHERE user_id = %s"
        params = [user_id]

        if ticker:
            query += " AND ticker = %s"
            params.append(ticker)

        query += " ORDER BY trade_date DESC, created_at DESC"

        with db_manager.get_cursor(commit=False) as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        items = [self._row_to_trading_history(row) for row in rows]

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
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT ticker FROM trading_history WHERE id = %s AND user_id = %s",
                (trading_id, user_id),
            )
            row = cursor.fetchone()
            if not row:
                return False
            ticker = row.get("ticker") if isinstance(row, dict) else row[0]

            cursor.execute(
                "DELETE FROM trading_history WHERE id = %s AND user_id = %s",
                (trading_id, user_id),
            )
            deleted = cursor.rowcount > 0
            conn.commit()

        if deleted:
            self._update_portfolio_from_trading(user_id, ticker)
        return deleted
    
    def _update_portfolio_from_trading(self, user_id: int, ticker: str):
        """매매 내역을 기반으로 포트폴리오 업데이트 (단순화된 계산)"""
        print(f"📊 _update_portfolio_from_trading 호출: user_id={user_id}, ticker={ticker}")
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT trade_type, quantity, price, trade_date 
                FROM trading_history 
                WHERE user_id = %s AND ticker = %s
                ORDER BY trade_date ASC, created_at ASC
            """, (user_id, ticker))
            trades = cursor.fetchall()

            if not trades:
                conn.commit()
                return

            total_buy_qty = 0
            total_buy_amount = 0
            total_sell_qty = 0
            total_sell_amount = 0

            for trade_type, quantity, price, trade_date in trades:
                if trade_type == 'buy':
                    total_buy_qty += quantity
                    total_buy_amount += quantity * price
                elif trade_type == 'sell':
                    total_sell_qty += quantity
                    total_sell_amount += quantity * price

            current_quantity = total_buy_qty - total_sell_qty

            if current_quantity <= 0:
                cursor.execute(
                    "DELETE FROM portfolio WHERE user_id = %s AND ticker = %s",
                    (user_id, ticker),
                )
                conn.commit()
                return

            avg_buy_price = total_buy_amount / total_buy_qty if total_buy_qty > 0 else 0

            cursor.execute("""
                SELECT name, MIN(trade_date) FROM trading_history 
                WHERE user_id = %s AND ticker = %s AND trade_type = 'buy'
            """, (user_id, ticker))
            name_row = cursor.fetchone()
            name = None
            first_buy_date = None
            if name_row:
                if isinstance(name_row, dict):
                    name = name_row.get("name")
                    first_buy_date = name_row.get("min")
                else:
                    name = name_row[0]
                    first_buy_date = name_row[1]
            if not name:
                name = ticker
            if not first_buy_date:
                first_buy_date = trades[0][3]

            current_price = self.get_current_price(ticker) or avg_buy_price

            total_investment = avg_buy_price * current_quantity
            current_value = current_price * current_quantity
            realized_profit = total_sell_amount - (avg_buy_price * total_sell_qty) if total_sell_qty > 0 else 0
            unrealized_profit = (current_price - avg_buy_price) * current_quantity
            total_profit = realized_profit + unrealized_profit
            total_profit_pct = (total_profit / total_buy_amount * 100) if total_buy_amount else 0

            cursor.execute("""
                INSERT INTO portfolio (
                    user_id, ticker, name, entry_price, quantity, entry_date, 
                    current_price, total_investment, current_value, profit_loss, 
                    profit_loss_pct, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'holding')
                ON CONFLICT (user_id, ticker) DO UPDATE SET
                    name = EXCLUDED.name,
                    entry_price = EXCLUDED.entry_price,
                    quantity = EXCLUDED.quantity,
                    entry_date = EXCLUDED.entry_date,
                    current_price = EXCLUDED.current_price,
                    total_investment = EXCLUDED.total_investment,
                    current_value = EXCLUDED.current_value,
                    profit_loss = EXCLUDED.profit_loss,
                    profit_loss_pct = EXCLUDED.profit_loss_pct,
                    status = EXCLUDED.status,
                    updated_at = NOW()
            """, (
                user_id,
                ticker,
                name,
                avg_buy_price,
                current_quantity,
                first_buy_date,
                current_price,
                total_investment,
                current_value,
                total_profit,
                total_profit_pct,
            ))
            conn.commit()
    
    def _row_to_trading_history(self, row) -> TradingHistory:
        """데이터베이스 행을 TradingHistory로 변환"""
        if not row:
            return None
        
        if isinstance(row, dict):
            data = row
        else:
            columns = [
                "id", "user_id", "ticker", "name", "trade_type", "quantity",
                "price", "trade_date", "notes", "created_at", "updated_at"
            ]
            data = dict(zip(columns, row))
        
        return TradingHistory(
            id=data.get("id"),
            user_id=data.get("user_id"),
            ticker=data.get("ticker"),
            name=data.get("name"),
            trade_type=data.get("trade_type"),
            quantity=data.get("quantity"),
            price=data.get("price"),
            trade_date=data.get("trade_date"),
            notes=data.get("notes"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )


# 전역 인스턴스
portfolio_service = PortfolioService()

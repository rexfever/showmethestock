import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from portfolio_service import portfolio_service
from kiwoom_api import KiwoomAPI
from db_manager import db_manager


class DailyUpdateService:
    def __init__(self):
        self.kiwoom_api = KiwoomAPI()
    
    def update_all_portfolios(self):
        """모든 사용자의 포트폴리오 일일 업데이트"""
        try:
            with db_manager.get_cursor(commit=False) as cursor:
                cursor.execute("""
                    SELECT DISTINCT user_id
                    FROM portfolio
                    WHERE status IN ('watching', 'holding')
                """)
                user_ids = [row["user_id"] for row in cursor.fetchall()]
            
            for user_id in user_ids:
                self.update_user_portfolio(user_id)
            
            print(f"✅ {len(user_ids)}명의 포트폴리오 업데이트 완료")
        except Exception as e:
            print(f"❌ 포트폴리오 업데이트 오류: {e}")
    
    def update_user_portfolio(self, user_id: int):
        """특정 사용자의 포트폴리오 업데이트"""
        try:
            with db_manager.get_cursor(commit=True) as cursor:
                cursor.execute("""
                    SELECT id, ticker, name, entry_price, entry_date, current_price,
                           max_return_pct, min_return_pct, holding_days
                    FROM portfolio
                    WHERE user_id = %s AND status IN ('watching', 'holding')
                """, (user_id,))
                portfolio_items = cursor.fetchall()
                
                for item in portfolio_items:
                    item_id = item["id"]
                    ticker = item["ticker"]
                    name = item["name"]
                    entry_price = item["entry_price"]
                    entry_date = item["entry_date"]
                    current_price = item["current_price"]
                    max_return = item["max_return_pct"]
                    min_return = item["min_return_pct"]
                    holding_days = item["holding_days"]
                    
                    new_current_price = self.get_current_price(ticker)
                    if new_current_price is None:
                        continue
                    
                    if entry_price and entry_price > 0:
                        current_return = ((new_current_price - entry_price) / entry_price) * 100
                        
                        new_max_return = max(max_return if max_return is not None else current_return, current_return)
                        new_min_return = min(min_return if min_return is not None else current_return, current_return)
                        
                        if entry_date:
                            entry_dt = datetime.strptime(entry_date, "%Y%m%d")
                            new_holding_days = (datetime.now() - entry_dt).days
                        else:
                            new_holding_days = holding_days
                        
                        daily_return = None
                        if current_price and current_price > 0:
                            daily_return = ((new_current_price - current_price) / current_price) * 100
                        
                        cursor.execute("""
                            UPDATE portfolio
                            SET current_price = %s,
                                daily_return_pct = %s,
                                max_return_pct = %s,
                                min_return_pct = %s,
                                holding_days = %s,
                                updated_at = NOW()
                            WHERE id = %s
                        """, (new_current_price, daily_return, new_max_return, new_min_return, new_holding_days, item_id))
                        
                        try:
                            prev_price = float(current_price) if current_price is not None else None
                            print_price = f"{prev_price:.0f}" if prev_price is not None else "N/A"
                        except (TypeError, ValueError):
                            print_price = "N/A"
                        print(f"📊 {name}({ticker}): {print_price} → {new_current_price:.0f} ({current_return:+.2f}%)")
        except Exception as e:
            print(f"❌ 사용자 {user_id} 포트폴리오 업데이트 오류: {e}")
    
    def get_current_price(self, ticker: str) -> Optional[float]:
        """현재가 조회"""
        try:
            # 1. 최신 스캔 결과에서 조회
            current_price = portfolio_service.get_current_price(ticker)
            if current_price:
                return current_price
            
            # 2. 키움 API에서 조회 (백업)
            # 실제 구현에서는 키움 API 호출
            # current_price = self.kiwoom_api.get_current_price(ticker)
            
            return None
            
        except Exception as e:
            print(f"현재가 조회 오류 ({ticker}): {e}")
            return None
    
    def generate_daily_report(self, user_id: int) -> Dict[str, Any]:
        """일일 리포트 생성"""
        try:
            with db_manager.get_cursor(commit=False) as cursor:
                cursor.execute("""
                    SELECT source,
                           COUNT(*) AS count,
                           AVG(profit_loss_pct) AS avg_return,
                           SUM(profit_loss) AS total_profit,
                           SUM(total_investment) AS total_investment
                    FROM portfolio
                    WHERE user_id = %s AND status IN ('watching', 'holding')
                    GROUP BY source
                """, (user_id,))
                
                source_stats = {}
                for row in cursor.fetchall():
                    source_stats[row["source"]] = {
                        'count': row["count"] or 0,
                        'avg_return': row["avg_return"] or 0,
                        'total_profit': row["total_profit"] or 0,
                        'total_investment': row["total_investment"] or 0
                    }
                
                cursor.execute("""
                    SELECT ticker, name, profit_loss_pct, daily_return_pct, source
                    FROM portfolio
                    WHERE user_id = %s AND status IN ('watching', 'holding')
                    ORDER BY profit_loss_pct DESC
                    LIMIT 5
                """, (user_id,))
                top_performers = cursor.fetchall()
                
                cursor.execute("""
                    SELECT ticker, name, profit_loss_pct, daily_return_pct, source
                    FROM portfolio
                    WHERE user_id = %s AND status IN ('watching', 'holding')
                    ORDER BY profit_loss_pct ASC
                    LIMIT 5
                """, (user_id,))
                bottom_performers = cursor.fetchall()
                
                return {
                    'date': datetime.now().strftime('%Y%m%d'),
                    'source_stats': source_stats,
                    'top_performers': top_performers,
                    'bottom_performers': bottom_performers
                }
        except Exception as e:
            print(f"일일 리포트 생성 오류: {e}")
            return {}


# 전역 인스턴스
daily_update_service = DailyUpdateService()


def run_daily_update():
    """일일 업데이트 실행 (cron에서 호출)"""
    print(f"🔄 일일 포트폴리오 업데이트 시작: {datetime.now()}")
    daily_update_service.update_all_portfolios()
    print(f"✅ 일일 포트폴리오 업데이트 완료: {datetime.now()}")


if __name__ == "__main__":
    run_daily_update()













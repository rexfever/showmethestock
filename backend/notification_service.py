import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from daily_update_service import daily_update_service


class NotificationService:
    def __init__(self, db_path: str = "portfolio.db"):
        self.db_path = db_path
    
    def send_daily_portfolio_report(self):
        """일일 포트폴리오 리포트 전송"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 모든 활성 사용자 조회
                cursor.execute("""
                    SELECT DISTINCT user_id FROM portfolio 
                    WHERE status IN ('watching', 'holding')
                """)
                user_ids = [row[0] for row in cursor.fetchall()]
                
                for user_id in user_ids:
                    self.send_user_daily_report(user_id)
                    
                print(f"✅ {len(user_ids)}명에게 일일 리포트 전송 완료")
                
        except Exception as e:
            print(f"❌ 일일 리포트 전송 오류: {e}")
    
    def send_user_daily_report(self, user_id: int):
        """특정 사용자에게 일일 리포트 전송"""
        try:
            # 일일 리포트 생성
            report = daily_update_service.generate_daily_report(user_id)
            
            if not report:
                return
            
            # 리포트 내용 구성
            message = self._format_daily_report(report)
            
            # 실제 구현에서는 이메일, 푸시 알림, 카카오톡 등으로 전송
            print(f"📧 사용자 {user_id} 일일 리포트:")
            print(message)
            
            # 리포트 저장 (선택사항)
            self._save_daily_report(user_id, report)
            
        except Exception as e:
            print(f"❌ 사용자 {user_id} 리포트 전송 오류: {e}")
    
    def _format_daily_report(self, report: Dict[str, Any]) -> str:
        """일일 리포트 포맷팅"""
        date = report.get('date', datetime.now().strftime('%Y-%m-%d'))
        source_stats = report.get('source_stats', {})
        top_performers = report.get('top_performers', [])
        bottom_performers = report.get('bottom_performers', [])
        
        message = f"📊 {date} 포트폴리오 리포트\n\n"
        
        # 추천종목 vs 개인종목 성과
        recommended_stats = source_stats.get('recommended', {})
        personal_stats = source_stats.get('personal', {})
        
        message += "🎯 성과 비교\n"
        if recommended_stats:
            message += f"• 추천종목: {recommended_stats['count']}개, 평균 수익률 {recommended_stats['avg_return']:.2f}%\n"
        if personal_stats:
            message += f"• 개인종목: {personal_stats['count']}개, 평균 수익률 {personal_stats['avg_return']:.2f}%\n"
        
        message += "\n📈 상위 성과 종목\n"
        for i, (ticker, name, profit_pct, daily_pct, source) in enumerate(top_performers[:3], 1):
            source_emoji = "🎯" if source == "recommended" else "👤"
            message += f"{i}. {source_emoji} {name}({ticker}): {profit_pct:.2f}% (일일: {daily_pct:.2f}%)\n"
        
        message += "\n📉 하위 성과 종목\n"
        for i, (ticker, name, profit_pct, daily_pct, source) in enumerate(bottom_performers[:3], 1):
            source_emoji = "🎯" if source == "recommended" else "👤"
            message += f"{i}. {source_emoji} {name}({ticker}): {profit_pct:.2f}% (일일: {daily_pct:.2f}%)\n"
        
        message += "\n💡 투자 조언: 꾸준한 관찰과 분산투자를 통해 리스크를 관리하세요."
        
        return message
    
    def _save_daily_report(self, user_id: int, report: Dict[str, Any]):
        """일일 리포트 저장"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 리포트 테이블 생성 (없는 경우)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS daily_reports (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        report_date TEXT NOT NULL,
                        report_data TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # 리포트 저장
                cursor.execute("""
                    INSERT INTO daily_reports (user_id, report_date, report_data)
                    VALUES (?, ?, ?)
                """, (user_id, report.get('date'), json.dumps(report)))
                
                conn.commit()
                
        except Exception as e:
            print(f"일일 리포트 저장 오류: {e}")
    
    def get_user_reports(self, user_id: int, days: int = 7) -> List[Dict[str, Any]]:
        """사용자의 최근 리포트 조회"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT report_date, report_data, created_at
                    FROM daily_reports 
                    WHERE user_id = ? 
                    ORDER BY report_date DESC 
                    LIMIT ?
                """, (user_id, days))
                
                reports = []
                for row in cursor.fetchall():
                    report_date, report_data, created_at = row
                    reports.append({
                        'date': report_date,
                        'data': json.loads(report_data),
                        'created_at': created_at
                    })
                
                return reports
                
        except Exception as e:
            print(f"사용자 리포트 조회 오류: {e}")
            return []


# 전역 인스턴스
notification_service = NotificationService()


def send_daily_notifications():
    """일일 알림 전송 (cron에서 호출)"""
    print(f"📧 일일 포트폴리오 알림 전송 시작: {datetime.now()}")
    notification_service.send_daily_portfolio_report()
    print(f"✅ 일일 포트폴리오 알림 전송 완료: {datetime.now()}")


if __name__ == "__main__":
    send_daily_notifications()








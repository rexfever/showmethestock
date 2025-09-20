import smtplib
import random
import string
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import sqlite3
import os
from typing import Optional

class EmailService:
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.from_email = os.getenv("FROM_EMAIL", "noreply@sohntech.ai.kr")
        
    def generate_verification_code(self) -> str:
        """6자리 인증 코드 생성"""
        return ''.join(random.choices(string.digits, k=6))
    
    def send_verification_email(self, email: str, verification_code: str) -> bool:
        """인증 이메일 발송"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = email
            msg['Subject'] = "Stock Insight 이메일 인증"
            
            body = f"""
안녕하세요, Stock Insight입니다.

회원가입을 위한 이메일 인증 코드입니다.

인증 코드: {verification_code}

이 코드는 10분간 유효합니다.
인증 코드를 입력하여 회원가입을 완료해주세요.

감사합니다.
Stock Insight 팀
            """
            
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            text = msg.as_string()
            server.sendmail(self.from_email, email, text)
            server.quit()
            
            return True
        except Exception as e:
            print(f"이메일 발송 실패: {e}")
            return False
    
    def send_password_reset_email(self, email: str, verification_code: str) -> bool:
        """비밀번호 재설정 이메일 발송"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = email
            msg['Subject'] = "Stock Insight 비밀번호 재설정"
            
            body = f"""
안녕하세요, Stock Insight입니다.

비밀번호 재설정을 위한 인증 코드입니다.

인증 코드: {verification_code}

이 코드는 10분간 유효합니다.
인증 코드를 입력하여 비밀번호를 재설정해주세요.

감사합니다.
Stock Insight 팀
            """
            
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            text = msg.as_string()
            server.sendmail(self.from_email, email, text)
            server.quit()
            
            return True
        except Exception as e:
            print(f"이메일 발송 실패: {e}")
            return False

class EmailVerificationService:
    def __init__(self):
        self.db_path = "email_verifications.db"
        self.init_db()
    
    def init_db(self):
        """이메일 인증 데이터베이스 초기화"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS email_verifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                verification_code TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                is_verified BOOLEAN DEFAULT FALSE,
                verification_type TEXT DEFAULT 'signup'  -- 'signup' or 'password_reset'
            )
        ''')
        conn.commit()
        conn.close()
    
    def store_verification_code(self, email: str, verification_code: str, verification_type: str = 'signup') -> bool:
        """인증 코드 저장"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 기존 인증 코드 삭제
            cursor.execute('DELETE FROM email_verifications WHERE email = ? AND verification_type = ?', 
                         (email, verification_type))
            
            # 새 인증 코드 저장 (10분 유효)
            expires_at = datetime.now() + timedelta(minutes=10)
            cursor.execute('''
                INSERT INTO email_verifications (email, verification_code, expires_at, verification_type)
                VALUES (?, ?, ?, ?)
            ''', (email, verification_code, expires_at, verification_type))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"인증 코드 저장 실패: {e}")
            return False
    
    def verify_code(self, email: str, verification_code: str, verification_type: str = 'signup') -> bool:
        """인증 코드 검증"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id FROM email_verifications 
                WHERE email = ? AND verification_code = ? AND verification_type = ?
                AND expires_at > ? AND is_verified = FALSE
            ''', (email, verification_code, verification_type, datetime.now()))
            
            result = cursor.fetchone()
            
            if result:
                # 인증 완료 처리
                cursor.execute('UPDATE email_verifications SET is_verified = TRUE WHERE id = ?', (result[0],))
                conn.commit()
                conn.close()
                return True
            else:
                conn.close()
                return False
                
        except Exception as e:
            print(f"인증 코드 검증 실패: {e}")
            return False
    
    def cleanup_expired_codes(self):
        """만료된 인증 코드 정리"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM email_verifications WHERE expires_at < ?', (datetime.now(),))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"만료된 코드 정리 실패: {e}")

# 전역 인스턴스
email_service = EmailService()
email_verification_service = EmailVerificationService()

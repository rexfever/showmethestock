"""
접속 기록 서비스
"""
import logging
from datetime import datetime
from typing import Optional
from db_manager import db_manager

logger = logging.getLogger(__name__)


def init_access_logs_table():
    """접속 기록 테이블 초기화"""
    with db_manager.get_cursor(commit=False) as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS access_logs (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT,
                email TEXT,
                ip_address TEXT,
                user_agent TEXT,
                request_path TEXT,
                request_method TEXT,
                status_code INTEGER,
                response_time_ms INTEGER,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
            )
        """)
        
        # 인덱스 생성
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_access_logs_user_id ON access_logs(user_id)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_access_logs_created_at ON access_logs(created_at)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_access_logs_ip_address ON access_logs(ip_address)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_access_logs_request_path ON access_logs(request_path)
        """)


def log_access(
    user_id: Optional[int] = None,
    email: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    request_path: Optional[str] = None,
    request_method: Optional[str] = None,
    status_code: Optional[int] = None,
    response_time_ms: Optional[int] = None
):
    """
    접속 기록 저장
    
    Args:
        user_id: 사용자 ID (로그인한 경우)
        email: 사용자 이메일 (로그인한 경우)
        ip_address: IP 주소
        user_agent: User-Agent 헤더
        request_path: 요청 경로
        request_method: HTTP 메서드
        status_code: HTTP 상태 코드
        response_time_ms: 응답 시간 (밀리초)
    """
    try:
        with db_manager.get_cursor(commit=True) as cur:
            cur.execute("""
                INSERT INTO access_logs (
                    user_id, email, ip_address, user_agent, 
                    request_path, request_method, status_code, response_time_ms
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                user_id,
                email,
                ip_address,
                user_agent,
                request_path,
                request_method,
                status_code,
                response_time_ms
            ))
    except Exception as e:
        # 접속 기록 실패는 로그만 남기고 요청 처리는 계속
        logger.error(f"접속 기록 저장 실패: {e}")


def get_access_logs(
    user_id: Optional[int] = None,
    email: Optional[str] = None,
    ip_address: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100
) -> list:
    """
    접속 기록 조회
    
    Args:
        user_id: 사용자 ID로 필터링
        email: 이메일로 필터링
        ip_address: IP 주소로 필터링
        start_date: 시작 날짜
        end_date: 종료 날짜
        limit: 최대 조회 개수
    
    Returns:
        접속 기록 리스트
    """
    try:
        with db_manager.get_cursor(commit=False) as cur:
            conditions = []
            params = []
            
            if user_id:
                conditions.append("user_id = %s")
                params.append(user_id)
            
            if email:
                conditions.append("email = %s")
                params.append(email)
            
            if ip_address:
                conditions.append("ip_address = %s")
                params.append(ip_address)
            
            if start_date:
                conditions.append("created_at >= %s")
                params.append(start_date)
            
            if end_date:
                conditions.append("created_at <= %s")
                params.append(end_date)
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            cur.execute(f"""
                SELECT 
                    id, user_id, email, ip_address, user_agent,
                    request_path, request_method, status_code, 
                    response_time_ms, created_at
                FROM access_logs
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT %s
            """, params + [limit])
            
            rows = cur.fetchall()
            
            return [
                {
                    'id': row[0],
                    'user_id': row[1],
                    'email': row[2],
                    'ip_address': row[3],
                    'user_agent': row[4],
                    'request_path': row[5],
                    'request_method': row[6],
                    'status_code': row[7],
                    'response_time_ms': row[8],
                    'created_at': row[9].isoformat() if row[9] else None
                }
                for row in rows
            ]
    except Exception as e:
        logger.error(f"접속 기록 조회 실패: {e}")
        return []


def get_daily_visitor_stats_by_path(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> list:
    """
    화면별 일 방문자 수 집계
    
    Args:
        start_date: 시작 날짜
        end_date: 종료 날짜
    
    Returns:
        화면별 일 방문자 수 리스트
        [
            {
                'date': '2025-12-01',
                'path': '/v2/scanner-v2',
                'unique_visitors': 10,
                'total_visits': 25
            },
            ...
        ]
    """
    try:
        with db_manager.get_cursor(commit=False) as cur:
            conditions = []
            params = []
            
            if start_date:
                conditions.append("DATE(created_at) >= %s")
                params.append(start_date.date())
            
            if end_date:
                conditions.append("DATE(created_at) <= %s")
                params.append(end_date.date())
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            # 사용자가 볼 수 있는 화면만 포함: 미국주식추천, 한국주식추천, 종목분석, 나의투자종목, 더보기
            include_paths = [
                '/v2/us-stocks-scanner',  # 미국주식추천
                '/v2/scanner-v2',         # 한국주식추천 (V2)
                '/customer-scanner',      # 한국주식추천 (V1)
                '/stock-analysis',        # 종목분석
                '/portfolio',             # 나의투자종목
                '/my-stocks',             # 나의투자종목 (대체 경로)
                '/more'                   # 더보기
            ]
            
            # 정적 파일이나 헬스 체크는 제외
            exclude_paths = ["/static/", "/_next/", "/favicon.ico", "/health", "/api/"]
            
            # 포함할 경로 조건 (IN 절 사용)
            include_placeholders = ",".join(["%s" for _ in include_paths])
            include_conditions = f"request_path IN ({include_placeholders})"
            params.extend(include_paths)
            
            # 제외할 경로 조건
            exclude_conditions = " AND ".join([f"request_path NOT LIKE %s" for _ in exclude_paths])
            params.extend([f"%{path}%" for path in exclude_paths])
            
            # 화면별 일 방문자 수 집계
            # 같은 날짜, 같은 경로에서 user_id가 있으면 user_id 기준, 없으면 ip_address + user_agent 조합 기준으로 중복 제거
            cur.execute(f"""
                SELECT 
                    DATE(created_at) as date,
                    request_path as path,
                    COUNT(DISTINCT CASE 
                        WHEN user_id IS NOT NULL THEN user_id::text
                        ELSE COALESCE(ip_address, '') || '|' || COALESCE(user_agent, '')
                    END) as unique_visitors,
                    COUNT(*) as total_visits
                FROM access_logs
                WHERE {where_clause} 
                    AND ({include_conditions})
                    AND {exclude_conditions}
                    AND request_path IS NOT NULL
                    AND request_path != ''
                GROUP BY DATE(created_at), request_path
                ORDER BY date DESC, unique_visitors DESC
            """, params)
            
            rows = cur.fetchall()
            
            return [
                {
                    'date': row[0].strftime('%Y-%m-%d') if hasattr(row[0], 'strftime') else str(row[0]),
                    'path': row[1],
                    'unique_visitors': row[2],
                    'total_visits': row[3]
                }
                for row in rows
            ]
    except Exception as e:
        import traceback
        logger.error(f"화면별 일 방문자 수 집계 실패: {e}\n{traceback.format_exc()}")
        return []


def get_daily_visitor_stats(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> list:
    """
    일별 방문자 수 집계
    
    Args:
        start_date: 시작 날짜
        end_date: 종료 날짜
    
    Returns:
        일별 방문자 수 리스트
        [
            {
                'date': '2025-12-01',
                'unique_visitors': 10,
                'total_visits': 25
            },
            ...
        ]
    """
    try:
        with db_manager.get_cursor(commit=False) as cur:
            conditions = []
            params = []
            
            if start_date:
                conditions.append("DATE(created_at) >= %s")
                params.append(start_date.date())
            
            if end_date:
                conditions.append("DATE(created_at) <= %s")
                params.append(end_date.date())
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            # 사용자가 볼 수 있는 화면만 포함: 미국주식추천, 한국주식추천, 종목분석, 나의투자종목, 더보기
            include_paths = [
                '/v2/us-stocks-scanner',  # 미국주식추천
                '/v2/scanner-v2',         # 한국주식추천 (V2)
                '/customer-scanner',      # 한국주식추천 (V1)
                '/stock-analysis',        # 종목분석
                '/portfolio',             # 나의투자종목
                '/my-stocks',             # 나의투자종목 (대체 경로)
                '/more'                   # 더보기
            ]
            
            # 정적 파일이나 헬스 체크는 제외
            exclude_paths = ["/static/", "/_next/", "/favicon.ico", "/health", "/api/"]
            
            # 포함할 경로 조건 (IN 절 사용)
            include_placeholders = ",".join(["%s" for _ in include_paths])
            include_conditions = f"request_path IN ({include_placeholders})"
            params.extend(include_paths)
            
            # 제외할 경로 조건
            exclude_conditions = " AND ".join([f"request_path NOT LIKE %s" for _ in exclude_paths])
            params.extend([f"%{path}%" for path in exclude_paths])
            
            # 일별 방문자 수 집계
            # 고유 방문자: user_id가 있으면 user_id 기준, 없으면 ip_address + user_agent 조합 기준
            # 총 방문 횟수: 실제 페이지 방문만 카운트 (API 호출 제외)
            cur.execute(f"""
                SELECT 
                    DATE(created_at) as date,
                    COUNT(DISTINCT CASE 
                        WHEN user_id IS NOT NULL THEN user_id::text
                        ELSE COALESCE(ip_address, '') || '|' || COALESCE(user_agent, '')
                    END) as unique_visitors,
                    COUNT(*) as total_visits
                FROM access_logs
                WHERE {where_clause} 
                    AND ({include_conditions})
                    AND {exclude_conditions}
                    AND request_path IS NOT NULL
                    AND request_path != ''
                GROUP BY DATE(created_at)
                ORDER BY date DESC
            """, params)
            
            rows = cur.fetchall()
            print(f"[DEBUG] 쿼리 결과: {len(rows)}개 행")
            logger.info(f"쿼리 결과: {len(rows)}개 행")
            
            result = [
                {
                    'date': row[0].strftime('%Y-%m-%d') if hasattr(row[0], 'strftime') else str(row[0]),
                    'unique_visitors': row[1],
                    'total_visits': row[2]
                }
                for row in rows
            ]
            print(f"[DEBUG] 결과 반환: {result}")
            logger.info(f"결과 반환: {result}")
            return result
    except Exception as e:
        import traceback
        error_msg = f"일별 방문자 수 집계 실패: {e}\n{traceback.format_exc()}"
        print(f"[ERROR] {error_msg}")
        logger.error(error_msg)
        return []


def get_cumulative_visitor_stats(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> dict:
    """
    누적 방문자 수 집계
    
    Args:
        start_date: 시작 날짜 (누적 시작일)
        end_date: 종료 날짜 (누적 종료일)
    
    Returns:
        누적 방문자 수 딕셔너리
        {
            'start_date': '2025-12-01',
            'end_date': '2025-12-31',
            'total_unique_visitors': 100,
            'total_visits': 500
        }
    """
    try:
        with db_manager.get_cursor(commit=False) as cur:
            conditions = []
            params = []
            
            if start_date:
                conditions.append("DATE(created_at) >= %s")
                params.append(start_date.date())
            
            if end_date:
                conditions.append("DATE(created_at) <= %s")
                params.append(end_date.date())
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            # 사용자가 볼 수 있는 화면만 포함: 미국주식추천, 한국주식추천, 종목분석, 나의투자종목, 더보기
            include_paths = [
                '/v2/us-stocks-scanner',  # 미국주식추천
                '/v2/scanner-v2',         # 한국주식추천 (V2)
                '/customer-scanner',      # 한국주식추천 (V1)
                '/stock-analysis',        # 종목분석
                '/portfolio',             # 나의투자종목
                '/my-stocks',             # 나의투자종목 (대체 경로)
                '/more'                   # 더보기
            ]
            
            # 정적 파일이나 헬스 체크는 제외
            exclude_paths = ["/static/", "/_next/", "/favicon.ico", "/health", "/api/"]
            
            # 포함할 경로 조건 (IN 절 사용)
            include_placeholders = ",".join(["%s" for _ in include_paths])
            include_conditions = f"request_path IN ({include_placeholders})"
            params.extend(include_paths)
            
            # 제외할 경로 조건
            exclude_conditions = " AND ".join([f"request_path NOT LIKE %s" for _ in exclude_paths])
            params.extend([f"%{path}%" for path in exclude_paths])
            
            # 누적 방문자 수 집계
            # 고유 방문자: user_id가 있으면 user_id 기준, 없으면 ip_address + user_agent 조합 기준
            # 총 방문 횟수: 실제 페이지 방문만 카운트 (API 호출 제외)
            cur.execute(f"""
                SELECT 
                    COUNT(DISTINCT CASE 
                        WHEN user_id IS NOT NULL THEN user_id::text
                        ELSE COALESCE(ip_address, '') || '|' || COALESCE(user_agent, '')
                    END) as total_unique_visitors,
                    COUNT(*) as total_visits,
                    MIN(DATE(created_at)) as first_date,
                    MAX(DATE(created_at)) as last_date
                FROM access_logs
                WHERE {where_clause} 
                    AND ({include_conditions})
                    AND {exclude_conditions}
                    AND request_path IS NOT NULL
                    AND request_path != ''
            """, params)
            
            row = cur.fetchone()
            
            if row:
                return {
                    'start_date': row[2].strftime('%Y-%m-%d') if row[2] and hasattr(row[2], 'strftime') else (start_date.date().strftime('%Y-%m-%d') if start_date else None),
                    'end_date': row[3].strftime('%Y-%m-%d') if row[3] and hasattr(row[3], 'strftime') else (end_date.date().strftime('%Y-%m-%d') if end_date else None),
                    'total_unique_visitors': row[0] or 0,
                    'total_visits': row[1] or 0
                }
            else:
                return {
                    'start_date': start_date.date().strftime('%Y-%m-%d') if start_date else None,
                    'end_date': end_date.date().strftime('%Y-%m-%d') if end_date else None,
                    'total_unique_visitors': 0,
                    'total_visits': 0
                }
    except Exception as e:
        logger.error(f"누적 방문자 수 집계 실패: {e}")
        return {
            'start_date': None,
            'end_date': None,
            'total_unique_visitors': 0,
            'total_visits': 0
        }


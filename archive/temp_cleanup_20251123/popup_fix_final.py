#!/usr/bin/env python3
"""
팝업 공지 날짜 파싱 최종 수정

문제: 데이터베이스에서 반환되는 timestamp 객체 처리
해결: datetime 객체와 문자열을 모두 처리할 수 있도록 수정
"""

import sys
import os

def fix_popup_notice_final():
    """main.py의 팝업 공지 날짜 파싱 로직을 최종 수정합니다."""
    
    # 백엔드 디렉토리 경로
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    main_py_path = os.path.join(backend_dir, "main.py")
    
    if not os.path.exists(main_py_path):
        print(f"❌ main.py 파일을 찾을 수 없습니다: {main_py_path}")
        return False
    
    # 백업 생성
    backup_path = f"{main_py_path}.backup.popup_fix_final"
    with open(main_py_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ 백업 생성: {backup_path}")
    
    # 기존 코드 찾기
    old_code = '''            # 날짜 범위 확인
            if is_enabled and start_date and end_date:
                from datetime import datetime
                import pytz
                try:
                    # timestamp 형식 파싱 시도
                    if isinstance(start_date, str) and len(start_date) > 10:
                        # "2025-11-15 00:00:00+09" 형식
                        start_dt = datetime.fromisoformat(start_date.replace('+09', '+09:00'))
                        end_dt = datetime.fromisoformat(end_date.replace('+09', '+09:00'))
                        # 시간대 인식 datetime이므로 현재 시간도 KST로 맞춤
                        kst = pytz.timezone('Asia/Seoul')
                        now = datetime.now(kst)
                    else:
                        # YYYYMMDD 형식 (기존 호환성) - naive datetime
                        start_dt = datetime.strptime(str(start_date), "%Y%m%d")
                        end_dt = datetime.strptime(str(end_date), "%Y%m%d")
                        now = datetime.now()
                    
                    # 날짜만 비교 (시간 무시)
                    start_date_only = start_dt.date()
                    end_date_only = end_dt.date()
                    now_date_only = now.date()
                    
                    if now_date_only < start_date_only or now_date_only > end_date_only:
                        is_enabled = False
                        
                    print(f"📅 팝업 공지 날짜 확인: {now_date_only} in [{start_date_only}, {end_date_only}] = {is_enabled}")
                        
                except (ValueError, TypeError) as e:
                    print(f"⚠️ 팝업 공지 날짜 파싱 오류: {e}")
                    is_enabled = False'''
    
    # 새로운 코드
    new_code = '''            # 날짜 범위 확인
            if is_enabled and start_date and end_date:
                from datetime import datetime
                import pytz
                try:
                    # 현재 날짜 (KST)
                    kst = pytz.timezone('Asia/Seoul')
                    now_date = datetime.now(kst).date()
                    
                    # start_date와 end_date 처리
                    if hasattr(start_date, 'date'):
                        # datetime 객체인 경우
                        start_date_only = start_date.date()
                        end_date_only = end_date.date()
                    elif isinstance(start_date, str):
                        if len(start_date) > 10:
                            # "2025-11-15 00:00:00+09:00" 형식
                            start_dt = datetime.fromisoformat(start_date.replace('+09', '+09:00'))
                            end_dt = datetime.fromisoformat(end_date.replace('+09', '+09:00'))
                            start_date_only = start_dt.date()
                            end_date_only = end_dt.date()
                        else:
                            # YYYYMMDD 형식
                            start_dt = datetime.strptime(str(start_date), "%Y%m%d")
                            end_dt = datetime.strptime(str(end_date), "%Y%m%d")
                            start_date_only = start_dt.date()
                            end_date_only = end_dt.date()
                    else:
                        # 기타 형식
                        start_date_only = datetime.strptime(str(start_date), "%Y%m%d").date()
                        end_date_only = datetime.strptime(str(end_date), "%Y%m%d").date()
                    
                    # 날짜 범위 확인
                    if now_date < start_date_only or now_date > end_date_only:
                        is_enabled = False
                        
                    print(f"📅 팝업 공지 날짜 확인: {now_date} in [{start_date_only}, {end_date_only}] = {is_enabled}")
                        
                except (ValueError, TypeError) as e:
                    print(f"⚠️ 팝업 공지 날짜 파싱 오류: {e}, start_date={start_date}, end_date={end_date}")
                    is_enabled = False'''
    
    # 코드 교체
    if old_code in content:
        new_content = content.replace(old_code, new_code)
        
        with open(main_py_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print("✅ 팝업 공지 날짜 파싱 로직이 최종 수정되었습니다.")
        print("📝 변경 사항:")
        print("  - datetime 객체 직접 처리 추가")
        print("  - 문자열과 객체 모두 지원")
        print("  - 더 상세한 디버그 로그")
        return True
    else:
        print("❌ 수정할 코드를 찾을 수 없습니다. 코드가 이미 변경되었을 수 있습니다.")
        return False

if __name__ == "__main__":
    print("🔧 팝업 공지 날짜 파싱 최종 수정 시작...")
    success = fix_popup_notice_final()
    
    if success:
        print("\n✅ 수정 완료! 서버를 재시작하면 팝업 공지가 정상 작동합니다.")
        print("🔄 서버 재시작 명령어:")
        print("   sudo systemctl restart stock-finder-backend")
    else:
        print("\n❌ 수정 실패. 수동으로 코드를 확인해주세요.")
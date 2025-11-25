#!/usr/bin/env python3
"""
팝업 공지 날짜 비교 로직 추가 수정

문제: 시간대 인식 datetime과 naive datetime 비교 오류
해결: 시간대를 통일하여 비교
"""

import sys
import os

def fix_popup_notice_comparison():
    """main.py의 팝업 공지 날짜 비교 로직을 추가 수정합니다."""
    
    # 백엔드 디렉토리 경로
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    main_py_path = os.path.join(backend_dir, "main.py")
    
    if not os.path.exists(main_py_path):
        print(f"❌ main.py 파일을 찾을 수 없습니다: {main_py_path}")
        return False
    
    # 백업 생성
    backup_path = f"{main_py_path}.backup.popup_fix_v2"
    with open(main_py_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ 백업 생성: {backup_path}")
    
    # 기존 코드 찾기
    old_code = '''            # 날짜 범위 확인
            if is_enabled and start_date and end_date:
                from datetime import datetime
                try:
                    # timestamp 형식 파싱 시도
                    if isinstance(start_date, str) and len(start_date) > 10:
                        # "2025-11-15 00:00:00+09" 형식
                        start_dt = datetime.fromisoformat(start_date.replace('+09', '+09:00'))
                        end_dt = datetime.fromisoformat(end_date.replace('+09', '+09:00'))
                    else:
                        # YYYYMMDD 형식 (기존 호환성)
                        start_dt = datetime.strptime(str(start_date), "%Y%m%d")
                        end_dt = datetime.strptime(str(end_date), "%Y%m%d")
                    
                    now = datetime.now()
                    
                    if now < start_dt or now > end_dt:
                        is_enabled = False
                except (ValueError, TypeError) as e:
                    print(f"⚠️ 팝업 공지 날짜 파싱 오류: {e}")
                    is_enabled = False'''
    
    # 새로운 코드
    new_code = '''            # 날짜 범위 확인
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
    
    # 코드 교체
    if old_code in content:
        new_content = content.replace(old_code, new_code)
        
        with open(main_py_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print("✅ 팝업 공지 날짜 비교 로직이 추가 수정되었습니다.")
        print("📝 변경 사항:")
        print("  - 시간대 인식 datetime 처리 개선")
        print("  - 날짜만 비교하도록 수정 (시간 무시)")
        print("  - 디버그 로그 추가")
        return True
    else:
        print("❌ 수정할 코드를 찾을 수 없습니다. 코드가 이미 변경되었을 수 있습니다.")
        return False

if __name__ == "__main__":
    print("🔧 팝업 공지 날짜 비교 로직 추가 수정 시작...")
    success = fix_popup_notice_comparison()
    
    if success:
        print("\n✅ 수정 완료! 서버를 재시작하면 팝업 공지가 정상 작동합니다.")
        print("🔄 서버 재시작 명령어:")
        print("   sudo systemctl restart stock-finder-backend")
    else:
        print("\n❌ 수정 실패. 수동으로 코드를 확인해주세요.")
#!/usr/bin/env python3
"""
팝업 공지 날짜 파싱 문제 수정 패치

문제: 백엔드 코드가 YYYYMMDD 형식을 기대하지만 DB에는 timestamp 형식으로 저장됨
해결: 날짜 파싱 로직을 timestamp 형식에 맞게 수정
"""

import sys
import os

def fix_popup_notice_parsing():
    """main.py의 팝업 공지 날짜 파싱 로직을 수정합니다."""
    
    # 백엔드 디렉토리 경로
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    main_py_path = os.path.join(backend_dir, "main.py")
    
    if not os.path.exists(main_py_path):
        print(f"❌ main.py 파일을 찾을 수 없습니다: {main_py_path}")
        return False
    
    # 백업 생성
    backup_path = f"{main_py_path}.backup.popup_fix"
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
                    start_dt = datetime.strptime(start_date, "%Y%m%d")
                    end_dt = datetime.strptime(end_date, "%Y%m%d")
                    now = datetime.now()
                    
                    if now < start_dt or now > end_dt:
                        is_enabled = False
                except ValueError:
                    is_enabled = False'''
    
    # 새로운 코드
    new_code = '''            # 날짜 범위 확인
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
    
    # 코드 교체
    if old_code in content:
        new_content = content.replace(old_code, new_code)
        
        with open(main_py_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print("✅ 팝업 공지 날짜 파싱 로직이 수정되었습니다.")
        print("📝 변경 사항:")
        print("  - timestamp 형식 날짜 파싱 지원 추가")
        print("  - 기존 YYYYMMDD 형식 호환성 유지")
        print("  - 에러 로깅 개선")
        return True
    else:
        print("❌ 수정할 코드를 찾을 수 없습니다. 코드가 이미 변경되었을 수 있습니다.")
        return False

if __name__ == "__main__":
    print("🔧 팝업 공지 날짜 파싱 문제 수정 시작...")
    success = fix_popup_notice_parsing()
    
    if success:
        print("\n✅ 수정 완료! 서버를 재시작하면 팝업 공지가 정상 작동합니다.")
        print("🔄 서버 재시작 명령어:")
        print("   sudo systemctl restart stock-finder-backend")
    else:
        print("\n❌ 수정 실패. 수동으로 코드를 확인해주세요.")
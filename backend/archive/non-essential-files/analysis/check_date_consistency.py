#!/usr/bin/env python3
"""
날짜 형식 일관성 점검 스크립트
"""
import os
import re
import glob

def check_file_patterns(file_path):
    """파일에서 날짜 패턴 검색"""
    issues = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
        
        # 문제가 될 수 있는 패턴들
        patterns = [
            (r'strftime\(["\']%Y-%m-%d["\']', 'YYYY-MM-DD 생성'),
            (r'strftime\(["\'][^"\']*-%m-[^"\']*["\']', '하이픈 포함 날짜'),
            (r'format=["\']%Y-%m-%d["\']', 'pandas YYYY-MM-DD 파싱'),
            (r'datetime\.strptime\([^,]+,\s*["\']%Y-%m-%d["\']', 'YYYY-MM-DD 파싱'),
            (r'["\'][0-9]{4}-[0-9]{2}-[0-9]{2}["\']', '하드코딩된 YYYY-MM-DD'),
            (r'date\.replace\(["\'][-]["\']', 'replace 하이픈 제거'),
        ]
        
        for i, line in enumerate(lines, 1):
            for pattern, desc in patterns:
                if re.search(pattern, line):
                    issues.append({
                        'line': i,
                        'content': line.strip(),
                        'issue': desc,
                        'pattern': pattern
                    })
    
    except Exception as e:
        issues.append({'error': str(e)})
    
    return issues

def check_all_files():
    """모든 Python 파일 검사"""
    files_to_check = [
        'main.py',
        'scan_service_refactored.py',
        'kiwoom_api.py',
        'services/returns_service.py',
        'services/scan_service.py',
        'services/report_generator.py',
        'notification_service.py',
        'daily_update_service.py',
        'auto_trading_service.py',
        'naver_pay_service.py',
        'market_analyzer.py',
        'scanner.py',
        'auth_service.py',
        'portfolio_service.py',
        'admin_service.py'
    ]
    
    print("🔍 날짜 형식 일관성 점검 시작...")
    print("="*60)
    
    total_issues = 0
    files_with_issues = 0
    
    for file_path in files_to_check:
        if not os.path.exists(file_path):
            continue
            
        issues = check_file_patterns(file_path)
        
        if issues:
            files_with_issues += 1
            total_issues += len(issues)
            print(f"\n❌ {file_path} ({len(issues)}개 이슈)")
            
            for issue in issues:
                if 'error' in issue:
                    print(f"   오류: {issue['error']}")
                else:
                    print(f"   라인 {issue['line']}: {issue['issue']}")
                    print(f"   코드: {issue['content']}")
        else:
            print(f"✅ {file_path}")
    
    print("\n" + "="*60)
    print(f"📊 점검 결과:")
    print(f"   검사한 파일: {len([f for f in files_to_check if os.path.exists(f)])}")
    print(f"   문제 파일: {files_with_issues}")
    print(f"   총 이슈: {total_issues}")
    
    if total_issues == 0:
        print("🎉 모든 파일이 YYYYMMDD 형식으로 통일되었습니다!")
    else:
        print(f"⚠️  {total_issues}개 이슈를 수정해야 합니다.")

def check_good_patterns():
    """올바른 YYYYMMDD 패턴 확인"""
    print("\n🔍 YYYYMMDD 패턴 사용 현황:")
    
    good_patterns = [
        r'strftime\(["\']%Y%m%d["\']',
        r'format=["\']%Y%m%d["\']',
    ]
    
    files = glob.glob('*.py') + glob.glob('services/*.py')
    good_count = 0
    
    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            for pattern in good_patterns:
                matches = len(re.findall(pattern, content))
                if matches > 0:
                    good_count += matches
                    print(f"✅ {file_path}: {matches}개 YYYYMMDD 패턴")
        except:
            continue
    
    print(f"총 {good_count}개 올바른 YYYYMMDD 패턴 발견")

if __name__ == "__main__":
    check_all_files()
    check_good_patterns()
#!/usr/bin/env python3
"""
바텀메뉴 링크 설정 초기화 스크립트
"""
from scanner_settings_manager import create_scanner_settings_table, set_scanner_setting
from db_manager import db_manager

with db_manager.get_cursor(commit=True) as cur:
    create_scanner_settings_table(cur)
    set_scanner_setting(
        'bottom_nav_scanner_link',
        'v1',
        '바텀메뉴 추천종목 링크 타입 (v1: /customer-scanner, v2: /v2/scanner-v2)'
    )
    print('✅ 바텀메뉴 링크 기본 설정 추가 완료 (v1)')


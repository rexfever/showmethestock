"""
Regime v4 + Scanner v2 구조 검증 스크립트
사용자 요구사항에 따른 완전한 검증 수행
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from typing import Dict, List, Tuple
import inspect

# 검증 결과 저장
results = {
    "pass": [],
    "fail": [],
    "warnings": []
}

def check_function_exists(module, func_name: str, description: str) -> bool:
    """함수 존재 여부 확인"""
    if hasattr(module, func_name):
        func = getattr(module, func_name)
        if callable(func):
            results["pass"].append(f"✅ {description}: {func_name}() 존재")
            return True
    results["fail"].append(f"❌ {description}: {func_name}() 없음")
    return False

def check_field_exists(dataclass, field_name: str, description: str) -> bool:
    """dataclass 필드 존재 여부 확인"""
    if hasattr(dataclass, '__dataclass_fields__'):
        if field_name in dataclass.__dataclass_fields__:
            results["pass"].append(f"✅ {description}: {field_name} 필드 존재")
            return True
    results["fail"].append(f"❌ {description}: {field_name} 필드 없음")
    return False

def check_code_pattern(file_path: str, pattern: str, description: str, should_exist: bool = True) -> bool:
    """코드 패턴 존재 여부 확인"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            exists = pattern in content
            if should_exist:
                if exists:
                    results["pass"].append(f"✅ {description}: 패턴 발견")
                    return True
                else:
                    results["fail"].append(f"❌ {description}: 패턴 없음")
                    return False
            else:
                if not exists:
                    results["pass"].append(f"✅ {description}: 패턴 없음 (올바름)")
                    return True
                else:
                    results["fail"].append(f"❌ {description}: 패턴 발견 (문제)")
                    return False
    except Exception as e:
        results["fail"].append(f"❌ {description}: 파일 읽기 실패 - {e}")
        return False

print("=" * 80)
print("Regime v4 + Scanner v2 구조 검증")
print("=" * 80)

# ==========================================================
# 1) market_analyzer_v4.py 검증
# ==========================================================
print("\n[1] market_analyzer.py 검증")
print("-" * 80)

try:
    from market_analyzer import MarketAnalyzer, MarketCondition
    
    analyzer = MarketAnalyzer()
    
    # (1) compute_long_regime() 구현 여부
    check_function_exists(analyzer, "compute_long_regime", "compute_long_regime() 구현")
    
    # (2) compute_mid_regime() 구현 여부
    check_function_exists(analyzer, "compute_mid_regime", "compute_mid_regime() 구현")
    
    # (3) compute_short_term_risk() 구현 여부
    check_function_exists(analyzer, "compute_short_term_risk", "compute_short_term_risk() 구현")
    
    # (4) compose_final_regime_v4() 존재 여부
    check_function_exists(analyzer, "compose_final_regime_v4", "compose_final_regime_v4() 구현")
    
    # (5) MarketCondition 필드 확인
    check_field_exists(MarketCondition, "longterm_regime", "MarketCondition.longterm_regime")
    check_field_exists(MarketCondition, "midterm_regime", "MarketCondition.midterm_regime")
    check_field_exists(MarketCondition, "short_term_risk_score", "MarketCondition.short_term_risk_score")
    
    # analyze_market_condition_v4 존재 확인
    if hasattr(analyzer, "analyze_market_condition_v4"):
        results["pass"].append("✅ analyze_market_condition_v4() 존재")
    else:
        results["fail"].append("❌ analyze_market_condition_v4() 없음")
        
except Exception as e:
    results["fail"].append(f"❌ market_analyzer.py 검증 실패: {e}")

# ==========================================================
# 2) 단기 변동이 스캔 조건을 변경하지 않는지 검증
# ==========================================================
print("\n[2] 단기 변동이 스캔 조건을 변경하지 않는지 검증")
print("-" * 80)

base_dir = os.path.dirname(os.path.abspath(__file__))
scan_service_path = os.path.join(base_dir, "services", "scan_service.py")
scanner_path = os.path.join(base_dir, "scanner_v2", "core", "scanner.py")
config_regime_path = os.path.join(base_dir, "scanner_v2", "config_regime.py")

# (1) 당일 KOSPI/선물 변동률이 gap/ext/ATR/slope/min_signals/score_cut에 영향을 주지 않아야 함
check_code_pattern(
    scan_service_path,
    "kospi_return.*gap_max|gap_max.*kospi_return",
    "execute_scan_with_fallback에서 당일 KOSPI 변동이 gap_max에 영향",
    should_exist=False
)

check_code_pattern(
    scan_service_path,
    "kospi_return.*ext_from_tema20_max|ext_from_tema20_max.*kospi_return",
    "execute_scan_with_fallback에서 당일 KOSPI 변동이 ext_from_tema20_max에 영향",
    should_exist=False
)

# (2) 조건 강화/완화 로직 제거 확인
check_code_pattern(
    scan_service_path,
    "step.*override|override.*step|조건.*강화|조건.*완화",
    "execute_scan_with_fallback에서 step override 로직",
    should_exist=False
)

# (3) midterm_regime만 cutoff 결정 확인
check_code_pattern(
    scanner_path,
    "midterm_regime.*cutoff|cutoff.*midterm_regime",
    "scanner.py에서 midterm_regime으로 cutoff 결정",
    should_exist=True
)

# (4) short_term_risk_score는 후보 제거 목적만 사용 확인
check_code_pattern(
    scanner_path,
    "short_term_risk_score.*cutoff|cutoff.*short_term_risk_score",
    "scanner.py에서 short_term_risk_score가 cutoff 변경",
    should_exist=False
)

# ==========================================================
# 3) scanner_v2/core/scanner.py 검증
# ==========================================================
print("\n[3] scanner_v2/core/scanner.py 검증")
print("-" * 80)

# (1) _apply_regime_cutoff가 midterm_regime만 입력으로 받는지
check_code_pattern(
    scanner_path,
    "def _apply_regime_cutoff.*midterm_regime|midterm_regime.*_apply_regime_cutoff",
    "_apply_regime_cutoff에서 midterm_regime 사용",
    should_exist=True
)

# (2) short_term_risk_score가 risk_score에 가중으로 적용되는지
check_code_pattern(
    scanner_path,
    "short_term_risk_score.*risk_score|risk_score.*short_term_risk_score",
    "short_term_risk_score가 risk_score에 가중 적용",
    should_exist=True
)

# (3) 후보 제거 기준 확인
check_code_pattern(
    scanner_path,
    "score.*risk_score.*cutoff|cutoff.*score.*risk_score",
    "후보 제거 기준: (score - risk_score) < cutoff",
    should_exist=True
)

# (4) 단기 변동률에 연동된 gap/ext/ATR/slope 조정 확인
check_code_pattern(
    scanner_path,
    "kospi_return.*gap|gap.*kospi_return|daily.*change.*gap|gap.*daily.*change",
    "scanner.py에서 당일 변동률이 gap/ext/ATR/slope 조정",
    should_exist=False
)

# ==========================================================
# 4) config_regime_v4.py 검증
# ==========================================================
print("\n[4] config_regime.py 검증")
print("-" * 80)

# (1) swing/position/longterm cutoff는 midterm_regime만 기준
check_code_pattern(
    config_regime_path,
    "REGIME_CUTOFFS|cutoff.*regime",
    "config_regime.py에 REGIME_CUTOFFS 존재",
    should_exist=True
)

# (2) crash는 swing/position 모두 999로 차단
check_code_pattern(
    config_regime_path,
    "crash.*999|'crash'.*999",
    "crash 장세에서 swing/position 999 차단",
    should_exist=True
)

# (3) bear에서는 swing 999, position cutoff는 높게
check_code_pattern(
    config_regime_path,
    "bear.*swing.*999|'bear'.*swing.*999",
    "bear 장세에서 swing 999 차단",
    should_exist=True
)

# ==========================================================
# 5) scan_service.py 검증
# ==========================================================
print("\n[5] scan_service.py 검증")
print("-" * 80)

# (1) analyze_market_condition_v4()가 호출되는지
check_code_pattern(
    scan_service_path,
    "analyze_market_condition_v4",
    "execute_scan_with_fallback에서 analyze_market_condition_v4 호출",
    should_exist=True
)

# (2) gap/ext/ATR/slope/min_signals 조정이 presets에서 삭제되었는지
check_code_pattern(
    scan_service_path,
    "fallback_presets.*gap|gap.*fallback_presets",
    "fallback_presets에서 gap 조정",
    should_exist=False
)

# (3) fallback 단계는 수량 확보 목적만 담당
check_code_pattern(
    scan_service_path,
    "fallback.*조건.*변경|조건.*변경.*fallback",
    "fallback에서 조건 변경",
    should_exist=False
)

# ==========================================================
# 결과 출력
# ==========================================================
print("\n" + "=" * 80)
print("검증 결과 요약")
print("=" * 80)

print(f"\n✅ PASS: {len(results['pass'])}개")
for item in results['pass']:
    print(f"  {item}")

print(f"\n❌ FAIL: {len(results['fail'])}개")
for item in results['fail']:
    print(f"  {item}")

print(f"\n⚠️ WARNINGS: {len(results['warnings'])}개")
for item in results['warnings']:
    print(f"  {item}")

# 최종 판정
if len(results['fail']) == 0:
    print("\n🎉 전체 검증 PASS")
    sys.exit(0)
else:
    print(f"\n❌ 검증 FAIL: {len(results['fail'])}개 항목 실패")
    sys.exit(1)


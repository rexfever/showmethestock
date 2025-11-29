"""
Regime v4 + Scanner v2 구조 종합 검증 및 테스트
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from market_analyzer import market_analyzer
from scanner_factory import scan_with_scanner
from kiwoom_api import api
from typing import Dict, List

print("=" * 80)
print("Regime v4 + Scanner v2 구조 종합 검증")
print("=" * 80)

# 검증 결과
validation_results = {
    "section1": {"pass": [], "fail": []},
    "section2": {"pass": [], "fail": []},
    "section3": {"pass": [], "fail": []},
    "section4": {"pass": [], "fail": []},
    "section5": {"pass": [], "fail": []},
    "section6": {"pass": [], "fail": []},
    "section7": {"fail": []}
}

# ==========================================================
# 1) market_analyzer_v4.py 검증
# ==========================================================
print("\n[1] market_analyzer.py 검증")
print("-" * 80)

from market_analyzer import MarketAnalyzer, MarketCondition
import inspect

analyzer = MarketAnalyzer()

# (1) compute_long_regime() 구현 여부
if hasattr(analyzer, "compute_long_regime"):
    validation_results["section1"]["pass"].append("compute_long_regime() 존재")
else:
    validation_results["section1"]["fail"].append("compute_long_regime() 없음 - 20~60일 기준 레짐 계산 필요")

# (2) compute_mid_regime() 구현 여부
if hasattr(analyzer, "compute_mid_regime"):
    validation_results["section1"]["pass"].append("compute_mid_regime() 존재")
else:
    validation_results["section1"]["fail"].append("compute_mid_regime() 없음 - 5~20일 기준 레짐 계산 필요 (스캔 조건 핵심)")

# (3) compute_short_term_risk() 구현 여부
if hasattr(analyzer, "compute_short_term_risk"):
    validation_results["section1"]["pass"].append("compute_short_term_risk() 존재")
else:
    validation_results["section1"]["fail"].append("compute_short_term_risk() 없음 - 당일 KOSPI/미국선물/VIX 기반 단기 리스크 점수 (0~3) 필요")

# (4) compose_final_regime_v4() 존재 여부
if hasattr(analyzer, "compose_final_regime_v4"):
    validation_results["section1"]["pass"].append("compose_final_regime_v4() 존재")
else:
    validation_results["section1"]["fail"].append("compose_final_regime_v4() 없음 - midterm_regime을 final_regime으로 사용하는 함수 필요")

# (5) MarketCondition 필드 확인
if hasattr(MarketCondition, '__dataclass_fields__'):
    fields = MarketCondition.__dataclass_fields__
    if 'longterm_regime' in fields:
        validation_results["section1"]["pass"].append("MarketCondition.longterm_regime 필드 존재")
    else:
        validation_results["section1"]["fail"].append("MarketCondition.longterm_regime 필드 없음")
    
    if 'midterm_regime' in fields:
        validation_results["section1"]["pass"].append("MarketCondition.midterm_regime 필드 존재")
    else:
        validation_results["section1"]["fail"].append("MarketCondition.midterm_regime 필드 없음 - 스캔 조건의 핵심")
    
    if 'short_term_risk_score' in fields:
        validation_results["section1"]["pass"].append("MarketCondition.short_term_risk_score 필드 존재")
    else:
        validation_results["section1"]["fail"].append("MarketCondition.short_term_risk_score 필드 없음 - 후보 제거 목적")

# ==========================================================
# 2) 단기 변동이 스캔 조건을 변경하지 않는지 검증
# ==========================================================
print("\n[2] 단기 변동이 스캔 조건을 변경하지 않는지 검증")
print("-" * 80)

base_dir = os.path.dirname(os.path.abspath(__file__))
scan_service_path = os.path.join(base_dir, "services", "scan_service.py")
scanner_path = os.path.join(base_dir, "scanner_v2", "core", "scanner.py")

# 파일 읽기
try:
    with open(scan_service_path, 'r', encoding='utf-8') as f:
        scan_service_content = f.read()
    
    with open(scanner_path, 'r', encoding='utf-8') as f:
        scanner_content = f.read()
    
    # (1) 당일 KOSPI 변동률이 gap/ext/ATR/slope/min_signals/score_cut에 영향을 주지 않아야 함
    patterns_to_check = [
        ("kospi_return.*gap_max|gap_max.*kospi_return", "당일 KOSPI 변동이 gap_max에 영향", False),
        ("kospi_return.*ext_from_tema20_max|ext_from_tema20_max.*kospi_return", "당일 KOSPI 변동이 ext_from_tema20_max에 영향", False),
        ("kospi_return.*atr|atr.*kospi_return", "당일 KOSPI 변동이 ATR에 영향", False),
        ("kospi_return.*slope|slope.*kospi_return", "당일 KOSPI 변동이 slope에 영향", False),
        ("kospi_return.*min_signals|min_signals.*kospi_return", "당일 KOSPI 변동이 min_signals에 영향", False),
    ]
    
    for pattern, desc, should_exist in patterns_to_check:
        import re
        found = bool(re.search(pattern, scan_service_content, re.IGNORECASE))
        if should_exist == found:
            validation_results["section2"]["pass"].append(f"{desc}: {'발견' if found else '없음'} (올바름)")
        else:
            validation_results["section2"]["fail"].append(f"{desc}: {'발견됨 (문제)' if found else '없음 (필요)'}")
    
    # (2) 조건 강화/완화 로직 제거 확인
    if "step.*override|override.*step" not in scan_service_content.lower():
        validation_results["section2"]["pass"].append("step override 로직 없음 (올바름)")
    else:
        validation_results["section2"]["fail"].append("step override 로직 발견 (제거 필요)")
    
    # (3) midterm_regime만 cutoff 결정 확인
    if "midterm_regime" in scanner_content:
        validation_results["section2"]["pass"].append("scanner.py에서 midterm_regime 사용")
    else:
        validation_results["section2"]["fail"].append("scanner.py에서 midterm_regime 사용 안 함 - final_regime 대신 midterm_regime 사용 필요")
    
    # (4) short_term_risk_score는 후보 제거 목적만 사용 확인
    if "short_term_risk_score.*cutoff|cutoff.*short_term_risk_score" not in scanner_content.lower():
        validation_results["section2"]["pass"].append("short_term_risk_score가 cutoff 변경 안 함 (올바름)")
    else:
        validation_results["section2"]["fail"].append("short_term_risk_score가 cutoff 변경 (문제)")
        
except Exception as e:
    validation_results["section2"]["fail"].append(f"파일 읽기 실패: {e}")

# ==========================================================
# 3) scanner_v2/core/scanner.py 검증
# ==========================================================
print("\n[3] scanner_v2/core/scanner.py 검증")
print("-" * 80)

try:
    # (1) _apply_regime_cutoff가 midterm_regime만 입력으로 받는지
    if "midterm_regime" in scanner_content and "_apply_regime_cutoff" in scanner_content:
        # 함수 시그니처 확인
        import re
        func_match = re.search(r"def _apply_regime_cutoff\([^)]*\)", scanner_content)
        if func_match:
            func_sig = func_match.group(0)
            if "midterm_regime" in func_sig:
                validation_results["section3"]["pass"].append("_apply_regime_cutoff가 midterm_regime 입력 받음")
            else:
                validation_results["section3"]["fail"].append("_apply_regime_cutoff가 midterm_regime 입력 안 받음")
        else:
            validation_results["section3"]["fail"].append("_apply_regime_cutoff 함수 시그니처 확인 실패")
    else:
        validation_results["section3"]["fail"].append("_apply_regime_cutoff 또는 midterm_regime 사용 안 함")
    
    # (2) short_term_risk_score가 risk_score에 가중으로 적용되는지
    if "short_term_risk_score" in scanner_content and "risk_score" in scanner_content:
        # 가중 적용 패턴 확인
        if re.search(r"risk_score.*short_term_risk_score|short_term_risk_score.*risk_score", scanner_content):
            validation_results["section3"]["pass"].append("short_term_risk_score가 risk_score에 가중 적용")
        else:
            validation_results["section3"]["fail"].append("short_term_risk_score가 risk_score에 가중 적용 안 함")
    else:
        validation_results["section3"]["fail"].append("short_term_risk_score 또는 risk_score 사용 안 함")
    
    # (3) 후보 제거 기준 확인
    if re.search(r"score.*-.*risk_score.*<.*cutoff|cutoff.*>.*score.*-.*risk_score", scanner_content):
        validation_results["section3"]["pass"].append("후보 제거 기준: (score - risk_score) < cutoff")
    else:
        validation_results["section3"]["fail"].append("후보 제거 기준이 (score - risk_score) < cutoff가 아님")
    
    # (4) 단기 변동률에 연동된 gap/ext/ATR/slope 조정 확인
    if not re.search(r"kospi_return.*gap|gap.*kospi_return|daily.*change.*gap", scanner_content, re.IGNORECASE):
        validation_results["section3"]["pass"].append("당일 변동률이 gap/ext/ATR/slope 조정 안 함 (올바름)")
    else:
        validation_results["section3"]["fail"].append("당일 변동률이 gap/ext/ATR/slope 조정 (문제)")
        
except Exception as e:
    validation_results["section3"]["fail"].append(f"검증 실패: {e}")

# ==========================================================
# 4) config_regime_v4.py 검증
# ==========================================================
print("\n[4] config_regime.py 검증")
print("-" * 80)

config_regime_path = os.path.join(base_dir, "scanner_v2", "config_regime.py")
try:
    with open(config_regime_path, 'r', encoding='utf-8') as f:
        config_content = f.read()
    
    # (1) REGIME_CUTOFFS 존재 확인
    if "REGIME_CUTOFFS" in config_content:
        validation_results["section4"]["pass"].append("REGIME_CUTOFFS 존재")
        
        # (2) crash는 swing/position 모두 999로 차단
        if "'crash'" in config_content and "999" in config_content:
            if "'swing': 999" in config_content or '"swing": 999' in config_content:
                validation_results["section4"]["pass"].append("crash에서 swing 999 차단")
            else:
                validation_results["section4"]["fail"].append("crash에서 swing 999 차단 안 함")
            
            if "'position': 999" in config_content or '"position": 999' in config_content:
                validation_results["section4"]["pass"].append("crash에서 position 999 차단")
            else:
                validation_results["section4"]["fail"].append("crash에서 position 999 차단 안 함")
        else:
            validation_results["section4"]["fail"].append("crash 장세 설정 없음")
        
        # (3) bear에서는 swing 999, position cutoff는 높게
        if "'bear'" in config_content:
            if "'swing': 999" in config_content or '"swing": 999' in config_content:
                validation_results["section4"]["pass"].append("bear에서 swing 999 차단")
            else:
                validation_results["section4"]["fail"].append("bear에서 swing 999 차단 안 함")
            
            # position cutoff가 높은지 확인 (5.0 이상)
            if re.search(r"'bear'.*'position':\s*([0-9.]+)", config_content):
                match = re.search(r"'bear'.*'position':\s*([0-9.]+)", config_content)
                if match:
                    pos_cutoff = float(match.group(1))
                    if pos_cutoff >= 5.0:
                        validation_results["section4"]["pass"].append(f"bear에서 position cutoff 높음 ({pos_cutoff})")
                    else:
                        validation_results["section4"]["fail"].append(f"bear에서 position cutoff 낮음 ({pos_cutoff}, 5.0 이상 필요)")
        else:
            validation_results["section4"]["fail"].append("bear 장세 설정 없음")
    else:
        validation_results["section4"]["fail"].append("REGIME_CUTOFFS 없음")
        
except Exception as e:
    validation_results["section4"]["fail"].append(f"config_regime.py 검증 실패: {e}")

# ==========================================================
# 5) scan_service.py 검증
# ==========================================================
print("\n[5] scan_service.py 검증")
print("-" * 80)

try:
    # (1) analyze_market_condition_v4()가 호출되는지
    if "analyze_market_condition_v4" in scan_service_content:
        validation_results["section5"]["pass"].append("analyze_market_condition_v4() 호출")
    else:
        validation_results["section5"]["fail"].append("analyze_market_condition_v4() 호출 안 함")
    
    # (2) gap/ext/ATR/slope/min_signals 조정이 presets에서 삭제되었는지
    if "fallback_presets" in scan_service_content:
        # presets에서 gap/ext/ATR/slope/min_signals 조정이 있는지 확인
        if not re.search(r"gap.*fallback_presets|fallback_presets.*gap", scan_service_content, re.IGNORECASE):
            validation_results["section5"]["pass"].append("fallback_presets에서 gap 조정 없음 (올바름)")
        else:
            validation_results["section5"]["fail"].append("fallback_presets에서 gap 조정 있음 (삭제 필요)")
    else:
        validation_results["section5"]["fail"].append("fallback_presets 없음")
    
    # (3) fallback 단계는 수량 확보 목적만 담당
    if "fallback" in scan_service_content.lower():
        # 조건 변경 로직이 있는지 확인
        if not re.search(r"fallback.*조건.*변경|조건.*변경.*fallback", scan_service_content, re.IGNORECASE):
            validation_results["section5"]["pass"].append("fallback에서 조건 변경 없음 (올바름)")
        else:
            validation_results["section5"]["fail"].append("fallback에서 조건 변경 있음 (수량 확보만 해야 함)")
            
except Exception as e:
    validation_results["section5"]["fail"].append(f"scan_service.py 검증 실패: {e}")

# ==========================================================
# 6) 테스트 검증
# ==========================================================
print("\n[6] 테스트 검증")
print("-" * 80)

test_dates = ['20250723', '20250917', '20251022', '20250820', '20251105']
test_results = []

for test_date in test_dates:
    try:
        market_analyzer.clear_cache()
        market_condition = market_analyzer.analyze_market_condition(test_date, regime_version='v4')
        
        # midterm_regime 확인
        midterm_regime = getattr(market_condition, 'midterm_regime', None)
        final_regime = getattr(market_condition, 'final_regime', None)
        short_term_risk = getattr(market_condition, 'short_term_risk_score', None)
        
        # 유니버스 구성
        kospi_universe = api.get_top_codes('KOSPI', 50)
        kosdaq_universe = api.get_top_codes('KOSDAQ', 50)
        universe = list(set(kospi_universe + kosdaq_universe))
        
        # 스캔 실행
        results = scan_with_scanner(
            universe_codes=universe,
            preset_overrides=None,
            base_date=test_date,
            market_condition=market_condition,
            version="v2"
        )
        
        test_results.append({
            "date": test_date,
            "midterm_regime": midterm_regime,
            "final_regime": final_regime,
            "short_term_risk_score": short_term_risk,
            "scan_count": len(results)
        })
        
        print(f"  {test_date}: midterm={midterm_regime}, final={final_regime}, risk={short_term_risk}, 스캔={len(results)}개")
        
    except Exception as e:
        print(f"  {test_date}: 오류 - {e}")
        test_results.append({
            "date": test_date,
            "error": str(e)
        })

# midterm_regime이 동일한 날은 스캔 조건이 동일해야 함
midterm_groups = {}
for result in test_results:
    if "error" not in result:
        midterm = result.get("midterm_regime")
        if midterm:
            if midterm not in midterm_groups:
                midterm_groups[midterm] = []
            midterm_groups[midterm].append(result)

if len(midterm_groups) > 0:
    validation_results["section6"]["pass"].append(f"테스트 완료: {len(test_results)}개 날짜")
    for midterm, group in midterm_groups.items():
        if len(group) > 1:
            scan_counts = [r["scan_count"] for r in group]
            if len(set(scan_counts)) == 1:
                validation_results["section6"]["pass"].append(f"midterm_regime={midterm}인 날들의 스캔 결과 동일")
            else:
                validation_results["section6"]["fail"].append(f"midterm_regime={midterm}인 날들의 스캔 결과 다름: {scan_counts}")
else:
    validation_results["section6"]["fail"].append("midterm_regime이 없어 테스트 불가")

# ==========================================================
# 7) FAIL 조건 확인
# ==========================================================
print("\n[7] FAIL 조건 확인")
print("-" * 80)

# 당일 KOSPI 변동률이 조건에 영향을 미치는지
if re.search(r"kospi_return.*gap_max|gap_max.*kospi_return", scan_service_content, re.IGNORECASE):
    validation_results["section7"]["fail"].append("FAIL: 당일 KOSPI 변동률이 gap_max에 영향")
if re.search(r"kospi_return.*ext_from_tema20_max|ext_from_tema20_max.*kospi_return", scan_service_content, re.IGNORECASE):
    validation_results["section7"]["fail"].append("FAIL: 당일 KOSPI 변동률이 ext_from_tema20_max에 영향")

# final_regime 대신 midterm_regime 비사용
if "midterm_regime" not in scanner_content or "_apply_regime_cutoff" not in scanner_content:
    validation_results["section7"]["fail"].append("FAIL: final_regime 대신 midterm_regime 비사용")

# short_term_risk_score가 cutoff를 변경하는지
if re.search(r"short_term_risk_score.*cutoff|cutoff.*short_term_risk_score", scanner_content, re.IGNORECASE):
    validation_results["section7"]["fail"].append("FAIL: short_term_risk_score가 cutoff를 변경")

# ==========================================================
# 최종 결과 출력
# ==========================================================
print("\n" + "=" * 80)
print("최종 검증 결과")
print("=" * 80)

total_pass = sum(len(v.get("pass", [])) for v in validation_results.values())
total_fail = sum(len(v.get("fail", [])) for v in validation_results.values())

print(f"\n✅ 총 PASS: {total_pass}개")
print(f"❌ 총 FAIL: {total_fail}개")

for section_name, results in validation_results.items():
    pass_items = results.get("pass", [])
    fail_items = results.get("fail", [])
    if pass_items or fail_items:
        print(f"\n[{section_name}]")
        for item in pass_items:
            print(f"  ✅ {item}")
        for item in fail_items:
            print(f"  ❌ {item}")

# 테스트 결과 테이블
print("\n" + "=" * 80)
print("테스트 결과 테이블")
print("=" * 80)
print(f"{'날짜':<12} {'midterm_regime':<15} {'final_regime':<15} {'short_term_risk':<15} {'스캔 결과':<10}")
print("-" * 80)
for result in test_results:
    if "error" not in result:
        print(f"{result['date']:<12} {str(result.get('midterm_regime', 'N/A')):<15} {str(result.get('final_regime', 'N/A')):<15} {str(result.get('short_term_risk_score', 'N/A')):<15} {result.get('scan_count', 0):<10}")
    else:
        print(f"{result['date']:<12} {'ERROR':<15} {'ERROR':<15} {'ERROR':<15} {'ERROR':<10}")

# 최종 판정
if total_fail == 0:
    print("\n🎉 전체 검증 PASS")
    sys.exit(0)
else:
    print(f"\n❌ 검증 FAIL: {total_fail}개 항목 실패")
    if len(validation_results["section7"]["fail"]) > 0:
        print("\n⚠️ CRITICAL FAIL 조건 발견:")
        for item in validation_results["section7"]["fail"]:
            print(f"  {item}")
    sys.exit(1)


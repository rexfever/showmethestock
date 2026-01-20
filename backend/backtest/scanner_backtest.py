#!/usr/bin/env python3
"""
스캐너 백테스트 스크립트
날짜 범위를 지정하여 스캔을 실행하고 성과를 분석합니다.
캐시 데이터를 활용하여 빠르게 실행합니다.
"""
import sys
import os
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import json
import pandas as pd

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from date_helper import normalize_date, yyyymmdd_to_date
from main import is_trading_day
from config import config
from kiwoom_api import api
from market_analyzer import market_analyzer
from services.scan_service import execute_scan_with_fallback
from scanner_factory import get_scanner
from scanner_settings_manager import get_scanner_version, get_regime_version
import holidays


def get_trading_days(start_date: str, end_date: str) -> List[str]:
    """시작일부터 종료일까지의 거래일 리스트 반환"""
    start_dt = datetime.strptime(start_date, "%Y%m%d")
    end_dt = datetime.strptime(end_date, "%Y%m%d")
    
    # 한국 공휴일
    kr_holidays = holidays.SouthKorea(years=range(start_dt.year, end_dt.year + 2))
    
    trading_days = []
    current = start_dt
    while current <= end_dt:
        date_str = current.strftime("%Y%m%d")
        # 주말 체크
        if current.weekday() < 5:  # 월~금
            # 공휴일 체크
            if current.date() not in kr_holidays:
                trading_days.append(date_str)
        current += timedelta(days=1)
    
    return trading_days


def get_nth_trading_day(start_date: str, n: int) -> Optional[str]:
    """
    시작일부터 N번째 거래일 반환
    
    Args:
        start_date: 시작 날짜 (YYYYMMDD)
        n: N번째 거래일 (1 = 다음 거래일, 2 = 다다음 거래일, ...)
    
    Returns:
        N번째 거래일 (YYYYMMDD), 찾지 못하면 None
    """
    if n <= 0:
        return start_date
    
    start_dt = datetime.strptime(start_date, "%Y%m%d")
    kr_holidays = holidays.SouthKorea(years=range(start_dt.year, start_dt.year + 2))
    
    # 충분한 범위까지 거래일 찾기 (최대 30일 후까지)
    end_dt = start_dt + timedelta(days=max(n * 2 + 10, 30))
    
    trading_days = []
    current = start_dt
    while current <= end_dt and len(trading_days) < n:
        # 주말 체크
        if current.weekday() < 5:  # 월~금
            # 공휴일 체크
            if current.date() not in kr_holidays:
                trading_days.append(current.strftime("%Y%m%d"))
        current += timedelta(days=1)
    
    # N번째 거래일 반환 (인덱스는 0부터 시작하므로 n-1)
    if len(trading_days) >= n:
        return trading_days[n - 1]
    elif trading_days:
        # N번째를 찾지 못했지만 마지막 거래일 반환
        return trading_days[-1]
    else:
        return None


def get_universe(kospi_limit: int = None, kosdaq_limit: int = None, date: str = None) -> List[str]:
    """유니버스 종목 리스트 가져오기"""
    kp = kospi_limit or config.universe_kospi
    kd = kosdaq_limit or config.universe_kosdaq
    
    try:
        kospi = api.get_top_codes('KOSPI', kp)
        kosdaq = api.get_top_codes('KOSDAQ', kd)
        universe = [*kospi, *kosdaq]
        return universe
    except Exception as e:
        print(f"⚠️ 유니버스 조회 실패: {e}")
        return []


def run_scan_for_date(
    date: str,
    kospi_limit: int = None,
    kosdaq_limit: int = None,
    scanner_version: str = None,
    regime_version: str = None,
    use_cache: bool = True
) -> Dict:
    """
    특정 날짜에 대한 스캔 실행
    
    Args:
        date: 스캔 날짜 (YYYYMMDD)
        kospi_limit: KOSPI 종목 수 제한
        kosdaq_limit: KOSDAQ 종목 수 제한
        scanner_version: 스캐너 버전 (v1/v2), None이면 DB에서 읽음
        regime_version: 레짐 분석 버전 (v1/v3/v4), None이면 DB에서 읽음
        use_cache: 캐시 사용 여부
    
    Returns:
        스캔 결과 딕셔너리
    """
    try:
        # 날짜 정규화
        normalized_date = normalize_date(date)
        
        # 거래일 체크
        if not is_trading_day(normalized_date):
            return {
                "date": normalized_date,
                "success": False,
                "error": "거래일이 아닙니다",
                "items": [],
                "market_condition": None
            }
        
        # 유니버스 조회
        universe = get_universe(kospi_limit, kosdaq_limit, normalized_date)
        if not universe:
            return {
                "date": normalized_date,
                "success": False,
                "error": "유니버스 조회 실패",
                "items": [],
                "market_condition": None
            }
        
        # 시장 상황 분석
        market_condition = None
        if config.market_analysis_enable:
            try:
                if not use_cache:
                    market_analyzer.clear_cache()
                
                # 레짐 버전 결정
                if regime_version is None:
                    try:
                        regime_version = get_regime_version()
                    except Exception:
                        regime_version = getattr(config, 'regime_version', 'v1')
                
                market_condition = market_analyzer.analyze_market_condition(
                    normalized_date,
                    regime_version=regime_version
                )
                
                # 레짐 버전 로그
                if hasattr(market_condition, 'version'):
                    if market_condition.version == 'regime_v4':
                        print(f"  📊 Regime v4: {market_condition.final_regime} "
                              f"(trend: {market_condition.global_trend_score:.2f}, "
                              f"risk: {market_condition.global_risk_score:.2f})")
                    elif market_condition.version == 'regime_v3':
                        print(f"  📊 Regime v3: {market_condition.final_regime} "
                              f"(점수: {market_condition.final_score:.2f})")
                    else:
                        print(f"  📊 Regime v1: {market_condition.market_sentiment} "
                              f"(수익률: {market_condition.kospi_return*100:.2f}%)")
            except Exception as e:
                print(f"  ⚠️ 시장 분석 실패: {e}")
        
        # 스캐너 버전 결정
        if scanner_version is None:
            try:
                scanner_version = get_scanner_version()
            except Exception:
                scanner_version = getattr(config, 'scanner_version', 'v1')
        
        # 스캔 실행
        result = execute_scan_with_fallback(universe, normalized_date, market_condition)
        
        if len(result) == 3:
            items, chosen_step, actual_scanner_version = result
        else:
            items, chosen_step = result
            actual_scanner_version = scanner_version
        
        return {
            "date": normalized_date,
            "success": True,
            "items": items,
            "matched_count": len(items),
            "chosen_step": chosen_step,
            "scanner_version": actual_scanner_version,
            "regime_version": regime_version or getattr(config, 'regime_version', 'v1'),
            "market_condition": {
                "version": getattr(market_condition, 'version', 'regime_v1') if market_condition else None,
                "sentiment": getattr(market_condition, 'market_sentiment', None) if market_condition else None,
                "final_regime": getattr(market_condition, 'final_regime', None) if market_condition else None,
                "kospi_return": getattr(market_condition, 'kospi_return', None) if market_condition else None,
            } if market_condition else None,
            "universe_size": len(universe)
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "date": date,
            "success": False,
            "error": str(e),
            "items": [],
            "market_condition": None
        }


def analyze_performance(scan_results: List[Dict], days_after: int = 5) -> Dict:
    """
    스캔 결과의 성과 분석
    
    Args:
        scan_results: 스캔 결과 리스트
        days_after: 몇 일 후 가격으로 성과 측정할지
    
    Returns:
        성과 분석 결과 (에러 통계 포함)
    """
    if not scan_results:
        return {
            "total_scans": 0,
            "total_items": 0,
            "analyzed_dates": 0,
            "overall_avg_return": 0,
            "overall_win_rate": 0,
            "performance_by_date": {},
            "errors": {
                "date_errors": [],
                "item_errors": [],
                "total_item_errors": 0
            }
        }
    
    total_scans = len([r for r in scan_results if r.get("success")])
    total_items = sum(len(r.get("items", [])) for r in scan_results if r.get("success"))
    
    # 날짜별 성과 분석
    performance_by_date = {}
    error_stats = {
        "date_errors": [],  # 날짜별 에러
        "item_errors": [],  # 종목별 에러 (최대 100개)
        "total_item_errors": 0  # 전체 종목 에러 수
    }
    
    for result in scan_results:
        if not result.get("success") or not result.get("items"):
            continue
        
        date = result["date"]
        items = result["items"]
        
        # N일 후 가격 조회 (정확한 거래일 찾기)
        try:
            # N번째 거래일 찾기 (days_after일 후의 거래일)
            target_date_str = get_nth_trading_day(date, days_after)
            if not target_date_str:
                # 거래일을 찾지 못한 경우 원래 날짜 사용
                target_date_str = date
                error_stats["date_errors"].append({
                    "date": date,
                    "error": f"{days_after}일 후 거래일을 찾지 못함"
                })
            
            performance_data = []
            item_errors_for_date = []
            
            for item in items:
                code = item.get("ticker") or item.get("code")
                if not code:
                    item_errors_for_date.append({
                        "code": "UNKNOWN",
                        "error": "종목 코드 없음"
                    })
                    error_stats["total_item_errors"] += 1
                    continue
                
                try:
                    # 스캔 당일 가격
                    scan_price = item.get("current_price") or item.get("close_price")
                    if not scan_price:
                        item_errors_for_date.append({
                            "code": code,
                            "error": "가격 정보 없음"
                        })
                        error_stats["total_item_errors"] += 1
                        continue
                    
                    # N일 후 가격 조회 (base_dt 명시적 사용, 캐시 활용)
                    # base_dt를 지정하여 해당 날짜 기준 데이터 조회
                    df = api.get_ohlcv(code, count=1, base_dt=target_date_str)
                    if df.empty:
                        # 캐시에서 찾지 못한 경우, 더 많은 데이터 조회 시도
                        df = api.get_ohlcv(code, count=10, base_dt=target_date_str)
                        if df.empty:
                            item_errors_for_date.append({
                                "code": code,
                                "error": f"{target_date_str} OHLCV 데이터 없음"
                            })
                            error_stats["total_item_errors"] += 1
                            continue
                    
                    # base_dt가 지정된 경우, 해당 날짜의 데이터가 있는지 확인
                    if 'date' in df.columns:
                        # 날짜 컬럼이 있는 경우, target_date_str과 일치하는 행 찾기
                        df['date_str'] = pd.to_datetime(df['date']).dt.strftime('%Y%m%d')
                        target_df = df[df['date_str'] == target_date_str]
                        if not target_df.empty:
                            future_price = float(target_df.iloc[-1]['close'])
                        else:
                            # 정확한 날짜가 없으면 마지막 행 사용
                            future_price = float(df.iloc[-1]['close'])
                    else:
                        # 날짜 컬럼이 없으면 마지막 행 사용
                        future_price = float(df.iloc[-1]['close'])
                    
                    return_pct = (future_price / scan_price - 1) * 100
                    
                    performance_data.append({
                        "code": code,
                        "name": item.get("name"),
                        "scan_price": scan_price,
                        "future_price": future_price,
                        "return_pct": return_pct,
                        "score": item.get("score", 0),
                        "strategy": item.get("strategy", "관찰")
                    })
                except Exception as e:
                    # 종목별 에러 추적 (최대 100개)
                    if len(error_stats["item_errors"]) < 100:
                        error_stats["item_errors"].append({
                            "date": date,
                            "code": code,
                            "error": str(e)
                        })
                    error_stats["total_item_errors"] += 1
                    continue
            
            # 날짜별 에러 기록
            if item_errors_for_date:
                error_stats["date_errors"].append({
                    "date": date,
                    "item_errors": item_errors_for_date[:10]  # 최대 10개만
                })
            
            if performance_data:
                avg_return = sum(p["return_pct"] for p in performance_data) / len(performance_data)
                win_rate = sum(1 for p in performance_data if p["return_pct"] > 0) / len(performance_data) * 100
                
                performance_by_date[date] = {
                    "items_count": len(performance_data),
                    "avg_return": avg_return,
                    "win_rate": win_rate,
                    "items": performance_data
                }
        except Exception as e:
            error_stats["date_errors"].append({
                "date": date,
                "error": str(e)
            })
            continue
    
    # 전체 통계
    all_returns = []
    for perf in performance_by_date.values():
        all_returns.extend([p["return_pct"] for p in perf["items"]])
    
    overall_avg_return = sum(all_returns) / len(all_returns) if all_returns else 0
    overall_win_rate = sum(1 for r in all_returns if r > 0) / len(all_returns) * 100 if all_returns else 0
    
    return {
        "total_scans": total_scans,
        "total_items": total_items,
        "analyzed_dates": len(performance_by_date),
        "overall_avg_return": overall_avg_return,
        "overall_win_rate": overall_win_rate,
        "performance_by_date": performance_by_date,
        "errors": error_stats
    }


def print_summary(scan_results: List[Dict], performance: Dict):
    """결과 요약 출력"""
    print("\n" + "=" * 80)
    print("📊 백테스트 결과 요약")
    print("=" * 80)
    
    print(f"\n✅ 성공한 스캔: {performance['total_scans']}개")
    print(f"📈 총 추천 종목: {performance['total_items']}개")
    print(f"📅 분석 완료 날짜: {performance['analyzed_dates']}개")
    
    if performance['analyzed_dates'] > 0:
        print(f"\n📊 전체 성과:")
        print(f"  평균 수익률: {performance['overall_avg_return']:.2f}%")
        print(f"  승률: {performance['overall_win_rate']:.2f}%")
    
    # 날짜별 상세
    if performance.get('performance_by_date'):
        print(f"\n📅 날짜별 성과:")
        for date, perf in sorted(performance['performance_by_date'].items()):
            print(f"  {date}: {perf['items_count']}개 종목, "
                  f"평균 {perf['avg_return']:.2f}%, 승률 {perf['win_rate']:.2f}%")
    
    # 실패한 스캔
    failed = [r for r in scan_results if not r.get("success")]
    if failed:
        print(f"\n❌ 실패한 스캔: {len(failed)}개")
        for r in failed[:5]:  # 최대 5개만 표시
            print(f"  {r['date']}: {r.get('error', 'Unknown error')}")
        if len(failed) > 5:
            print(f"  ... 외 {len(failed) - 5}개")
    
    # 에러 통계 표시
    if performance.get('errors'):
        errors = performance['errors']
        if errors.get('date_errors') or errors.get('item_errors'):
            print(f"\n⚠️ 에러 통계:")
            print(f"  날짜별 에러: {len(errors.get('date_errors', []))}개")
            print(f"  종목별 에러: {errors.get('total_item_errors', 0)}개")
            if errors.get('date_errors'):
                print(f"  날짜별 에러 상세 (최대 5개):")
                for err in errors['date_errors'][:5]:
                    print(f"    {err.get('date', 'UNKNOWN')}: {err.get('error', 'Unknown')}")


def save_results(scan_results: List[Dict], performance: Dict, output_dir: str = "backtest_results"):
    """결과를 파일로 저장"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 스캔 결과 저장
    results_file = output_path / f"scan_results_{timestamp}.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(scan_results, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n💾 스캔 결과 저장: {results_file}")
    
    # 성과 분석 저장
    perf_file = output_path / f"performance_{timestamp}.json"
    with open(perf_file, 'w', encoding='utf-8') as f:
        json.dump(performance, f, ensure_ascii=False, indent=2, default=str)
    print(f"💾 성과 분석 저장: {perf_file}")
    
    # CSV 요약 저장
    if performance.get('performance_by_date'):
        csv_data = []
        for date, perf in sorted(performance['performance_by_date'].items()):
            csv_data.append({
                "date": date,
                "items_count": perf['items_count'],
                "avg_return": perf['avg_return'],
                "win_rate": perf['win_rate']
            })
        
        csv_file = output_path / f"performance_summary_{timestamp}.csv"
        df = pd.DataFrame(csv_data)
        df.to_csv(csv_file, index=False, encoding='utf-8-sig')
        print(f"💾 성과 요약 CSV 저장: {csv_file}")


def main():
    parser = argparse.ArgumentParser(description="스캐너 백테스트 실행")
    parser.add_argument(
        "--start-date",
        type=str,
        required=True,
        help="시작 날짜 (YYYYMMDD)"
    )
    parser.add_argument(
        "--end-date",
        type=str,
        required=True,
        help="종료 날짜 (YYYYMMDD)"
    )
    parser.add_argument(
        "--scanner-version",
        type=str,
        choices=['v1', 'v2'],
        default=None,
        help="스캐너 버전 (기본: DB 설정)"
    )
    parser.add_argument(
        "--regime-version",
        type=str,
        choices=['v1', 'v3', 'v4'],
        default=None,
        help="레짐 분석 버전 (기본: DB 설정)"
    )
    parser.add_argument(
        "--kospi-limit",
        type=int,
        default=None,
        help="KOSPI 종목 수 제한 (기본: config 값)"
    )
    parser.add_argument(
        "--kosdaq-limit",
        type=int,
        default=None,
        help="KOSDAQ 종목 수 제한 (기본: config 값)"
    )
    parser.add_argument(
        "--days-after",
        type=int,
        default=5,
        help="성과 측정 일수 (기본: 5일)"
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="캐시 사용 안 함"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="backtest_results",
        help="결과 저장 디렉토리 (기본: backtest_results)"
    )
    parser.add_argument(
        "--save-results",
        action="store_true",
        help="결과를 파일로 저장"
    )
    
    args = parser.parse_args()
    
    # 날짜 검증
    try:
        start_date = normalize_date(args.start_date)
        end_date = normalize_date(args.end_date)
    except Exception as e:
        print(f"❌ 날짜 형식 오류: {e}")
        return 1
    
    # 거래일 리스트 가져오기
    trading_days = get_trading_days(start_date, end_date)
    if not trading_days:
        print(f"❌ {start_date} ~ {end_date} 기간에 거래일이 없습니다.")
        return 1
    
    print(f"📅 백테스트 기간: {start_date} ~ {end_date}")
    print(f"📊 거래일 수: {len(trading_days)}개")
    print(f"🔧 스캐너 버전: {args.scanner_version or 'DB 설정'}")
    print(f"🔧 레짐 버전: {args.regime_version or 'DB 설정'}")
    print(f"💾 캐시 사용: {not args.no_cache}")
    print()
    
    # 캐시 상태 확인
    if not args.no_cache:
        cache_stats = api.get_ohlcv_cache_stats()
        print(f"📦 OHLCV 캐시 상태:")
        print(f"  메모리: {cache_stats.get('memory', {}).get('hits', 0)} hits, "
              f"{cache_stats.get('memory', {}).get('misses', 0)} misses")
        print(f"  디스크: {cache_stats.get('disk', {}).get('files', 0)} 파일, "
              f"{cache_stats.get('disk', {}).get('size_mb', 0):.2f} MB")
        print()
    
    # 스캔 실행
    scan_results = []
    for i, date in enumerate(trading_days, 1):
        print(f"[{i}/{len(trading_days)}] {date} 스캔 중...", end=' ', flush=True)
        
        result = run_scan_for_date(
            date=date,
            kospi_limit=args.kospi_limit,
            kosdaq_limit=args.kosdaq_limit,
            scanner_version=args.scanner_version,
            regime_version=args.regime_version,
            use_cache=not args.no_cache
        )
        
        scan_results.append(result)
        
        if result.get("success"):
            print(f"✅ 완료 ({result.get('matched_count', 0)}개 종목)")
        else:
            print(f"❌ 실패: {result.get('error', 'Unknown error')}")
    
    # 성과 분석
    print("\n📊 성과 분석 중...")
    performance = analyze_performance(scan_results, days_after=args.days_after)
    
    # 결과 출력
    print_summary(scan_results, performance)
    
    # 캐시 상태 확인 (종료)
    if not args.no_cache and cache_stats_before:
        cache_stats_after = api.get_ohlcv_cache_stats()
        print(f"\n📦 OHLCV 캐시 상태 (종료):")
        print(f"  메모리: {cache_stats_after.get('memory', {}).get('hits', 0)} hits, "
              f"{cache_stats_after.get('memory', {}).get('misses', 0)} misses")
        print(f"  디스크: {cache_stats_after.get('disk', {}).get('files', 0)} 파일, "
              f"{cache_stats_after.get('disk', {}).get('size_mb', 0):.2f} MB")
        
        # 캐시 히트율 계산
        mem_hits = cache_stats_after.get('memory', {}).get('hits', 0)
        mem_misses = cache_stats_after.get('memory', {}).get('misses', 0)
        if mem_hits + mem_misses > 0:
            hit_rate = mem_hits / (mem_hits + mem_misses) * 100
            print(f"  캐시 히트율: {hit_rate:.2f}%")
    
    # 결과 저장
    if args.save_results:
        save_results(scan_results, performance, args.output_dir)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())


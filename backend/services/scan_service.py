"""
스캔 관련 서비스
"""
import json
import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime
from scanner_factory import scan_with_scanner
from config import config
from kiwoom_api import api
from db_manager import db_manager


def _ensure_scan_rank_table(cursor) -> None:
    """scan_rank 테이블 생성 (실제 DB 스키마와 일치: DATE 타입 사용)"""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scan_rank(
            date DATE NOT NULL,
            code TEXT NOT NULL,
            name TEXT,
            score DOUBLE PRECISION,
            flags TEXT,
            score_label TEXT,
            close_price DOUBLE PRECISION,
            volume DOUBLE PRECISION,
            change_rate DOUBLE PRECISION,
            scanner_version TEXT NOT NULL DEFAULT 'v1',
            PRIMARY KEY (date, code, scanner_version)
        )
    """)
    
    # 기존 테이블에 scanner_version 컬럼이 없으면 추가 (마이그레이션)
    cursor.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'scan_rank' AND column_name = 'scanner_version'
            ) THEN
                ALTER TABLE scan_rank ADD COLUMN scanner_version TEXT NOT NULL DEFAULT 'v1';
                ALTER TABLE scan_rank DROP CONSTRAINT IF EXISTS scan_rank_pkey;
                ALTER TABLE scan_rank ADD CONSTRAINT scan_rank_pkey PRIMARY KEY (date, code, scanner_version);
            END IF;
        END $$;
    """)


def get_recurrence_data(tickers: List[str], today_as_of: str) -> Dict[str, Dict]:
    """재등장 이력 조회 (배치 처리)"""
    recurrence_data = {}
    
    if not tickers:
        return recurrence_data
    
    try:
        from date_helper import yyyymmdd_to_date, timestamp_to_yyyymmdd
        
        with db_manager.get_cursor(commit=False) as cur_hist:
            _ensure_scan_rank_table(cur_hist)
            cur_hist.execute("""
                SELECT code, date
                FROM scan_rank
                WHERE code = ANY(%s)
                ORDER BY code, date DESC
            """, (tickers,))
            rows = cur_hist.fetchall()
        
        # today_as_of를 date 객체로 변환 (비교용)
        today_date_obj = yyyymmdd_to_date(today_as_of)
        
        # 결과를 종목별로 그룹화
        for ticker in tickers:
            prev_dates = []
            for row in rows:
                if row["code"] == ticker:
                    row_date = row["date"]
                    # date 객체인 경우 그대로 비교, 문자열인 경우 변환
                    if isinstance(row_date, str):
                        try:
                            row_date_obj = yyyymmdd_to_date(row_date)
                        except ValueError:
                            continue
                    elif hasattr(row_date, 'date'):
                        row_date_obj = row_date.date()
                    else:
                        row_date_obj = row_date
                    
                    if row_date_obj < today_date_obj:
                        # date 객체를 YYYYMMDD 문자열로 변환
                        if hasattr(row_date, 'strftime'):
                            prev_dates.append(row_date.strftime('%Y%m%d'))
                        else:
                            prev_dates.append(str(row_date))
            if prev_dates:
                last_as_of = prev_dates[0]
                first_as_of = prev_dates[-1]
                try:
                    days_since_last = int((pd.to_datetime(today_as_of) - pd.to_datetime(last_as_of)).days)
                except Exception:
                    days_since_last = None
                recurrence_data[ticker] = {
                    'appeared_before': True,
                    'appear_count': len(prev_dates),
                    'last_as_of': last_as_of,
                    'first_as_of': first_as_of,
                    'days_since_last': days_since_last,
                }
            else:
                recurrence_data[ticker] = {
                    'appeared_before': False,
                    'appear_count': 0,
                    'last_as_of': None,
                    'first_as_of': today_as_of,
                    'days_since_last': None,
                }
    except Exception as e:
        print(f"재등장 이력 조회 오류: {e}")
        # 오류 시 기본값 설정
        for ticker in tickers:
            recurrence_data[ticker] = {
                'appeared_before': False,
                'appear_count': 0,
                'last_as_of': None,
                'first_as_of': today_as_of,
                'days_since_last': None,
            }
    
    return recurrence_data


def save_scan_snapshot(scan_items: List[Dict], today_as_of: str, scanner_version: str = None) -> None:
    """스캔 스냅샷 저장 (returns, recurrence 포함)
    
    Args:
        scan_items: 스캔 결과 리스트 (returns, recurrence 포함 가능)
        today_as_of: 스캔 날짜 (YYYYMMDD)
        scanner_version: 스캐너 버전 (v1 또는 v2), None이면 현재 활성화된 버전 사용
    """
    try:
        from date_helper import yyyymmdd_to_date
        
        # YYYYMMDD 문자열을 date 객체로 변환
        date_obj = yyyymmdd_to_date(today_as_of)
        
        # 스캐너 버전 결정 (없으면 현재 활성화된 버전 사용)
        if scanner_version is None:
            try:
                from scanner_settings_manager import get_scanner_version
                scanner_version = get_scanner_version()
            except Exception:
                from config import config
                scanner_version = getattr(config, 'scanner_version', 'v1')
        
        # 버전 검증
        if scanner_version not in ['v1', 'v2']:
            scanner_version = 'v1'
        
        with db_manager.get_cursor(commit=True) as cur_hist:
            _ensure_scan_rank_table(cur_hist)
        
            enhanced_rank = []
            for it in scan_items:
                try:
                    # 스캔 결과에 이미 포함된 종가와 등락률 우선 사용
                    indicators = it.get("indicators", {})
                    # indicators가 객체인 경우 dict로 변환
                    if not isinstance(indicators, dict):
                        if hasattr(indicators, '__dict__'):
                            indicators = indicators.__dict__
                        elif hasattr(indicators, 'get'):
                            # 이미 dict-like 객체
                            pass
                        else:
                            indicators = {}
                    
                    scan_close = indicators.get("close") if isinstance(indicators, dict) else getattr(indicators, "close", None)
                    scan_change_rate = indicators.get("change_rate") if isinstance(indicators, dict) else getattr(indicators, "change_rate", None)
                    
                    # change_rate 변환: 스캐너 v2는 소수 형태로 반환 (예: 0.0596 = 5.96%)
                    # 이미 퍼센트 형태인 경우(절대값 >= 1.0)는 그대로 사용, 소수 형태(절대값 < 1.0)는 100 곱하기
                    if scan_change_rate is not None:
                        scan_change_rate = float(scan_change_rate)
                        # 소수 형태인지 확인 (절대값이 1보다 작고 0이 아닌 경우)
                        # 단, -1.0 ~ 1.0 범위는 소수 형태로 간주 (예: 0.0596, -0.67)
                        # 1.0 이상은 이미 퍼센트 형태로 간주 (예: 5.96, -67.0)
                        if abs(scan_change_rate) < 1.0 and scan_change_rate != 0.0:
                            scan_change_rate = scan_change_rate * 100
                    
                    # 스캔 결과에 종가와 등락률이 있으면 사용
                    if scan_close is not None and scan_change_rate is not None:
                        # volume은 별도로 가져오기 (스캔 결과에 없을 수 있음)
                        try:
                            df = api.get_ohlcv(it["ticker"], 1, today_as_of)
                            volume = float(df.iloc[-1]["volume"]) if not df.empty else 0.0
                        except Exception:
                            volume = float(indicators.get("VOL", 0))
                        
                        enhanced_rank.append({
                            "date": date_obj,
                            "code": it["ticker"],
                            "name": it["name"],
                            "score": it["score"],
                            "flags": json.dumps(it["flags"], ensure_ascii=False),
                            "score_label": it["score_label"],
                            "close_price": float(scan_close),
                            "volume": volume,
                            "change_rate": round(float(scan_change_rate), 2),  # 퍼센트로 저장, 소수점 2자리
                            "scanner_version": scanner_version,
                        })
                    else:
                        # 스캔 결과에 없으면 API로 계산 (fallback)
                        df = api.get_ohlcv(it["ticker"], 2, today_as_of)
                        if not df.empty:
                            latest = df.iloc[-1]
                            prev = df.iloc[-2] if len(df) > 1 else None
                            # 등락률을 퍼센트로 계산
                            change_rate = ((latest.close - prev.close) / prev.close * 100) if prev is not None and prev.close > 0 else 0.0
                            # returns와 recurrence 데이터 포함
                            returns_data = it.get("returns", {})
                            recurrence_data = it.get("recurrence", {})
                            
                            enhanced_rank.append({
                                "date": date_obj,
                                "code": it["ticker"],
                                "name": it["name"],
                                "score": it["score"],
                                "flags": json.dumps(it["flags"], ensure_ascii=False),
                                "score_label": it["score_label"],
                                "close_price": float(latest.close),
                                "volume": float(latest.volume),
                                "change_rate": round(float(change_rate), 2),
                                "returns": json.dumps(returns_data, ensure_ascii=False) if returns_data else None,
                                "recurrence": json.dumps(recurrence_data, ensure_ascii=False) if recurrence_data else None,
                                "strategy": it.get("strategy") or (it.get("flags", {}).get("trading_strategy") if isinstance(it.get("flags"), dict) else None),
                                "scanner_version": scanner_version,
                            })
                except Exception as e:
                    logger.debug(f"스캔 결과 저장 중 오류 ({it.get('ticker', 'unknown')}): {e}")
                    continue
        
            # 해당 날짜와 버전의 기존 데이터 삭제 (date 객체 사용)
            cur_hist.execute("DELETE FROM scan_rank WHERE date = %s AND scanner_version = %s", 
                           (date_obj, scanner_version))
            
            if not scan_items:
                print(f"📭 스캔 결과 0개 - NORESULT 레코드 저장: {today_as_of} (버전: {scanner_version})")
                cur_hist.execute(
                    """
                    INSERT INTO scan_rank (date, code, name, score, flags, score_label, close_price, volume, change_rate, scanner_version)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (date_obj, "NORESULT", "추천종목 없음", 0.0, json.dumps({"no_result": True}, ensure_ascii=False),
                     "추천종목 없음", 0.0, 0.0, 0.0, scanner_version)
                )
            elif enhanced_rank:
                cur_hist.executemany("""
                    INSERT INTO scan_rank (date, code, name, score, flags, score_label, close_price, volume, change_rate, returns, recurrence, strategy, scanner_version)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, [
                    (
                        r["date"], r["code"], r["name"], r["score"], r["flags"],
                        r["score_label"], r["close_price"], r["volume"], r["change_rate"],
                        r.get("returns"), r.get("recurrence"), r.get("strategy"), r["scanner_version"]
                    )
                    for r in enhanced_rank
                ])
                print(f"✅ 스캔 결과 저장 완료: {len(enhanced_rank)}개 종목 (날짜: {today_as_of}, 버전: {scanner_version})")
            else:
                print(f"📭 enhanced_rank 비어있음 - NORESULT 레코드 저장: {today_as_of} (버전: {scanner_version})")
                cur_hist.execute(
                    """
                    INSERT INTO scan_rank (date, code, name, score, flags, score_label, close_price, volume, change_rate, scanner_version)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (date_obj, "NORESULT", "추천종목 없음", 0.0, json.dumps({"no_result": True}, ensure_ascii=False),
                     "추천종목 없음", 0.0, 0.0, 0.0, scanner_version)
                )
    except Exception as e:
        print(f"스냅샷 저장 오류: {e}")
        import traceback
        traceback.print_exc()


def execute_scan_with_fallback(universe: List[str], date: Optional[str] = None, market_condition=None) -> tuple:
    """Fallback 로직을 적용한 스캔 실행 (하이브리드 접근: 10점 이상 우선, 없으면 8점 이상 Fallback)
    
    Returns:
        tuple: (items, chosen_step, scanner_version)
            - items: 스캔 결과 리스트
            - chosen_step: 선택된 fallback step
            - scanner_version: 사용된 스캐너 버전 (v1 또는 v2)
    """
    chosen_step = None
    
    # 현재 사용된 스캐너 버전 확인 (함수 시작 시)
    try:
        from scanner_settings_manager import get_scanner_version
        current_scanner_version = get_scanner_version()
    except Exception:
        # config는 이미 파일 상단에서 import됨
        current_scanner_version = getattr(config, 'scanner_version', 'v1')
    
    # v4 장세 분석 시도 (v3 fallback)
    if market_condition is None:
        try:
            from market_analyzer import market_analyzer
            market_condition = market_analyzer.analyze_market_condition_v4(date, mode="backtest")
            if market_condition.version == "regime_v4":
                print(f"📊 Global Regime v4 사용: {market_condition.final_regime} (trend: {market_condition.global_trend_score:.2f}, risk: {market_condition.global_risk_score:.2f})")
            elif market_condition.version == "regime_v3":
                print(f"📊 Global Regime v3 fallback: {market_condition.final_regime} (점수: {market_condition.final_score:.2f})")
            else:
                print(f"📊 v1 fallback 사용: {market_condition.market_sentiment}")
        except Exception as e:
            print(f"⚠️ 장세 분석 실패, 기본 조건 사용: {e}")
    
    # 급락장/crash 감지 로그 (스캔은 계속 진행, cutoff로 제어)
    crash_detected = False
    if market_condition:
        if hasattr(market_condition, 'final_regime') and market_condition.final_regime == 'crash':
            crash_detected = True
            print(f"🔴 Global Regime v4 급락장 감지 - longterm horizon만 허용")
        elif hasattr(market_condition, 'midterm_regime') and market_condition.midterm_regime == 'crash':
            crash_detected = True
            print(f"🔴 급락장 감지 (midterm_regime=crash) - longterm horizon만 허용")
        elif market_condition.market_sentiment == 'crash':
            crash_detected = True
            kospi_return = getattr(market_condition, 'kospi_return', 0.0)
            print(f"🔴 급락장 감지 (KOSPI: {kospi_return:.2f}%) - longterm horizon만 허용")
    
    # crash여도 스캔은 진행 (cutoff로 swing/position 차단, longterm만 허용)
    
    # 약세장에서도 fallback 활성화하되, 장세별 목표 개수 적용
    use_fallback = config.fallback_enable
    
    # 장세별 목표 개수 설정 (v3 final_regime 우선 사용)
    current_regime = 'neutral'
    if market_condition:
        if hasattr(market_condition, 'final_regime') and market_condition.final_regime:
            current_regime = market_condition.final_regime
        else:
            current_regime = market_condition.market_sentiment
    
    if current_regime == 'bear':
        target_min = max(1, config.fallback_target_min_bear)
        target_max = max(target_min, config.fallback_target_max_bear)
        print(f"⚠️ {current_regime} 장세 감지 - Fallback 활성화, 목표: {target_min}~{target_max}개")
    else:
        target_min = max(1, config.fallback_target_min_bull)
        target_max = max(target_min, config.fallback_target_max_bull)
        print(f"📈 {current_regime} 장세 - Fallback 활성화, 목표: {target_min}~{target_max}개")
    
    print(f"🔄 하이브리드 Fallback 로직 시작: universe={len(universe)}개, fallback_enable={use_fallback}")
    
    if not use_fallback:
        # Fallback 비활성화 시 기존 로직 (10점 이상만)
        print(f"📊 Fallback 비활성화 - 시장 상황 기반 조건으로 스캔 (10점 이상만)")
        try:
            items = scan_with_scanner(universe, {}, date, market_condition)
        except Exception as e:
            print(f"❌ 스캔 오류: {e}")
            return [], None, current_scanner_version
        # 10점 이상만 필터링
        items_10_plus = [item for item in items if item.get("score", 0) >= 10]
        items = items_10_plus[:config.top_k]
        chosen_step = 0  # 기본 조건 사용
        print(f"📊 스캔 결과: {len(items)}개 종목 (10점 이상만, 조건 강화)")
    else:
        # 통합 Fallback: 점수와 지표를 동시에 Fallback
        print(f"📊 통합 Fallback 활성화 - 목표: 최소 {target_min}개, 최대 {target_max}개")
        
        final_items = []
        chosen_step = None  # 명확한 초기값
        
        # Step 0: 기본 조건 (10점 이상만, 지표 완화 없음)
        print(f"🔄 Step 0: 기본 조건 (10점 이상만)")
        try:
            step0_items = scan_with_scanner(universe, {}, date, market_condition)
        except Exception as e:
            print(f"❌ Step 0 스캔 오류: {e}")
            return [], None, current_scanner_version
        # 신호 우선 원칙: 신호 충족 = 후보군 (점수 무관), 점수 = 순위 매기기용
        step0_items_filtered = []
        for item in step0_items:
            matched = item.get("match", False)
            
            # 신호 충족 = 후보군 (점수 무관하게 포함)
            # 신호 미충족 = 제외 (점수와 무관)
            if matched:
                step0_items_filtered.append(item)
        
        # 점수 순으로 정렬 (높은 점수 우선)
        step0_items_filtered.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        step0_items_10_plus = step0_items_filtered
        print(f"📊 Step 0 결과: {len(step0_items_10_plus)}개 종목 (신호 충족만, 점수=순위)")
        
        if len(step0_items_10_plus) >= target_min:
            chosen_step = 0
            final_items = step0_items_10_plus[:min(config.top_k, target_max)]
            print(f"✅ Step 0에서 목표 달성: {len(final_items)}개 종목 선택 (10점 이상만)")
        else:
            # Step 1: 지표 완화 Level 1 + 10점 이상
            print(f"🔄 Step 1: 지표 완화 Level 1 + 10점 이상")
            try:
                if len(config.fallback_presets) < 2:
                    print(f"❌ fallback_presets 인덱스 오류: Step 1 프리셋 없음")
                    return [], None, current_scanner_version
                step1_items = scan_with_scanner(universe, config.fallback_presets[1], date, market_condition)
            except Exception as e:
                print(f"❌ Step 1 스캔 오류: {e}")
                return [], None, current_scanner_version
            # 신호 우선 원칙: 신호 충족 = 후보군 (점수 무관), 점수 = 순위 매기기용
            step1_items_filtered = []
            for item in step1_items:
                matched = item.get("match", False)
                
                # 신호 충족 = 후보군 (점수 무관하게 포함)
                if matched:
                    step1_items_filtered.append(item)
            
            # 점수 순으로 정렬
            step1_items_filtered.sort(key=lambda x: x.get("score", 0), reverse=True)
            
            step1_items_10_plus = step1_items_filtered
            print(f"📊 Step 1 결과: {len(step1_items_10_plus)}개 종목 (지표 완화 + 신호 충족만, 점수=순위)")
            
            if len(step1_items_10_plus) >= target_min:
                chosen_step = 1
                final_items = step1_items_10_plus[:min(config.top_k, target_max)]
                print(f"✅ Step 1에서 목표 달성: {len(final_items)}개 종목 선택 (지표 완화 + 10점 이상)")
            else:
                # Step 2: 지표 완화 Level 1 (신호 우선 원칙 유지)
                print(f"🔄 Step 2: 지표 완화 Level 1 (신호 충족 종목만)")
                step1_items_8_plus = []
                for item in step1_items:
                    matched = item.get("match", False)
                    
                    # 신호 충족 = 후보군 (점수 무관하게 포함)
                    if matched:
                        step1_items_8_plus.append(item)
                
                # 점수 순으로 정렬
                step1_items_8_plus.sort(key=lambda x: x.get("score", 0), reverse=True)
                
                print(f"📊 Step 2 결과: {len(step1_items_8_plus)}개 종목 (지표 완화 + 신호 충족만, 점수=순위)")
                
                if len(step1_items_8_plus) >= target_min:
                    chosen_step = 2
                    final_items = step1_items_8_plus[:min(config.top_k, target_max)]
                    print(f"✅ Step 2에서 목표 달성: {len(final_items)}개 종목 선택 (지표 완화 + 8점 이상)")
                else:
                    # Step 3: 지표 추가 완화 + 8점 이상 (Step 3까지만 시도)
                    print(f"⚠️ Step 2에서 목표 미달 - 지표 추가 완화 시도 (Step 3까지만)")
                    
                    # Step 3: 지표 추가 완화 + 8점 이상
                    print(f"🔄 Step 3: 지표 완화 Level 2 + 8점 이상")
                    try:
                        if len(config.fallback_presets) < 3:
                            print(f"❌ fallback_presets 인덱스 오류: Step 3 프리셋 없음")
                            final_items = []
                            chosen_step = None
                        else:
                            step3_overrides = config.fallback_presets[2]
                            print(f"   설정: {step3_overrides}")
                            step3_items = scan_with_scanner(universe, step3_overrides, date, market_condition)
                            # Step 3: 신호 충족 = 점수 무관, 미충족 = 8점 이상
                            step3_items_8_plus = []
                            for item in step3_items:
                                flags = item.get("flags", {})
                                score = item.get("score", 0)
                                matched = item.get("match", False)
                                fallback = flags.get("fallback", False)
                                
                                # 신호 충족 = 후보군 (점수 무관하게 포함)
                                # 신호 미충족 = 점수 기준 완화 (8점 이상)
                                if matched:  # 신호 충족으로 매칭된 경우
                                    step3_items_8_plus.append(item)
                                elif fallback or score >= 8:  # 신호 미충족이지만 점수 높은 경우
                                    step3_items_8_plus.append(item)
                            
                            # 점수 순으로 정렬
                            step3_items_8_plus.sort(key=lambda x: x.get("score", 0), reverse=True)
                            
                            print(f"📊 Step 3 결과: {len(step3_items_8_plus)}개 종목 (지표 완화 Level 2 + 신호 충족만, 점수=순위)")
                            
                            if len(step3_items_8_plus) >= target_min:
                                chosen_step = 3
                                final_items = step3_items_8_plus[:min(config.top_k, target_max)]
                                print(f"✅ Step 3에서 목표 달성: {len(final_items)}개 종목 선택")
                            else:
                                print(f"❌ Step 3 목표 미달: {len(step3_items_8_plus)} < {target_min}")
                    except Exception as e:
                        print(f"❌ Step 3 스캔 오류: {e}")
                        final_items = []
                        chosen_step = None
                    
                    # Step 3에서도 목표 미달이면 빈 리스트 반환 (Step 7 제거)
                    if not final_items:
                        print(f"⚠️ Step 0~3 모두 목표 미달 - 추천 종목 없음 (품질 저하 방지)")
                        print(f"🔍 디버깅: universe={len(universe)}개, market_condition={market_condition}")
                        final_items = []
                        chosen_step = None
        
        items = final_items
    
    print(f"🎯 최종 선택: Step {chosen_step}, {len(items)}개 종목")
    return items, chosen_step, current_scanner_version

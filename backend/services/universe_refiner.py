"""
정제된 유니버스 생성 모듈

기존 유니버스(KOSPI, KOSDAQ 거래대금 상위 100개씩 = 200개)를 유지하되,
전략과 구조적으로 맞지 않는 종목을 사전에 제거한 "정제된 유니버스 200"을 생성한다.

이 모듈은 전략 개선이 아니라, 입력 데이터 품질 관리다.
"""
from typing import List, Dict, Set, Optional
from datetime import datetime, timedelta
import logging
import json
from pathlib import Path

logger = logging.getLogger(__name__)

# ETF 키워드 리스트
ETF_KEYWORDS = ["KODEX", "TIGER", "KBSTAR", "ARIRANG", "HANARO", "KOSEF"]

# 임시 제외 목록 파일 경로
EXCLUSION_LIST_PATH = Path(__file__).parent.parent / "cache" / "universe_exclusions.json"


class UniverseRefiner:
    """정제된 유니버스 생성 클래스"""
    
    def __init__(self, kospi_limit: int = 100, kosdaq_limit: int = 100):
        """
        Args:
            kospi_limit: KOSPI 상위 종목 수
            kosdaq_limit: KOSDAQ 상위 종목 수
        """
        self.kospi_limit = kospi_limit
        self.kosdaq_limit = kosdaq_limit
        self.exclusion_list = self._load_exclusion_list()
    
    def generate_refined_universe(self, date: str = None) -> List[str]:
        """
        정제된 유니버스 생성
        
        절차:
        1. 기본 유니버스 생성 (KOSPI 100 + KOSDAQ 100 = 200개)
        2. ETF 완전 제외
        3. 추세 불가능 종목 제거 (20일 변동폭 < 7%)
        4. 경험적 부적합 종목 임시 제외 (NEUTRAL 2회 이상 또는 stop_loss 2회 이상)
        
        Args:
            date: 기준일 (YYYYMMDD), None이면 오늘 날짜 사용
        
        Returns:
            정제된 유니버스 종목 코드 리스트
        """
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
        
        from kiwoom_api import api
        
        logger.info(f"정제된 유니버스 생성 시작: {date}")
        
        # STEP 1: 기본 유니버스 생성
        kospi_codes = api.get_top_codes("KOSPI", limit=self.kospi_limit)
        kosdaq_codes = api.get_top_codes("KOSDAQ", limit=self.kosdaq_limit)
        base_universe = sorted(set([*kospi_codes, *kosdaq_codes]))
        
        logger.info(f"STEP 1: 기본 유니버스 생성 완료 - {len(base_universe)}개 종목 (KOSPI {len(kospi_codes)}개 + KOSDAQ {len(kosdaq_codes)}개)")
        
        # STEP 2: ETF 완전 제외
        universe_after_etf = self._remove_etf(base_universe, api)
        etf_removed = len(base_universe) - len(universe_after_etf)
        logger.info(f"STEP 2: ETF 제외 완료 - {etf_removed}개 제거, {len(universe_after_etf)}개 남음")
        
        # STEP 3: 추세 불가능 종목 제거
        universe_after_volatility = self._remove_low_volatility_stocks(universe_after_etf, date, api)
        volatility_removed = len(universe_after_etf) - len(universe_after_volatility)
        logger.info(f"STEP 3: 추세 불가능 종목 제거 완료 - {volatility_removed}개 제거, {len(universe_after_volatility)}개 남음")
        
        # STEP 4: 경험적 부적합 종목 임시 제외
        universe_final = self._apply_experience_based_exclusions(universe_after_volatility, date)
        exclusion_removed = len(universe_after_volatility) - len(universe_final)
        logger.info(f"STEP 4: 경험적 부적합 종목 제외 완료 - {exclusion_removed}개 제거, {len(universe_final)}개 남음")
        
        logger.info(f"최종 정제된 유니버스: {len(universe_final)}개 종목")
        
        return universe_final
    
    def _remove_etf(self, universe: List[str], api) -> List[str]:
        """
        STEP 2: ETF 완전 제외
        
        ETF는 단기 추세 형성이 어려워 본 전략 유니버스에서 제외한다.
        
        제외 조건:
        - 종목명에 ETF 키워드 포함: ["KODEX", "TIGER", "KBSTAR", "ARIRANG", "HANARO", "KOSEF"]
        """
        filtered = []
        for code in universe:
            try:
                stock_name = api.get_stock_name(code)
                # ETF 키워드 체크
                is_etf = any(keyword in stock_name for keyword in ETF_KEYWORDS)
                if not is_etf:
                    filtered.append(code)
            except Exception as e:
                logger.debug(f"ETF 체크 실패 ({code}): {e}")
                # 체크 실패 시 일단 포함 (안전한 선택)
                filtered.append(code)
        
        return filtered
    
    def _remove_low_volatility_stocks(self, universe: List[str], date: str, api) -> List[str]:
        """
        STEP 3: 추세 불가능 종목 제거 (소프트 정제)
        
        단기 목표 수익률(약 5%)을 구조적으로 만들 수 없는 종목 제거.
        이는 시장 판단이나 레짐이 아니라 종목 물성 체크다.
        
        제외 조건:
        - 최근 20거래일 기준: (20일 최고가 - 20일 최저가) / 20일 최저가 < 0.07
        """
        filtered = []
        for code in universe:
            try:
                # 최근 20거래일 데이터 가져오기
                df = api.get_ohlcv(code, count=20, base_date=date)
                if df.empty or len(df) < 20:
                    # 데이터 부족 시 포함 (안전한 선택)
                    filtered.append(code)
                    continue
                
                # 20일 최고가/최저가 계산
                high_20 = df['high'].max()
                low_20 = df['low'].min()
                
                if low_20 <= 0:
                    filtered.append(code)
                    continue
                
                # 변동폭 계산: (최고가 - 최저가) / 최저가
                volatility_ratio = (high_20 - low_20) / low_20
                
                # 변동폭이 7% 이상인 종목만 포함
                if volatility_ratio >= 0.07:
                    filtered.append(code)
            except Exception as e:
                logger.debug(f"변동폭 체크 실패 ({code}): {e}")
                # 체크 실패 시 일단 포함 (안전한 선택)
                filtered.append(code)
        
        return filtered
    
    def _apply_experience_based_exclusions(self, universe: List[str], date: str) -> List[str]:
        """
        STEP 4: 경험적 부적합 종목 임시 제외
        
        본 전략과 단기적으로 궁합이 맞지 않음이 데이터로 확인된 종목 휴식.
        이 제외는 영구적이지 않으며, 20거래일 경과 시 자동으로 유니버스에 복귀 가능하다.
        
        제외 조건 (최근 3개월 내):
        - NEUTRAL(time_stop) 2회 이상
        - stop_loss 2회 이상
        """
        # 제외 목록 업데이트 (만료된 항목 제거)
        self._update_exclusion_list(date)
        
        # 제외 목록에 있는 종목 필터링
        filtered = [code for code in universe if code not in self.exclusion_list]
        
        return filtered
    
    def _load_exclusion_list(self) -> Set[str]:
        """임시 제외 목록 로드"""
        if not EXCLUSION_LIST_PATH.exists():
            return set()
        
        try:
            with open(EXCLUSION_LIST_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # {ticker: exclusion_date} 형태로 저장되어 있다고 가정
                exclusions = set(data.keys())
                return exclusions
        except Exception as e:
            logger.warning(f"제외 목록 로드 실패: {e}")
            return set()
    
    def _update_exclusion_list(self, current_date: str):
        """제외 목록 업데이트 (만료된 항목 제거)"""
        if not EXCLUSION_LIST_PATH.exists():
            return
        
        try:
            with open(EXCLUSION_LIST_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            current_dt = datetime.strptime(current_date, '%Y%m%d')
            updated_data = {}
            
            for ticker, exclusion_date_str in data.items():
                exclusion_dt = datetime.strptime(exclusion_date_str, '%Y%m%d')
                days_since_exclusion = (current_dt - exclusion_dt).days
                
                # 20거래일 = 약 28일 경과 시 제외 해제
                if days_since_exclusion < 28:
                    updated_data[ticker] = exclusion_date_str
            
            # 업데이트된 목록 저장
            EXCLUSION_LIST_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(EXCLUSION_LIST_PATH, 'w', encoding='utf-8') as f:
                json.dump(updated_data, f, ensure_ascii=False, indent=2)
            
            self.exclusion_list = set(updated_data.keys())
            
        except Exception as e:
            logger.warning(f"제외 목록 업데이트 실패: {e}")
    
    def add_to_exclusion_list(self, ticker: str, reason: str, date: str = None):
        """
        제외 목록에 종목 추가
        
        Args:
            ticker: 종목 코드
            reason: 제외 사유 ('NEUTRAL_2+' 또는 'STOP_LOSS_2+')
            date: 제외일 (YYYYMMDD), None이면 오늘 날짜 사용
        """
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
        
        try:
            # 기존 목록 로드
            if EXCLUSION_LIST_PATH.exists():
                with open(EXCLUSION_LIST_PATH, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {}
            
            # 새 항목 추가 (또는 업데이트)
            data[ticker] = date
            
            # 저장
            EXCLUSION_LIST_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(EXCLUSION_LIST_PATH, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            self.exclusion_list.add(ticker)
            logger.info(f"제외 목록 추가: {ticker} (사유: {reason}, 날짜: {date})")
            
        except Exception as e:
            logger.error(f"제외 목록 추가 실패 ({ticker}): {e}")


def generate_refined_universe(
    kospi_limit: int = 100,
    kosdaq_limit: int = 100,
    date: str = None
) -> List[str]:
    """
    정제된 유니버스 생성 (편의 함수)
    
    Args:
        kospi_limit: KOSPI 상위 종목 수
        kosdaq_limit: KOSDAQ 상위 종목 수
        date: 기준일 (YYYYMMDD), None이면 오늘 날짜 사용
    
    Returns:
        정제된 유니버스 종목 코드 리스트
    """
    refiner = UniverseRefiner(kospi_limit=kospi_limit, kosdaq_limit=kosdaq_limit)
    return refiner.generate_refined_universe(date=date)

























"""
Global Regime v3 설정 파일
"""

# 장세별 horizon cutoff 설정
REGIME_CUTOFFS = {
    'bull': {
        'swing': 6.0,      # 강세장에서 단기 매매 점수 기준
        'position': 4.3,   # 강세장에서 중기 포지션 점수 기준  
        'longterm': 5.0    # 강세장에서 장기 투자 점수 기준
    },
    'neutral': {
        'swing': 6.0,      # 중립장에서 단기 매매 점수 기준
        'position': 4.5,   # 중립장에서 중기 포지션 점수 기준
        'longterm': 6.0    # 중립장에서 장기 투자 점수 기준
    },
    'bear': {
        'swing': 999.0,    # 약세장에서 단기 매매 비활성화
        'position': 5.5,   # 약세장에서 중기 포지션 점수 기준 (보수적)
        'longterm': 6.0    # 약세장에서 장기 투자 점수 기준
    },
    'crash': {
        'swing': 999.0,    # 급락장에서 모든 매매 비활성화
        'position': 999.0, 
        'longterm': 999.0
    }
}

# horizon별 최대 후보 개수
MAX_CANDIDATES = {
    'swing': 20,     # 단기 매매 최대 20개
    'position': 15,  # 중기 포지션 최대 15개  
    'longterm': 20   # 장기 투자 최대 20개
}

# 장세 점수 계산 가중치
REGIME_WEIGHTS = {
    'kr_weight': 0.6,      # 한국 시장 가중치 60%
    'us_weight': 0.4,      # 미국 시장 가중치 40%
    'preopen_penalty': {   # pre-open 리스크 페널티
        'watch': 0.5,
        'danger': 1.0
    }
}

# 장세 구분 임계값
REGIME_THRESHOLDS = {
    'bull_min': 2.0,       # bull 최소 점수
    'bear_max': -2.0,      # bear 최대 점수
    'crash_conditions': {  # crash 조건
        'intraday_drop': -0.025,  # 장중 하락률 -2.5% 이하
        'vix_threshold': 35        # VIX 35 이상
    }
}
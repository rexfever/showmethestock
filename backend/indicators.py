import numpy as np
import pandas as pd


def ema(series: pd.Series, n: int) -> pd.Series:
    return series.ewm(span=n, adjust=False).mean()


def dema_smooth(series: pd.Series, n: int) -> pd.Series:
    e1 = ema(series, n)
    e2 = ema(e1, n)
    return 2 * e1 - e2


def tema_smooth(series: pd.Series, n: int) -> pd.Series:
    e1 = ema(series, n)
    e2 = ema(e1, n)
    e3 = ema(e2, n)
    return 3 * e1 - 3 * e2 + e3


def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    efast = ema(series, fast)
    eslow = ema(series, slow)
    macd_line = efast - eslow
    signal_line = ema(macd_line, signal)
    osc = macd_line - signal_line
    return macd_line, signal_line, osc


def rsi_standard(series: pd.Series, period: int = 14) -> pd.Series:
    chg = series.diff()
    up = chg.clip(lower=0)
    dn = (-chg).clip(lower=0)
    avg_up = ema(up, period)
    avg_dn = ema(dn, period)
    rs = avg_up / (avg_dn.replace(0, np.nan))
    rsi = 100 - 100 / (1 + rs)
    return rsi.fillna(50)


def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    sign = np.sign(close.diff().fillna(0))
    return (sign * volume).fillna(0).cumsum()


def rsi_tema(series: pd.Series, period: int) -> pd.Series:
    chg = series.diff()
    up = chg.clip(lower=0)
    dn = (-chg).clip(lower=0)
    up_s = tema_smooth(up.fillna(0), period)
    dn_s = tema_smooth(dn.fillna(0), period)
    rs = up_s / (dn_s.replace(0, np.nan))
    rsi = 100 - 100 / (1 + rs)
    return rsi.fillna(50)


def rsi_dema(series: pd.Series, period: int) -> pd.Series:
    chg = series.diff()
    up = chg.clip(lower=0)
    dn = (-chg).clip(lower=0)
    up_s = dema_smooth(up.fillna(0), period)
    dn_s = dema_smooth(dn.fillna(0), period)
    rs = up_s / (dn_s.replace(0, np.nan))
    rsi = 100 - 100 / (1 + rs)
    return rsi.fillna(50)



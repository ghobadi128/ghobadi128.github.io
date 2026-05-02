"""
Shared utility functions used across the MarketScintillation pipeline.
"""

import logging
import sys
from typing import Optional

import numpy as np
import pandas as pd
from scipy.signal import butter, filtfilt


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Return a consistently formatted logger."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        fmt = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(fmt)
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger


# ---------------------------------------------------------------------------
# Signal processing utilities
# ---------------------------------------------------------------------------

def high_pass_filter(
    series: np.ndarray,
    cutoff_frac: float = 0.05,
    order: int = 4,
) -> np.ndarray:
    """
    Zero-phase Butterworth high-pass filter.

    Analogous to the ionospheric detrending filter used in GNSS scintillation
    studies: removes low-frequency (carrier / trend) component so only the
    high-frequency fluctuation (scintillation) remains.

    Parameters
    ----------
    series : array-like
        Input 1-D signal.
    cutoff_frac : float
        Cut-off as fraction of Nyquist (0 < cutoff_frac < 1).
    order : int
        Filter order.
    """
    if len(series) < 2 * order + 1:
        return series - np.mean(series)
    b, a = butter(order, cutoff_frac, btype="high", analog=False)
    return filtfilt(b, a, series)


def rolling_detrend(
    series: pd.Series,
    window: int,
    min_periods: int = 5,
) -> pd.Series:
    """
    Subtract a rolling mean trend from a series (adaptive moving-average detrend).

    This mirrors the polynomial / moving-average detrending applied to GNSS
    carrier-phase data before computing σφ.
    """
    trend = series.rolling(window=window, min_periods=min_periods, center=False).mean()
    return series - trend


def rolling_apply_min(
    series: pd.Series,
    window: int,
    func,
    min_periods: int = 5,
) -> pd.Series:
    """Rolling apply with a minimum period guard."""
    return series.rolling(window=window, min_periods=min_periods).apply(func, raw=True)


# ---------------------------------------------------------------------------
# Financial helpers
# ---------------------------------------------------------------------------

def log_returns(prices: pd.Series) -> pd.Series:
    """Compute log returns from price series."""
    return np.log(prices / prices.shift(1))


def realized_vol(
    returns: pd.Series,
    window: int,
    min_periods: int = 5,
    annualize: bool = False,
    bars_per_year: int = 252 * 23400,  # 1-second bars
) -> pd.Series:
    """
    Rolling realized volatility (std of log returns).

    Parameters
    ----------
    annualize : bool
        If True, scale to annualized vol assuming ``bars_per_year`` bars.
    """
    rv = returns.rolling(window=window, min_periods=min_periods).std()
    if annualize:
        rv = rv * np.sqrt(bars_per_year)
    return rv


def sharpe_ratio(
    returns: pd.Series,
    risk_free: float = 0.0,
    periods_per_year: int = 252,
) -> float:
    """Annualized Sharpe ratio."""
    excess = returns - risk_free / periods_per_year
    if excess.std() == 0:
        return 0.0
    return float(excess.mean() / excess.std() * np.sqrt(periods_per_year))


def sortino_ratio(
    returns: pd.Series,
    risk_free: float = 0.0,
    periods_per_year: int = 252,
) -> float:
    """Annualized Sortino ratio."""
    excess = returns - risk_free / periods_per_year
    downside = excess[excess < 0].std()
    if downside == 0:
        return 0.0
    return float(excess.mean() / downside * np.sqrt(periods_per_year))


def max_drawdown(equity: pd.Series) -> float:
    """Maximum peak-to-trough drawdown as a fraction."""
    roll_max = equity.cummax()
    dd = (equity - roll_max) / roll_max
    return float(dd.min())


def calmar_ratio(
    returns: pd.Series,
    equity: pd.Series,
    periods_per_year: int = 252,
) -> float:
    """Calmar ratio = annualized return / |max drawdown|."""
    ann_ret = float(returns.mean() * periods_per_year)
    mdd = abs(max_drawdown(equity))
    if mdd == 0:
        return np.inf
    return ann_ret / mdd


def compute_performance_metrics(
    returns: pd.Series,
    equity: pd.Series,
    label: str = "Strategy",
    periods_per_year: int = 252,
) -> dict:
    """Bundle all performance metrics into a dict."""
    n_trades = int((returns != 0).sum())
    win_rate = float((returns > 0).sum() / max(n_trades, 1))
    return {
        "label": label,
        "total_return_pct": float((equity.iloc[-1] / equity.iloc[0] - 1) * 100),
        "sharpe": sharpe_ratio(returns, periods_per_year=periods_per_year),
        "sortino": sortino_ratio(returns, periods_per_year=periods_per_year),
        "max_drawdown_pct": float(max_drawdown(equity) * 100),
        "calmar": calmar_ratio(returns, equity, periods_per_year=periods_per_year),
        "n_trades": n_trades,
        "win_rate_pct": float(win_rate * 100),
        "ann_vol_pct": float(returns.std() * np.sqrt(periods_per_year) * 100),
    }

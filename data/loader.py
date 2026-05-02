"""
High-Frequency Data Loader
==========================
Fetches tick-level or 1-second aggregated OHLCV data.

Primary source  : Polygon.io REST API (requires API key)
Fallback source : yfinance  (minute-bar granularity)

The output is always a tidy DataFrame with columns:
    timestamp (DatetimeIndex, UTC-aware)
    open, high, low, close, volume, vwap (where available)
    returns   – log returns on close
"""

from __future__ import annotations

import os
import time
from datetime import date, datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd
import requests

from utils.helpers import get_logger, log_returns
from config import POLYGON_API_KEY, YFINANCE_FALLBACK

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Column schema expected downstream
# ---------------------------------------------------------------------------
REQUIRED_COLS = ["open", "high", "low", "close", "volume"]


# ---------------------------------------------------------------------------
# Polygon.io loader
# ---------------------------------------------------------------------------

class PolygonLoader:
    """
    Load aggregated bars (timespan=second or minute) from Polygon.io.

    Polygon free tier allows 5 API calls/minute; Starter/higher tiers
    have no rate limit.  We include a small backoff on 429 responses.
    """

    BASE_URL = "https://api.polygon.io/v2/aggs/ticker"

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or os.environ.get("POLYGON_API_KEY", POLYGON_API_KEY)
        if self.api_key == "YOUR_POLYGON_API_KEY":
            logger.warning(
                "Polygon API key not set. Set POLYGON_API_KEY env var or edit config.py."
            )

    def fetch(
        self,
        ticker: str,
        start: str,
        end: str,
        timespan: str = "second",
        multiplier: int = 1,
        limit: int = 50_000,
    ) -> pd.DataFrame:
        """
        Parameters
        ----------
        ticker     : e.g. "TSLA", "NVDA"
        start/end  : "YYYY-MM-DD"
        timespan   : "second" | "minute" | "hour" | "day"
        multiplier : bar size multiplier (1 second, 5 minutes, …)
        limit      : max bars per Polygon request (max 50,000)
        """
        all_results: list[dict] = []
        url = (
            f"{self.BASE_URL}/{ticker}/range/{multiplier}/{timespan}"
            f"/{start}/{end}"
        )
        params = {
            "adjusted": "true",
            "sort": "asc",
            "limit": limit,
            "apiKey": self.api_key,
        }

        while url:
            try:
                resp = requests.get(url, params=params, timeout=30)
            except requests.RequestException as exc:
                logger.error("Polygon request failed: %s", exc)
                break

            if resp.status_code == 429:
                logger.warning("Rate limited by Polygon. Sleeping 60 s …")
                time.sleep(60)
                continue

            if resp.status_code != 200:
                logger.error(
                    "Polygon returned HTTP %s: %s", resp.status_code, resp.text[:200]
                )
                break

            data = resp.json()
            results = data.get("results", [])
            all_results.extend(results)
            logger.info("Fetched %d bars (total %d)", len(results), len(all_results))

            # Polygon paginates via next_url
            url = data.get("next_url")
            params = {"apiKey": self.api_key}  # next_url already contains other params

        if not all_results:
            logger.warning("No data returned from Polygon for %s", ticker)
            return pd.DataFrame()

        return self._to_dataframe(all_results)

    @staticmethod
    def _to_dataframe(results: list[dict]) -> pd.DataFrame:
        df = pd.DataFrame(results)
        df["timestamp"] = pd.to_datetime(df["t"], unit="ms", utc=True)
        df = df.rename(
            columns={
                "o": "open",
                "h": "high",
                "l": "low",
                "c": "close",
                "v": "volume",
                "vw": "vwap",
                "n": "n_trades",
            }
        )
        cols = [c for c in ["timestamp", "open", "high", "low", "close", "volume", "vwap", "n_trades"] if c in df.columns]
        df = df[cols].set_index("timestamp").sort_index()
        return df


# ---------------------------------------------------------------------------
# yfinance fallback loader
# ---------------------------------------------------------------------------

class YFinanceLoader:
    """
    Fallback loader using yfinance (minute-bar resolution max).
    Produces the same column schema as PolygonLoader.
    """

    def fetch(
        self,
        ticker: str,
        start: str,
        end: str,
        interval: str = "1m",
    ) -> pd.DataFrame:
        """
        Parameters
        ----------
        interval : "1m" | "2m" | "5m" | "15m" | "30m" | "60m" | "1d"
                   yfinance only supports up to 60-day history for sub-hour intervals.
        """
        try:
            import yfinance as yf
        except ImportError as exc:
            raise ImportError("Install yfinance: pip install yfinance") from exc

        logger.info("Fetching %s from yfinance (%s bars, %s to %s)", ticker, interval, start, end)
        tk = yf.Ticker(ticker)
        df = tk.history(start=start, end=end, interval=interval, auto_adjust=True)

        if df.empty:
            logger.warning("yfinance returned empty DataFrame for %s", ticker)
            return df

        df.index = pd.to_datetime(df.index, utc=True)
        df.index.name = "timestamp"
        df.columns = [c.lower() for c in df.columns]
        df = df.rename(columns={"dividends": "dividends_", "stock splits": "splits_"})
        for col in REQUIRED_COLS:
            if col not in df.columns:
                df[col] = np.nan
        return df[REQUIRED_COLS]


# ---------------------------------------------------------------------------
# Unified loader (public API)
# ---------------------------------------------------------------------------

class DataLoader:
    """
    Unified high-frequency data loader.

    Tries Polygon.io first; falls back to yfinance if the API key is missing
    or the response is empty and ``YFINANCE_FALLBACK`` is True.

    Usage
    -----
    >>> loader = DataLoader()
    >>> df = loader.load("TSLA", "2024-08-01", "2024-08-05", timespan="minute")
    """

    def __init__(
        self,
        polygon_api_key: Optional[str] = None,
        use_yfinance_fallback: bool = YFINANCE_FALLBACK,
    ) -> None:
        self._polygon = PolygonLoader(api_key=polygon_api_key)
        self._yfinance = YFinanceLoader()
        self._use_fallback = use_yfinance_fallback

    def load(
        self,
        ticker: str,
        start: str,
        end: str,
        timespan: str = "minute",
        multiplier: int = 1,
        source: str = "auto",
    ) -> pd.DataFrame:
        """
        Load OHLCV data and attach computed returns.

        Parameters
        ----------
        ticker     : Stock or futures symbol.
        start/end  : ISO date strings "YYYY-MM-DD".
        timespan   : "second" | "minute" (Polygon) or "1m" | "5m" (yfinance).
        multiplier : Bar multiplier for Polygon.
        source     : "polygon" | "yfinance" | "auto".
        """
        df = pd.DataFrame()

        if source in ("polygon", "auto") and self._polygon.api_key != "YOUR_POLYGON_API_KEY":
            df = self._polygon.fetch(ticker, start, end, timespan=timespan, multiplier=multiplier)

        if df.empty and self._use_fallback:
            logger.info("Falling back to yfinance for %s", ticker)
            yf_interval = "1m" if timespan in ("second", "minute") else timespan
            df = self._yfinance.fetch(ticker, start, end, interval=yf_interval)

        if df.empty:
            raise ValueError(
                f"No data loaded for {ticker} ({start} → {end}). "
                "Check your API key or date range."
            )

        df = self._postprocess(df)
        logger.info(
            "Loaded %d bars for %s (%s → %s)",
            len(df),
            ticker,
            df.index[0].date(),
            df.index[-1].date(),
        )
        return df

    @staticmethod
    def _postprocess(df: pd.DataFrame) -> pd.DataFrame:
        """Clean, validate, and enrich raw OHLCV data."""
        df = df.copy()

        # Drop exact duplicates
        df = df[~df.index.duplicated(keep="first")]
        df = df.sort_index()

        # Forward-fill isolated NaNs (microstructure gaps), cap at 5 bars
        df[REQUIRED_COLS] = df[REQUIRED_COLS].ffill(limit=5)

        # Remove bars where close is still NaN or non-positive
        df = df[df["close"].notna() & (df["close"] > 0)]

        # Attach log returns
        df["returns"] = log_returns(df["close"])
        df["returns"] = df["returns"].fillna(0.0)

        # Volume: replace NaN with 0 (some after-hours bars)
        df["volume"] = df["volume"].fillna(0.0)

        return df


# ---------------------------------------------------------------------------
# Synthetic data generator (for demo / testing without API key)
# ---------------------------------------------------------------------------

def generate_synthetic_hf_data(
    n_bars: int = 23_400,         # one full US trading day at 1-second
    seed: int = 42,
    regime_frac: float = 0.25,    # fraction of bars in turbulent regime
    freq: str = "1s",
) -> pd.DataFrame:
    """
    Generate realistic synthetic 1-second OHLCV data with embedded turbulent
    regimes.  Used for demonstration and unit tests when no API key is set.

    The price follows a GBM with regime-switching volatility:
        quiet   σ ≈ 0.01% per second
        turbulent σ ≈ 0.04% per second  (4× amplification)
    """
    rng = np.random.default_rng(seed)
    timestamps = pd.date_range("2024-08-01 09:30:00", periods=n_bars, freq=freq, tz="UTC")

    # Regime mask: turbulent blocks scattered through the day
    regime = np.zeros(n_bars, dtype=int)
    turbulent_starts = rng.choice(n_bars // 10, size=int(n_bars * regime_frac / 60), replace=False) * 10
    for ts in turbulent_starts:
        length = rng.integers(30, 180)
        regime[ts : ts + length] = 1

    # Volatility per bar
    sigma = np.where(regime == 1, 4e-4, 1e-4)

    # GBM returns with occasional jumps in turbulent regime
    noise = rng.standard_normal(n_bars) * sigma
    jump_mask = (regime == 1) & (rng.random(n_bars) < 0.01)
    noise[jump_mask] += rng.choice([-1, 1], size=jump_mask.sum()) * rng.uniform(0.002, 0.005, size=jump_mask.sum())

    log_price = np.cumsum(noise) + np.log(200.0)  # start at $200
    close = np.exp(log_price)

    # Build OHLCV
    spread = sigma * close * 0.5
    high = close + np.abs(rng.normal(0, spread))
    low  = close - np.abs(rng.normal(0, spread))
    open_ = close * np.exp(-noise)          # reverse-engineered open

    # Volume: higher during turbulent regime
    base_vol = rng.integers(1_000, 5_000, size=n_bars).astype(float)
    volume = base_vol * (1 + regime * rng.uniform(1, 3, size=n_bars))

    df = pd.DataFrame(
        {
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
            "true_regime": regime,          # ground-truth label for evaluation
        },
        index=timestamps,
    )
    df.index.name = "timestamp"

    # Attach returns
    df["returns"] = log_returns(df["close"]).fillna(0.0)
    return df

"""
ScintillationFeatureExtractor
==============================
Adapts ionospheric scintillation detection techniques from GPS Solutions
to high-frequency financial time-series data.

Analogy map
-----------
GNSS signal intensity (amplitude)   ↔  |return| (amplitude of price move)
GNSS carrier phase                  ↔  cumulative log-return (price "phase")
Ionospheric scintillation           ↔  market turbulence / microstructure noise
S4 index (amplitude scintillation)  ↔  S4_mkt: normalized fluctuation intensity
σφ  (phase scintillation)           ↔  σφ_mkt: detrended phase volatility
Detrending filter                   ↔  Rolling MA subtraction / HPF
Power spectral density              ↔  Welch PSD of returns in rolling window
Deterministic index                 ↔  Autocorrelation / predictability index
Reflective index                    ↔  Bid-ask bounce / mean-reversion measure
"""

from __future__ import annotations

import warnings
from typing import List, Optional

import numpy as np
import pandas as pd
from scipy.signal import welch
from scipy.stats import kurtosis, skew

from config import FeatureConfig, FEATURE_CFG
from utils.helpers import get_logger, high_pass_filter, rolling_detrend

logger = get_logger(__name__)

warnings.filterwarnings("ignore", category=RuntimeWarning)


class ScintillationFeatureExtractor:
    """
    Compute a rich set of scintillation-inspired features over rolling windows.

    Parameters
    ----------
    cfg : FeatureConfig
        Configuration dataclass controlling window sizes, filter parameters, etc.

    Usage
    -----
    >>> extractor = ScintillationFeatureExtractor()
    >>> features = extractor.transform(df)   # df must have 'returns', 'close', 'volume'
    """

    def __init__(self, cfg: FeatureConfig = FEATURE_CFG) -> None:
        self.cfg = cfg
        self._feature_names: List[str] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute all scintillation features on ``df`` and return a new DataFrame.

        Input columns required: returns, close, volume
        Output: one row per bar with all feature columns (NaN at warm-up).
        """
        logger.info("Computing scintillation features on %d bars …", len(df))
        frames: List[pd.DataFrame] = []

        for window in self.cfg.windows:
            logger.debug("  window=%d bars", window)
            frames.append(self._compute_for_window(df, window))

        # Cross-window features (ratios between scales)
        cross = self._cross_window_features(frames)
        frames.append(cross)

        result = pd.concat(frames, axis=1)
        result = result.loc[:, ~result.columns.duplicated()]
        self._feature_names = [c for c in result.columns if not c.startswith("_")]

        logger.info("Feature matrix: %d rows × %d columns", *result.shape)
        return result

    @property
    def feature_names(self) -> List[str]:
        """List of feature column names produced by the last transform() call."""
        return self._feature_names

    # ------------------------------------------------------------------
    # Per-window feature blocks
    # ------------------------------------------------------------------

    def _compute_for_window(self, df: pd.DataFrame, window: int) -> pd.DataFrame:
        r = df["returns"]
        c = df["close"]
        v = df["volume"]
        w = window
        mp = self.cfg.min_periods
        eps = self.cfg.eps
        tag = f"_w{w}"

        out: dict[str, pd.Series] = {}

        # ---------------------------------------------------------------
        # 1. S4 index — Amplitude Scintillation Index
        #    S4 = σ(I) / μ(I)   where I = |r| (signal intensity analog)
        #
        #    In GNSS: S4 = sqrt[ (<I²> - <I>²) / <I>² ]
        #             where <·> denotes a short-interval average.
        #    Here we use the ratio form on |returns|.
        # ---------------------------------------------------------------
        I = r.abs()  # "intensity" = magnitude of price move
        I_mean = I.rolling(w, min_periods=mp).mean()
        I_sq_mean = (I**2).rolling(w, min_periods=mp).mean()
        I_mean_sq = I_mean**2

        # Classic S4 formula (bounded in [0, 1] for Rayleigh-distributed I)
        s4_sq = (I_sq_mean - I_mean_sq).clip(lower=0) / (I_mean_sq + eps)
        out[f"s4{tag}"] = np.sqrt(s4_sq)

        # High-pass filtered version of S4 (only fluctuation component)
        I_hp = I.copy()
        I_hp_vals = high_pass_filter(I.values, cutoff_frac=0.1)
        I_hp = pd.Series(I_hp_vals, index=I.index)
        I_hp_mean = I_hp.abs().rolling(w, min_periods=mp).mean()
        I_hp_sq_mean = (I_hp**2).rolling(w, min_periods=mp).mean()
        I_hp_mean_sq = I_hp_mean**2
        s4_hp_sq = (I_hp_sq_mean - I_hp_mean_sq).clip(lower=0) / (I_hp_mean_sq + eps)
        out[f"s4_hp{tag}"] = np.sqrt(s4_hp_sq)

        # ---------------------------------------------------------------
        # 2. σφ — Phase Scintillation Index
        #    In GNSS: σφ = std of detrended carrier phase over N seconds.
        #    Here:    phase = cumulative log-return (price phase).
        #             Detrend with rolling MA, then take rolling std.
        # ---------------------------------------------------------------
        phase = r.cumsum()
        phase_detrended = rolling_detrend(phase, window=self.cfg.detrend_window, min_periods=mp)
        out[f"sigma_phi{tag}"] = phase_detrended.rolling(w, min_periods=mp).std()

        # Detrended phase acceleration (second difference = phase "jerk")
        phase_vel = phase_detrended.diff()
        out[f"sigma_phi_vel{tag}"] = phase_vel.rolling(w, min_periods=mp).std()

        # ---------------------------------------------------------------
        # 3. Adaptive detrend residual volatility
        #    Detrend close price, then measure residual std.
        #    Larger residual → noisier, less predictable price.
        # ---------------------------------------------------------------
        close_detrended = rolling_detrend(np.log(c), window=w, min_periods=mp)
        out[f"detrend_vol{tag}"] = close_detrended.rolling(w, min_periods=mp).std()

        # ---------------------------------------------------------------
        # 4. Rolling statistical moments (tail-risk features)
        # ---------------------------------------------------------------
        out[f"ret_std{tag}"] = r.rolling(w, min_periods=mp).std()
        out[f"ret_kurt{tag}"] = r.rolling(w, min_periods=mp).apply(
            lambda x: kurtosis(x, fisher=True, bias=False) if len(x) >= 4 else np.nan,
            raw=True,
        )
        out[f"ret_skew{tag}"] = r.rolling(w, min_periods=mp).apply(
            lambda x: skew(x, bias=False) if len(x) >= 3 else np.nan,
            raw=True,
        )

        # Absolute kurtosis excess (turbulence = heavy tails in both directions)
        out[f"abs_kurt{tag}"] = out[f"ret_kurt{tag}"].abs()

        # ---------------------------------------------------------------
        # 5. Deterministic Index (DI)
        #    In GNSS: ratio of deterministic (sinusoidal) power to total power,
        #    measuring how predictable the signal is.
        #    Here: 1 - (rolling autocorrelation lag-1).  High DI → unpredictable.
        # ---------------------------------------------------------------
        def lag1_autocorr(x: np.ndarray) -> float:
            if len(x) < 3:
                return np.nan
            c0 = np.dot(x - x.mean(), x - x.mean())
            if c0 == 0:
                return 0.0
            x_lag = x[:-1]
            x_fut = x[1:]
            return float(np.dot(x_lag - x_lag.mean(), x_fut - x_fut.mean()) / (np.std(x_lag) * np.std(x_fut) * len(x_lag) + eps))

        out[f"det_idx{tag}"] = r.rolling(w, min_periods=mp).apply(
            lambda x: 1.0 - abs(lag1_autocorr(x)), raw=True
        )

        # ---------------------------------------------------------------
        # 6. Reflective Index (RI) — Bid-Ask Bounce / Mean-Reversion
        #    In GNSS: measures signal energy that "bounced" off a reflecting layer.
        #    Here: signed autocorrelation (negative AC → bid-ask bounce).
        #    RI = -lag1_autocorr  (positive when price alternates = microstructure noise)
        # ---------------------------------------------------------------
        out[f"refl_idx{tag}"] = r.rolling(w, min_periods=mp).apply(
            lambda x: -lag1_autocorr(x) if not np.isnan(lag1_autocorr(x)) else np.nan,
            raw=True,
        )

        # ---------------------------------------------------------------
        # 7. Volume-weighted scintillation (anomalous volume + vol spike)
        # ---------------------------------------------------------------
        v_mean = v.rolling(w, min_periods=mp).mean()
        out[f"vol_ratio{tag}"] = v / (v_mean + eps)  # >1 = volume spike

        # Combined amplitude-volume scintillation
        out[f"av_scint{tag}"] = out[f"s4{tag}"] * out[f"vol_ratio{tag}"]

        # ---------------------------------------------------------------
        # 8. Power Spectral Density features (frequency-domain)
        #    In GNSS: scintillation power-law slope p estimated from S(f) ~ f^-p.
        #    Here: estimate PSD slope of returns; steep negative slope → smoother
        #    (quiet); flat or positive slope → high-frequency energy = turbulent.
        # ---------------------------------------------------------------
        nperseg = min(self.cfg.psd_nperseg, w)
        if nperseg >= 4:
            out[f"psd_slope{tag}"] = r.rolling(w, min_periods=max(nperseg, mp)).apply(
                lambda x: self._psd_slope(x, nperseg=nperseg),
                raw=True,
            )
            out[f"psd_entropy{tag}"] = r.rolling(w, min_periods=max(nperseg, mp)).apply(
                lambda x: self._spectral_entropy(x, nperseg=nperseg),
                raw=True,
            )
            out[f"psd_hf_ratio{tag}"] = r.rolling(w, min_periods=max(nperseg, mp)).apply(
                lambda x: self._hf_power_ratio(x, nperseg=nperseg),
                raw=True,
            )

        # ---------------------------------------------------------------
        # 9. High-pass filtered intensity volatility
        #    Isolate the "scintillating" component by high-pass filtering,
        #    then measure its energy in the rolling window.
        # ---------------------------------------------------------------
        r_hp_vals = high_pass_filter(r.values, cutoff_frac=0.05)
        r_hp = pd.Series(r_hp_vals, index=r.index)
        out[f"hp_vol{tag}"] = r_hp.rolling(w, min_periods=mp).std()
        out[f"hp_energy{tag}"] = (r_hp**2).rolling(w, min_periods=mp).mean()

        # ---------------------------------------------------------------
        # 10. Intra-bar range scintillation
        #     High-Low range normalized by close = "price oscillation depth"
        #     Mirrors signal amplitude spread in GNSS.
        # ---------------------------------------------------------------
        if "high" in df.columns and "low" in df.columns:
            bar_range = (df["high"] - df["low"]) / (df["close"] + eps)
            out[f"range_scint{tag}"] = bar_range.rolling(w, min_periods=mp).mean()
            out[f"range_vol{tag}"] = bar_range.rolling(w, min_periods=mp).std()

        return pd.DataFrame(out, index=df.index)

    # ------------------------------------------------------------------
    # Cross-window features (scale interactions)
    # ------------------------------------------------------------------

    def _cross_window_features(self, frames: List[pd.DataFrame]) -> pd.DataFrame:
        """
        Compute ratios and differences between features at different time-scales.

        Fast-vs-slow regime: if short-window scintillation >> long-window,
        we are in an acute turbulent burst (matches GNSS burst scintillation).
        """
        if len(frames) < 2:
            return pd.DataFrame(index=frames[0].index)

        ws = self.cfg.windows
        out: dict[str, pd.Series] = {}

        def _safe_col(frame: pd.DataFrame, col: str) -> Optional[pd.Series]:
            return frame[col] if col in frame.columns else None

        for i in range(len(ws) - 1):
            w_fast = ws[i]
            w_slow = ws[i + 1]
            f_fast = frames[i]
            f_slow = frames[i + 1]

            for feat in ["s4", "ret_std", "sigma_phi", "hp_vol"]:
                col_fast = f"{feat}_w{w_fast}"
                col_slow = f"{feat}_w{w_slow}"
                s_fast = _safe_col(f_fast, col_fast)
                s_slow = _safe_col(f_slow, col_slow)
                if s_fast is not None and s_slow is not None:
                    eps = self.cfg.eps
                    out[f"{feat}_ratio_{w_fast}v{w_slow}"] = s_fast / (s_slow + eps)
                    out[f"{feat}_diff_{w_fast}v{w_slow}"] = s_fast - s_slow

        return pd.DataFrame(out, index=frames[0].index)

    # ------------------------------------------------------------------
    # PSD helper methods
    # ------------------------------------------------------------------

    @staticmethod
    def _psd_slope(x: np.ndarray, nperseg: int = 32) -> float:
        """
        Estimate the power-law slope p of PSD(f) ~ f^{-p} via log-log regression.

        In GNSS scintillation: p ≈ 1.5–3.0 in quiet conditions; flatter near p ≈ 0
        or negative p indicates broad-band (turbulent) scintillation energy.
        """
        try:
            if np.std(x) < 1e-15:
                return 0.0
            nperseg = min(nperseg, len(x))
            freqs, psd = welch(x, nperseg=nperseg)
            # Skip DC (f=0)
            mask = freqs > 0
            if mask.sum() < 2:
                return 0.0
            log_f = np.log(freqs[mask] + 1e-12)
            log_p = np.log(psd[mask] + 1e-30)
            slope, _ = np.polyfit(log_f, log_p, 1)
            return float(slope)
        except Exception:
            return np.nan

    @staticmethod
    def _spectral_entropy(x: np.ndarray, nperseg: int = 32) -> float:
        """
        Normalized spectral entropy of the PSD.

        High entropy = broad-band energy distribution = turbulent / noisy signal.
        Low entropy  = energy concentrated at a few frequencies = predictable.

        Analogous to the spectral regularity used in ionospheric scintillation
        classification (Phase Spectral Index).
        """
        try:
            if np.std(x) < 1e-15:
                return 0.0
            nperseg = min(nperseg, len(x))
            _, psd = welch(x, nperseg=nperseg)
            psd = psd / (psd.sum() + 1e-30)
            entropy = -np.sum(psd * np.log(psd + 1e-30))
            max_entropy = np.log(len(psd))
            return float(entropy / max_entropy) if max_entropy > 0 else 0.0
        except Exception:
            return np.nan

    @staticmethod
    def _hf_power_ratio(x: np.ndarray, nperseg: int = 32) -> float:
        """
        Ratio of high-frequency power (top half of spectrum) to total power.

        High ratio → dominant high-frequency content → turbulent.
        Mirrors the T-index (high-frequency scintillation index) in GNSS.
        """
        try:
            if np.std(x) < 1e-15:
                return 0.0
            nperseg = min(nperseg, len(x))
            freqs, psd = welch(x, nperseg=nperseg)
            midpoint = len(freqs) // 2
            hf_power = psd[midpoint:].sum()
            total_power = psd.sum()
            return float(hf_power / (total_power + 1e-30))
        except Exception:
            return np.nan


# ---------------------------------------------------------------------------
# Labeling: generate turbulence labels for supervised ML
# ---------------------------------------------------------------------------

def label_turbulent_regimes(
    df: pd.DataFrame,
    method: str = "future_vol",
    future_window: int = 60,
    quantile: float = 0.75,
    z_thresh: float = 2.5,
) -> pd.Series:
    """
    Create binary turbulence labels (0=quiet, 1=turbulent).

    Parameters
    ----------
    method : "future_vol" | "sharp_move" | "combined"
        future_vol  : turbulent if future rolling vol > quantile threshold.
        sharp_move  : turbulent if |return| > z_thresh × rolling std.
        combined    : OR of both above.
    future_window : int
        Bars ahead to compute realized vol for the future_vol method.
    quantile : float
        Threshold quantile for future_vol method.
    z_thresh : float
        Z-score threshold for sharp_move method.
    """
    r = df["returns"]

    if method in ("future_vol", "combined"):
        # Shift realized vol backward: at time t, label based on vol of [t, t+window]
        fut_vol = r.rolling(future_window, min_periods=5).std().shift(-future_window)
        threshold = fut_vol.quantile(quantile)
        label_vol = (fut_vol > threshold).astype(int)

    if method in ("sharp_move", "combined"):
        roll_std = r.rolling(60, min_periods=5).std()
        label_sharp = (r.abs() > z_thresh * roll_std).astype(int)

    if method == "future_vol":
        return label_vol.rename("label")
    elif method == "sharp_move":
        return label_sharp.rename("label")
    elif method == "combined":
        return (label_vol | label_sharp).astype(int).rename("label")
    else:
        raise ValueError(f"Unknown labeling method: {method}")

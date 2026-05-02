"""
Regime Forecaster
=================
Projects the ML turbulence probability forward N bars using an AR(1) +
mean-reversion model, then translates the trajectory into plain-language
signal predictions ("BUY expected in ~3 min", "SELL warning in ~1 min").

Analogy to GNSS scintillation
------------------------------
In ionospheric studies, scintillation events exhibit "persistence" — once
strong scintillation begins it tends to last several minutes before
decaying back to quiet.  We model this with the same class of AR(1) /
exponential-smoothing forecaster used for TEC fluctuation prediction.

  p̂(t+k) = μ + φᵏ (p(t) - μ)

where φ is estimated from recent autocorrelation of the probability series
and μ is the rolling mean (the "baseline" turbulence level).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from utils.helpers import get_logger

logger = get_logger(__name__)


@dataclass
class ForecastResult:
    horizons_min: list[int]           # [1, 5, 15]
    proba_forecast: list[float]       # P(turbulent) at each horizon
    signal_forecast: list[str]        # "BUY" / "SELL" / "HOLD" at each horizon
    next_signal_bar: Optional[int]    # bars until next expected signal change
    next_signal_type: Optional[str]   # "BUY" / "SELL"
    confidence: float                 # overall forecast confidence [0,1]
    summary: str                      # natural-language prediction


class RegimeForecaster:
    """
    AR(1) turbulence probability forecaster.

    Parameters
    ----------
    entry_threshold : float   P < this → quiet/BUY zone
    exit_threshold  : float   P > this → turbulent/SELL zone
    lookback        : int     bars of history used to estimate AR(1) params
    horizons_min    : list    forecast horizons in bars (≈ minutes for 1-min data)
    """

    def __init__(
        self,
        entry_threshold: float = 0.40,
        exit_threshold: float  = 0.55,
        lookback: int          = 30,
        horizons_min: list[int] = None,
    ) -> None:
        self.entry_threshold = entry_threshold
        self.exit_threshold  = exit_threshold
        self.lookback        = lookback
        self.horizons        = horizons_min or [1, 5, 15]

    def forecast(
        self,
        proba: pd.Series,
        current_position: str = "FLAT",
    ) -> ForecastResult:
        """
        Forecast regime probabilities at each horizon.

        Parameters
        ----------
        proba            : full historical P(turbulent) series (aligned to df index)
        current_position : "LONG" | "SHORT" | "FLAT"
        """
        recent = proba.dropna().iloc[-self.lookback:]
        if len(recent) < 4:
            return self._fallback(proba)

        # ── Estimate AR(1) parameters ──────────────────────────────────
        mu  = float(recent.mean())
        phi = float(np.corrcoef(recent.values[:-1], recent.values[1:])[0, 1])
        phi = np.clip(phi, -0.95, 0.95)           # bound persistence

        # Residual std → confidence proxy (low residual = more predictable)
        resid_std = float(recent.std())
        confidence = float(np.clip(1.0 - resid_std * 4, 0.1, 0.95))

        p0 = float(recent.iloc[-1])               # latest probability

        # ── Project forward ────────────────────────────────────────────
        proba_forecast = []
        for k in self.horizons:
            p_k = mu + (phi ** k) * (p0 - mu)
            p_k = float(np.clip(p_k, 0.0, 1.0))
            proba_forecast.append(round(p_k, 4))

        # ── Translate to signal ────────────────────────────────────────
        signal_forecast = []
        for p_k in proba_forecast:
            if p_k < self.entry_threshold:
                signal_forecast.append("BUY zone")
            elif p_k > self.exit_threshold:
                signal_forecast.append("SELL zone")
            else:
                signal_forecast.append("Neutral")

        # ── Next-signal bar ────────────────────────────────────────────
        next_bar, next_type = self._next_crossing(p0, mu, phi)

        # ── Natural language summary ───────────────────────────────────
        summary = self._summarise(
            p0, proba_forecast, signal_forecast,
            next_bar, next_type, current_position, confidence,
        )

        return ForecastResult(
            horizons_min=self.horizons,
            proba_forecast=proba_forecast,
            signal_forecast=signal_forecast,
            next_signal_bar=next_bar,
            next_signal_type=next_type,
            confidence=confidence,
            summary=summary,
        )

    # ------------------------------------------------------------------

    def _next_crossing(
        self, p0: float, mu: float, phi: float, max_horizon: int = 30,
    ) -> tuple[Optional[int], Optional[str]]:
        """Find first bar where forecast crosses entry or exit threshold."""
        p = p0
        for k in range(1, max_horizon + 1):
            p = mu + phi * (p - mu)
            p = float(np.clip(p, 0.0, 1.0))
            if p < self.entry_threshold and p0 >= self.entry_threshold:
                return k, "BUY"
            if p > self.exit_threshold and p0 <= self.exit_threshold:
                return k, "SELL"
        return None, None

    def _summarise(
        self, p0, proba_fc, signal_fc, next_bar, next_type,
        position, confidence,
    ) -> str:
        now_zone = ("QUIET" if p0 < self.entry_threshold
                    else "TURBULENT" if p0 > self.exit_threshold
                    else "TRANSITIONING")
        lines = [f"Regime now: {now_zone} (P={p0:.2f})"]

        for h, p, s in zip(self.horizons, proba_fc, signal_fc):
            lines.append(f"+{h:2d} min → P={p:.2f}  [{s}]")

        if next_bar and next_type:
            lines.append(f"⚡ {next_type} crossing expected in ~{next_bar} bar(s)")
        elif position in ("LONG", "SHORT"):
            if p0 < self.exit_threshold:
                lines.append("Position safe — regime stable")
            else:
                lines.append("⚠ Regime turbulent — exit risk rising")

        lines.append(f"Forecast confidence: {confidence:.0%}")
        return "\n".join(lines)

    def _fallback(self, proba: pd.Series) -> ForecastResult:
        p0 = float(proba.dropna().iloc[-1]) if not proba.dropna().empty else 0.5
        return ForecastResult(
            horizons_min=self.horizons,
            proba_forecast=[p0] * len(self.horizons),
            signal_forecast=["Insufficient data"] * len(self.horizons),
            next_signal_bar=None,
            next_signal_type=None,
            confidence=0.0,
            summary="Insufficient history for forecasting.",
        )

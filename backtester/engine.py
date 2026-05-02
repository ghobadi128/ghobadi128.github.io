"""
Regime-Aware Backtesting Engine
================================
Runs two strategies side-by-side:
    1. Baseline HF strategy (momentum or mean-reversion, full position always on)
    2. ML-filtered version    (goes flat or reduces size when turbulent)

Both strategies trade on 1-second (or 1-minute) bars.

Signal logic
------------
Momentum    : go long if returns over last N bars > 0, else short.
Mean-rev    : go short if returns > threshold, long if < -threshold.

Performance metrics: Sharpe, Sortino, max drawdown, Calmar, n_trades, win_rate.
"""

from __future__ import annotations

import logging
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd

from config import BacktestConfig, BACKTEST_CFG
from utils.helpers import compute_performance_metrics, get_logger

logger = get_logger(__name__)


class BacktestEngine:
    """
    Vectorized regime-aware backtester.

    Parameters
    ----------
    cfg : BacktestConfig
        Strategy and risk parameters.

    Usage
    -----
    >>> engine = BacktestEngine()
    >>> results = engine.run(price_df, regime_proba)
    """

    def __init__(self, cfg: BacktestConfig = BACKTEST_CFG) -> None:
        self.cfg = cfg

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def run(
        self,
        df: pd.DataFrame,
        turbulence_proba: Optional[pd.Series] = None,
        regime_label: Optional[pd.Series] = None,
    ) -> Dict[str, pd.DataFrame]:
        """
        Run baseline and (optionally) ML-filtered backtests.

        Parameters
        ----------
        df : OHLCV + returns DataFrame (output of DataLoader).
        turbulence_proba : continuous [0,1] turbulence score per bar.
        regime_label     : binary 0/1 turbulence label per bar.

        Returns
        -------
        dict with keys:
            "baseline"  : strategy results DataFrame
            "filtered"  : regime-filtered results DataFrame (if regime_label provided)
            "metrics"   : combined performance metrics dict
        """
        raw_signal = self._compute_signal(df)

        baseline_pos = self._apply_sizing(raw_signal, size=self.cfg.position_size)
        baseline_results = self._simulate(df, baseline_pos, label="Baseline")

        output = {"baseline": baseline_results}

        if regime_label is not None or turbulence_proba is not None:
            if regime_label is None and turbulence_proba is not None:
                regime_label = (turbulence_proba >= self.cfg.regime_threshold).astype(int)

            # In turbulent regime → reduce to turbulent_size; else full position
            size_mask = np.where(
                regime_label.reindex(df.index, fill_value=0) == 1,
                self.cfg.turbulent_size,
                self.cfg.position_size,
            )
            size_series = pd.Series(size_mask, index=df.index)
            filtered_pos = raw_signal * size_series

            filtered_results = self._simulate(df, filtered_pos, label="ML-Filtered")
            output["filtered"] = filtered_results

        output["metrics"] = self._combined_metrics(output)
        return output

    # ------------------------------------------------------------------
    # Signal generation
    # ------------------------------------------------------------------

    def _compute_signal(self, df: pd.DataFrame) -> pd.Series:
        """
        Generate raw directional signal in {-1, 0, +1}.

        Momentum : +1 if rolling return > 0, -1 otherwise.
        Mean-rev : +1 if recent move was down, -1 if up.
        """
        r = df["returns"]
        w = self.cfg.signal_window

        roll_ret = r.rolling(w, min_periods=2).sum()

        if self.cfg.strategy == "momentum":
            signal = np.sign(roll_ret)
        elif self.cfg.strategy == "mean_reversion":
            signal = -np.sign(roll_ret)
        else:
            raise ValueError(f"Unknown strategy: {self.cfg.strategy}")

        # Shift by 1 bar to avoid look-ahead: we act on the NEXT bar's open
        signal = signal.shift(1).fillna(0.0)
        return signal.rename("signal")

    @staticmethod
    def _apply_sizing(signal: pd.Series, size: float) -> pd.Series:
        return signal * size

    # ------------------------------------------------------------------
    # Simulation
    # ------------------------------------------------------------------

    def _simulate(
        self,
        df: pd.DataFrame,
        position: pd.Series,
        label: str = "Strategy",
    ) -> pd.DataFrame:
        """
        Vectorized P&L simulation.

        Returns a DataFrame with columns:
            position, gross_ret, net_ret, equity, drawdown
        """
        # Raw bar return earned by holding the position
        gross_ret = position * df["returns"]

        # Transaction costs: cost triggered on position changes
        tc_bps = self.cfg.transaction_cost_bps * 1e-4
        turnover = position.diff().abs().fillna(0.0)
        tc = turnover * tc_bps
        net_ret = gross_ret - tc

        # Equity curve
        equity = (1 + net_ret).cumprod() * self.cfg.initial_capital

        # Drawdown
        peak = equity.cummax()
        drawdown = (equity - peak) / peak

        result = pd.DataFrame(
            {
                "position": position,
                "gross_ret": gross_ret,
                "net_ret": net_ret,
                "equity": equity,
                "drawdown": drawdown,
            },
            index=df.index,
        )
        result.attrs["label"] = label
        return result

    # ------------------------------------------------------------------
    # Performance metrics
    # ------------------------------------------------------------------

    def _combined_metrics(self, output: Dict[str, pd.DataFrame]) -> Dict:
        metrics = {}

        bars_per_year = self._infer_bars_per_year(output["baseline"])

        for key in ("baseline", "filtered"):
            if key not in output:
                continue
            res = output[key]
            label = res.attrs.get("label", key)
            m = compute_performance_metrics(
                returns=res["net_ret"],
                equity=res["equity"],
                label=label,
                periods_per_year=bars_per_year,
            )
            metrics[key] = m

        # Print comparison table
        self._log_comparison(metrics)
        return metrics

    @staticmethod
    def _infer_bars_per_year(result: pd.DataFrame) -> int:
        """Estimate bars-per-year from the index frequency."""
        if len(result) < 2:
            return 252
        delta = (result.index[1] - result.index[0]).total_seconds()
        bars_per_day = 23_400 / max(delta, 1)   # 6.5h trading day
        return int(bars_per_day * 252)

    @staticmethod
    def _log_comparison(metrics: Dict) -> None:
        keys_order = ["total_return_pct", "sharpe", "sortino",
                      "max_drawdown_pct", "calmar", "n_trades",
                      "win_rate_pct", "ann_vol_pct"]
        header = f"{'Metric':<22}  {'Baseline':>12}  {'ML-Filtered':>14}"
        logger.info("=" * len(header))
        logger.info(header)
        logger.info("=" * len(header))

        base = metrics.get("baseline", {})
        filt = metrics.get("filtered", {})

        for k in keys_order:
            b_val = f"{base.get(k, 'N/A'):>12.2f}" if isinstance(base.get(k), (int, float)) else f"{'N/A':>12}"
            f_val = f"{filt.get(k, 'N/A'):>14.2f}" if isinstance(filt.get(k), (int, float)) else f"{'N/A':>14}"
            logger.info("  %-22s %s  %s", k, b_val, f_val)

        logger.info("=" * len(header))


# ---------------------------------------------------------------------------
# Quick standalone run for inspection
# ---------------------------------------------------------------------------

def quick_backtest(
    df: pd.DataFrame,
    regime_label: Optional[pd.Series] = None,
    turbulence_proba: Optional[pd.Series] = None,
    cfg: BacktestConfig = BACKTEST_CFG,
) -> Dict[str, pd.DataFrame]:
    """Convenience wrapper around BacktestEngine.run()."""
    engine = BacktestEngine(cfg=cfg)
    return engine.run(df, turbulence_proba=turbulence_proba, regime_label=regime_label)

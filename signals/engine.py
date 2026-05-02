"""
Systematic Trading Signal Engine
==================================
Converts the ML turbulence probability into actionable BUY / SELL / HOLD
signals with a full position-state machine.

Signal logic
------------
The engine layers three filters in sequence:

  1. Regime gate     — block new entries when ML P(turbulent) > entry_threshold.
  2. Momentum entry  — go long when short-term momentum is positive in quiet regime;
                       go short when negative (configurable).
  3. Exit rules      — exit position when:
                         a) regime flips turbulent  (primary: regime-driven exit)
                         b) trailing stop triggered  (secondary: risk control)
                         c) profit-target hit        (optional)
                         d) momentum reverses        (tertiary)

Output columns (one row per bar)
---------------------------------
  signal        : +1 BUY · 0 HOLD · -1 SELL
  position      : current held position (+1 long, 0 flat, -1 short)
  entry_price   : fill price of current open position (NaN when flat)
  pnl_pct       : open P&L % from entry (NaN when flat)
  signal_reason : human-readable string explaining the signal
  confidence    : ML turbulence probability inverted for long confidence
  buzz          : True when a new BUY or SELL fires (transition bar)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

from utils.helpers import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class SignalConfig:
    # Regime gate thresholds
    entry_threshold: float  = 0.40   # P(turbulent) must be BELOW this to enter long
    exit_threshold:  float  = 0.55   # P(turbulent) must be ABOVE this to trigger exit
    short_threshold: float  = 0.40   # same gate for short entries (if allow_short=True)

    # Momentum parameters
    momentum_window: int    = 5      # bars for short-term momentum signal
    allow_short:     bool   = False  # whether to take short positions

    # Risk controls
    stop_loss_pct:   float  = 0.02   # exit if position loses > 2% from entry
    profit_target_pct: Optional[float] = 0.03  # take profit at +3% (None = off)
    min_hold_bars:   int    = 2      # minimum bars before momentum-reversal exit

    # Confidence display
    confidence_floor: float = 0.0   # floor for display confidence score


# ---------------------------------------------------------------------------
# Signal engine
# ---------------------------------------------------------------------------

class TradingSignalEngine:
    """
    Stateful position machine: takes ML probability + price data and emits signals.

    Parameters
    ----------
    cfg : SignalConfig
    """

    def __init__(self, cfg: Optional[SignalConfig] = None) -> None:
        self.cfg = cfg or SignalConfig()

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def generate(
        self,
        df: pd.DataFrame,
        turbulence_proba: pd.Series,
    ) -> pd.DataFrame:
        """
        Run the signal engine over the full history.

        Parameters
        ----------
        df              : OHLCV + returns DataFrame.
        turbulence_proba: ML P(turbulent) per bar, index-aligned with df.

        Returns
        -------
        DataFrame with columns: signal, position, entry_price, pnl_pct,
                                 signal_reason, confidence, buzz.
        """
        proba   = turbulence_proba.reindex(df.index).ffill().fillna(0.5)
        close   = df["close"]
        returns = df["returns"]
        cfg     = self.cfg

        # --- Momentum: rolling sum of returns ---
        momentum = returns.rolling(cfg.momentum_window, min_periods=2).sum()

        n = len(df)
        signal       = np.zeros(n, dtype=int)
        position     = np.zeros(n, dtype=int)
        entry_price  = np.full(n, np.nan)
        pnl_pct      = np.full(n, np.nan)
        reasons      = [""] * n
        confidence   = np.zeros(n)
        buzz         = np.zeros(n, dtype=bool)

        cur_pos      = 0      # current position: +1 / 0 / -1
        cur_entry    = np.nan
        bars_held    = 0

        for i in range(n):
            p      = proba.iloc[i]
            mom    = momentum.iloc[i]
            px     = close.iloc[i]
            conf   = max(1.0 - p, cfg.confidence_floor)  # long confidence

            # --- Carry current position ---
            position[i]    = cur_pos
            entry_price[i] = cur_entry
            confidence[i]  = conf

            if cur_pos != 0 and not np.isnan(cur_entry):
                pnl_pct[i] = (px / cur_entry - 1.0) * cur_pos
            else:
                pnl_pct[i] = np.nan

            # ---- Exit logic (if in position) ----
            if cur_pos != 0:
                bars_held += 1
                open_pnl = pnl_pct[i]

                exit_reason = None

                # 1. Regime-driven exit
                if cur_pos == 1 and p > cfg.exit_threshold:
                    exit_reason = f"regime exit (P_turb={p:.2f}>{cfg.exit_threshold})"
                elif cur_pos == -1 and p > cfg.exit_threshold:
                    exit_reason = f"regime exit short (P_turb={p:.2f}>{cfg.exit_threshold})"

                # 2. Stop-loss
                elif open_pnl < -cfg.stop_loss_pct:
                    exit_reason = f"stop-loss ({open_pnl:+.2%})"

                # 3. Profit target
                elif cfg.profit_target_pct and open_pnl > cfg.profit_target_pct:
                    exit_reason = f"profit target ({open_pnl:+.2%})"

                # 4. Momentum reversal (after min_hold_bars)
                elif bars_held >= cfg.min_hold_bars:
                    if cur_pos == 1 and mom < 0 and p < cfg.exit_threshold:
                        exit_reason = f"momentum reversal (mom={mom:.4f})"
                    elif cur_pos == -1 and mom > 0 and p < cfg.exit_threshold:
                        exit_reason = f"momentum reversal short (mom={mom:.4f})"

                if exit_reason:
                    signal[i]    = -cur_pos        # SELL (+1→-1) or BUY COVER (-1→+1)
                    reasons[i]   = f"EXIT: {exit_reason}"
                    buzz[i]      = True
                    cur_pos      = 0
                    cur_entry    = np.nan
                    bars_held    = 0
                    position[i]  = 0               # show flat on exit bar
                    continue

            # ---- Entry logic (if flat) ----
            if cur_pos == 0:
                if p < cfg.entry_threshold and not np.isnan(mom):
                    # Long entry
                    if mom > 0:
                        signal[i]   = 1
                        reasons[i]  = f"BUY: quiet regime (P={p:.2f}) + momentum ↑ ({mom:+.4f})"
                        buzz[i]     = True
                        cur_pos     = 1
                        cur_entry   = px
                        bars_held   = 0
                        position[i] = 1

                    # Short entry (optional)
                    elif mom < 0 and cfg.allow_short and p < cfg.short_threshold:
                        signal[i]   = -1
                        reasons[i]  = f"SHORT: quiet regime (P={p:.2f}) + momentum ↓ ({mom:+.4f})"
                        buzz[i]     = True
                        cur_pos     = -1
                        cur_entry   = px
                        bars_held   = 0
                        position[i] = -1

        result = pd.DataFrame(
            {
                "signal":       signal,
                "position":     position,
                "entry_price":  entry_price,
                "pnl_pct":      pnl_pct,
                "signal_reason":reasons,
                "confidence":   confidence,
                "buzz":         buzz,
            },
            index=df.index,
        )

        n_buys  = int((signal ==  1).sum())
        n_sells = int((signal == -1).sum())
        logger.info("Signal engine: %d BUY · %d SELL · %d HOLD", n_buys, n_sells, n - n_buys - n_sells)
        return result

    # ------------------------------------------------------------------
    # Convenience: current (latest bar) signal summary
    # ------------------------------------------------------------------

    @staticmethod
    def latest_signal(signals: pd.DataFrame) -> dict:
        """Extract the most recent bar's signal for dashboard display."""
        last = signals.iloc[-1]
        direction_map = {1: "BUY", -1: "SELL", 0: "HOLD"}
        pos_map       = {1: "LONG", -1: "SHORT", 0: "FLAT"}

        return {
            "signal":       int(last["signal"]),
            "direction":    direction_map[int(last["signal"])],
            "position":     pos_map[int(last["position"])],
            "confidence":   float(last["confidence"]),
            "pnl_pct":      float(last["pnl_pct"]) if not np.isnan(last["pnl_pct"]) else None,
            "entry_price":  float(last["entry_price"]) if not np.isnan(last["entry_price"]) else None,
            "reason":       str(last["signal_reason"]) or "HOLD: monitoring",
            "buzz":         bool(last["buzz"]),
            "timestamp":    signals.index[-1],
        }

    # ------------------------------------------------------------------
    # Trade log: every BUY/SELL transition
    # ------------------------------------------------------------------

    @staticmethod
    def trade_log(signals: pd.DataFrame, df: pd.DataFrame) -> pd.DataFrame:
        """
        Return a cleaned trade log with entry/exit price, P&L, and hold duration.
        """
        mask   = signals["buzz"]
        events = signals[mask].copy()
        events["close"] = df["close"].reindex(events.index)

        rows = []
        open_trade: dict = {}

        for ts, row in events.iterrows():
            sig = int(row["signal"])
            if sig == 1:                                    # BUY entry
                open_trade = {
                    "entry_time":  ts,
                    "entry_price": float(row["close"]),
                    "direction":   "LONG",
                }
            elif sig == -1 and open_trade:                 # SELL / exit
                ep = open_trade.get("entry_price", float(row["close"]))
                pnl = (float(row["close"]) / ep - 1.0) * 100.0
                hold = int((ts - open_trade["entry_time"]).total_seconds() / 60)
                rows.append({
                    "Entry Time":    open_trade["entry_time"].strftime("%H:%M"),
                    "Exit Time":     ts.strftime("%H:%M"),
                    "Direction":     open_trade.get("direction", "LONG"),
                    "Entry $":       f"${ep:.2f}",
                    "Exit $":        f"${float(row['close']):.2f}",
                    "P&L %":         f"{pnl:+.2f}%",
                    "Hold (min)":    hold,
                    "Exit Reason":   str(row["signal_reason"]).replace("EXIT: ", ""),
                    "_pnl_raw":      pnl,
                })
                open_trade = {}

        if not rows:
            return pd.DataFrame()

        log = pd.DataFrame(rows)
        return log


# ---------------------------------------------------------------------------
# P&L simulation on signal stream
# ---------------------------------------------------------------------------

def simulate_signal_pnl(
    df: pd.DataFrame,
    signals: pd.DataFrame,
    initial_capital: float = 10_000.0,
    transaction_cost_bps: float = 0.5,
) -> pd.DataFrame:
    """
    Dollar P&L simulation from the signal engine output.
    Returns a DataFrame with: shares, cash, equity, daily_pnl columns.
    """
    tc  = transaction_cost_bps * 1e-4
    pos = signals["position"]
    ret = df["returns"]

    # Bar return = position × price return − transaction cost on changes
    gross   = pos.shift(1).fillna(0) * ret
    turnover = pos.diff().abs().fillna(0)
    net      = gross - turnover * tc

    equity   = (1 + net).cumprod() * initial_capital
    drawdown = (equity - equity.cummax()) / equity.cummax()

    return pd.DataFrame(
        {"net_ret": net, "equity": equity, "drawdown": drawdown},
        index=df.index,
    )

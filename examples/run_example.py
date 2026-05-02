"""
MarketScintillation — Standalone Example Runner
================================================
Runs the full pipeline on a real ticker (UAMY or RKLB) using yfinance
1-minute bars and prints a comprehensive performance report.

Usage
-----
    python examples/run_example.py              # defaults to UAMY
    python examples/run_example.py --ticker RKLB
    python examples/run_example.py --ticker UAMY --period 7d
    python examples/run_example.py --synthetic  # no internet needed
"""

from __future__ import annotations

import argparse
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd

from data.loader import DataLoader, generate_synthetic_hf_data
from features.extractor import ScintillationFeatureExtractor, label_turbulent_regimes
from models.classifier import TurbulenceClassifier, train_test_split_ts
from backtester.engine import BacktestEngine
from config import FeatureConfig, LabelConfig, ModelConfig, BacktestConfig
from utils.helpers import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Per-ticker tuned presets
# (minute-bar data → shorter windows than second-bar defaults)
# ---------------------------------------------------------------------------

PRESETS: dict[str, dict] = {
    "UAMY": {
        "description": "United States Antimony Corp — 137% ann vol, high scintillation",
        "period": "7d", "interval": "1m",
        "feature_windows": [5, 15, 30, 60], "detrend_window": 30,
        "label_method": "future_vol", "future_window": 15,
        "turbulence_quantile": 0.70, "strategy": "momentum",
        "signal_window": 5, "turbulent_size": 0.0, "regime_threshold": 0.45,
    },
    "HOOD": {
        "description": "Robinhood Markets — 84% ann vol, heavy microstructure noise",
        "period": "7d", "interval": "1m",
        "feature_windows": [5, 15, 30, 60], "detrend_window": 30,
        "label_method": "future_vol", "future_window": 15,
        "turbulence_quantile": 0.72, "strategy": "momentum",
        "signal_window": 5, "turbulent_size": 0.0, "regime_threshold": 0.42,
    },
    "NVDA": {
        "description": "NVIDIA Corp — 38% ann vol, chip-cycle regime shifts",
        "period": "7d", "interval": "1m",
        "feature_windows": [5, 15, 30, 60], "detrend_window": 30,
        "label_method": "future_vol", "future_window": 20,
        "turbulence_quantile": 0.75, "strategy": "momentum",
        "signal_window": 8, "turbulent_size": 0.0, "regime_threshold": 0.45,
    },
    "RKLB": {
        "description": "Rocket Lab Corp — 93% ann vol, intraday regime shifts",
        "period": "7d", "interval": "1m",
        "feature_windows": [5, 15, 30, 60], "detrend_window": 30,
        "label_method": "future_vol", "future_window": 15,
        "turbulence_quantile": 0.72, "strategy": "momentum",
        "signal_window": 5, "turbulent_size": 0.0, "regime_threshold": 0.45,
    },
    "SYNTHETIC": {
        "description": "Regime-switching synthetic data (no API key needed)",
        "period": None,
        "interval": None,
        "feature_windows": [10, 30, 60, 300],
        "detrend_window": 60,
        "label_method": "future_vol",
        "future_window": 60,
        "turbulence_quantile": 0.75,
        "strategy": "momentum",
        "signal_window": 10,
        "turbulent_size": 0.0,
        "regime_threshold": 0.50,
    },
}


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def run(ticker: str = "UAMY", synthetic: bool = False, verbose: bool = True) -> dict:
    key = "SYNTHETIC" if synthetic else ticker.upper()
    preset = PRESETS.get(key, PRESETS["UAMY"])

    print(f"\n{'='*65}")
    print(f"  MarketScintillation — {key}")
    print(f"  {preset['description']}")
    print(f"{'='*65}\n")

    # ------ 1. Load data ------
    if synthetic:
        print("[1/5] Generating synthetic HF data (23,400 × 1-second bars) …")
        df = generate_synthetic_hf_data(n_bars=23_400, seed=42)
    else:
        print(f"[1/5] Fetching {ticker} ({preset['period']} @ {preset['interval']}) via yfinance …")
        loader = DataLoader(use_yfinance_fallback=True)
        # yfinance period-based fetch (no start/end needed)
        try:
            import yfinance as yf
            raw = yf.Ticker(ticker).history(
                period=preset["period"],
                interval=preset["interval"],
                auto_adjust=True,
            )
            if raw.empty:
                raise ValueError(f"No data returned for {ticker}")
            raw.index = pd.to_datetime(raw.index, utc=True)
            raw.index.name = "timestamp"
            raw.columns = [c.lower() for c in raw.columns]
            from utils.helpers import log_returns
            raw["returns"] = log_returns(raw["close"]).fillna(0.0)
            raw["volume"] = raw["volume"].fillna(0.0)
            df = raw[["open", "high", "low", "close", "volume", "returns"]]
        except Exception as exc:
            print(f"  ⚠  yfinance failed ({exc}). Falling back to synthetic data.")
            df = generate_synthetic_hf_data(n_bars=23_400, seed=42)

    print(f"     → {len(df):,} bars  |  close range [{df['close'].min():.4f}, {df['close'].max():.4f}]")
    ann_vol = df["returns"].std() * np.sqrt(_bars_per_year(df))
    print(f"     → Annualized vol: {ann_vol:.1%}")

    # ------ 2. Feature extraction ------
    print(f"\n[2/5] Computing scintillation features  (windows={preset['feature_windows']}) …")
    feat_cfg = FeatureConfig(
        windows=preset["feature_windows"],
        detrend_window=preset["detrend_window"],
        psd_nperseg=min(32, preset["feature_windows"][0]),
    )
    extractor = ScintillationFeatureExtractor(cfg=feat_cfg)
    features = extractor.transform(df)
    print(f"     → Feature matrix: {features.shape[0]:,} rows × {features.shape[1]} columns")
    print(f"     → NaN rate: {features.isna().mean().mean():.1%}")

    # ------ 3. Labels ------
    print(f"\n[3/5] Generating turbulence labels  (method={preset['label_method']!r}) …")
    labels = label_turbulent_regimes(
        df,
        method=preset["label_method"],
        future_window=preset["future_window"],
        quantile=preset["turbulence_quantile"],
    )
    turb_rate = labels.mean()
    print(f"     → Turbulent bars: {labels.sum():,} / {labels.notna().sum():,}  ({turb_rate:.1%})")

    # ------ 4. ML Classifier ------
    print(f"\n[4/5] Training XGBoost classifier (TimeSeriesSplit 5-fold) …")
    model_cfg = ModelConfig(
        model_type="xgboost",
        n_splits=5,
        xgb_params={
            "n_estimators": 300,
            "max_depth": 4,
            "learning_rate": 0.05,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "eval_metric": "logloss",
            "random_state": 42,
            "n_jobs": -1,
        },
    )
    clf = TurbulenceClassifier(cfg=model_cfg)
    X_tr, X_te, y_tr, y_te = train_test_split_ts(features, labels, test_frac=0.20)
    clf.fit(X_tr, y_tr)

    test_metrics = clf.evaluate(X_te, y_te)
    print(f"\n  ── Test set results ──────────────────────────────")
    print(f"     ROC-AUC  : {test_metrics['roc_auc']:.4f}")
    print(f"     F1       : {test_metrics['f1']:.4f}")
    print(f"     Precision: {test_metrics['precision_turbulent']:.4f}")
    print(f"     Recall   : {test_metrics['recall_turbulent']:.4f}")
    print(f"     Threshold: {clf.threshold_:.3f}")

    proba, regime = clf.predict_series(features)

    # Feature importance
    print(f"\n  ── Top 10 scintillation features ─────────────────")
    imp = clf.feature_importance(X=features, use_shap=False)
    for rank, (name, val) in enumerate(imp.head(10).items(), 1):
        bar = "█" * int(val / imp.iloc[0] * 20)
        print(f"     {rank:2d}. {name:<35s} {bar}")

    # ------ 5. Signal engine + backtest ------
    print(f"\n[5/5] Running signal engine + regime-aware backtest …")
    from signals.engine import TradingSignalEngine, SignalConfig, simulate_signal_pnl

    sig_cfg = SignalConfig(
        entry_threshold=preset["regime_threshold"],
        exit_threshold=preset["regime_threshold"] + 0.15,
        momentum_window=preset["signal_window"],
        stop_loss_pct=0.02,
        profit_target_pct=0.03,
        allow_short=False,
    )
    sig_engine = TradingSignalEngine(cfg=sig_cfg)
    signals    = sig_engine.generate(df, proba)
    pnl_df     = simulate_signal_pnl(df, signals, initial_capital=10_000.0)
    trade_log  = TradingSignalEngine.trade_log(signals, df)
    latest     = TradingSignalEngine.latest_signal(signals)

    n_buys  = int((signals["signal"] ==  1).sum())
    n_sells = int((signals["signal"] == -1).sum())

    print(f"\n  ── Signal engine results ─────────────────────────")
    print(f"     BUY  signals fired : {n_buys}")
    print(f"     SELL signals fired : {n_sells}")
    print(f"     Current signal     : {latest['direction']} ({latest['position']})")
    print(f"     Confidence         : {latest['confidence']:.1%}")
    print(f"     Reason             : {latest['reason']}")

    pnl_total = (pnl_df["equity"].iloc[-1] / 10_000 - 1) * 100
    mdd       = pnl_df["drawdown"].min() * 100
    print(f"\n     Portfolio P&L      : {pnl_total:+.2f}%  (started $10,000)")
    print(f"     Max drawdown       : {mdd:.2f}%")

    if not trade_log.empty:
        wins     = int((trade_log["_pnl_raw"] > 0).sum())
        avg_win  = trade_log[trade_log["_pnl_raw"] > 0]["_pnl_raw"].mean() if wins else 0
        avg_loss = trade_log[trade_log["_pnl_raw"] <= 0]["_pnl_raw"].mean() if len(trade_log)-wins else 0
        print(f"\n  ── Trade log ({len(trade_log)} completed trades) ───────────────")
        print(f"     Win rate  : {wins/max(len(trade_log),1):.0%}")
        print(f"     Avg win   : {avg_win:+.2f}%")
        print(f"     Avg loss  : {avg_loss:+.2f}%")
        disp_cols = [c for c in trade_log.columns if not c.startswith("_")]
        print(trade_log[disp_cols].to_string(index=False))

    bt_cfg  = BacktestConfig(
        strategy=preset["strategy"], signal_window=preset["signal_window"],
        regime_threshold=preset["regime_threshold"], turbulent_size=preset["turbulent_size"],
    )
    results = BacktestEngine(cfg=bt_cfg).run(df, turbulence_proba=proba, regime_label=regime)
    b = results["metrics"].get("baseline", {})
    f = results["metrics"].get("filtered", {})

    print(f"\n  ── Regime backtest comparison ─────────────────────")
    _row = lambda lbl, bv, fv, hi=True: (
        f"  {'  ✓' if (fv>bv if hi else fv<bv) else '   '}"
        f"  {lbl:<22}  Baseline={bv:>8.3f}   ML-Filtered={fv:>8.3f}  (Δ{fv-bv:+.3f})"
    )
    print(_row("Sharpe",      b.get("sharpe",0),           f.get("sharpe",0)))
    print(_row("Max DD (%)",  b.get("max_drawdown_pct",0), f.get("max_drawdown_pct",0), hi=False))
    print(_row("Ann vol (%)", b.get("ann_vol_pct",0),      f.get("ann_vol_pct",0),      hi=False))

    print(f"\n{'='*65}\n")

    return {
        "df": df, "features": features, "labels": labels,
        "proba": proba, "regime": regime, "clf": clf,
        "signals": signals, "pnl": pnl_df, "trade_log": trade_log,
        "latest": latest, "results": results,
    }


def _bars_per_year(df: pd.DataFrame) -> int:
    if len(df) < 2:
        return 252
    delta = (df.index[1] - df.index[0]).total_seconds()
    bars_per_day = 23_400 / max(delta, 1)
    return int(bars_per_day * 252)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="MarketScintillation example runner")
    parser.add_argument("--ticker",    default="UAMY",  help="Ticker symbol (default: UAMY)")
    parser.add_argument("--period",    default=None,    help="yfinance period override (e.g. 7d, 14d)")
    parser.add_argument("--synthetic", action="store_true", help="Use synthetic data instead of live")
    args = parser.parse_args()

    if args.period and args.ticker in PRESETS:
        PRESETS[args.ticker]["period"] = args.period

    run(ticker=args.ticker, synthetic=args.synthetic)


if __name__ == "__main__":
    main()

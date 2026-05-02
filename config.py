"""
Global configuration for MarketScintillation.
All tunable parameters and API keys live here.
"""

from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# API credentials (replace with real keys or set via environment variables)
# ---------------------------------------------------------------------------
POLYGON_API_KEY: str = "YOUR_POLYGON_API_KEY"   # https://polygon.io
YFINANCE_FALLBACK: bool = True                   # use yfinance when Polygon unavailable


# ---------------------------------------------------------------------------
# Feature engineering defaults
# ---------------------------------------------------------------------------
@dataclass
class FeatureConfig:
    # Rolling window sizes (in bars / seconds for 1-s aggregated data)
    windows: list = field(default_factory=lambda: [10, 30, 60, 300])  # 10s, 30s, 1m, 5m
    detrend_window: int = 60          # window for adaptive moving-average detrend
    psd_nperseg: int = 32             # segment length for Welch PSD
    min_periods: int = 5              # minimum observations before computing a feature
    eps: float = 1e-10                # numerical stability guard


# ---------------------------------------------------------------------------
# Labeling / regime classification
# ---------------------------------------------------------------------------
@dataclass
class LabelConfig:
    method: str = "future_vol"        # "future_vol" | "sharp_move"
    future_window: int = 60           # bars ahead to measure future realized vol
    turbulence_quantile: float = 0.75 # top-X% realized vol → turbulent label
    sharp_move_z: float = 2.5         # |return| > Z * rolling_std → turbulent


# ---------------------------------------------------------------------------
# ML model defaults
# ---------------------------------------------------------------------------
@dataclass
class ModelConfig:
    model_type: str = "xgboost"       # "xgboost" | "lightgbm"
    n_splits: int = 5                 # TimeSeriesSplit folds
    test_size_frac: float = 0.20      # hold-out test fraction
    xgb_params: dict = field(default_factory=lambda: {
        "n_estimators": 400,
        "max_depth": 5,
        "learning_rate": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "eval_metric": "logloss",
        "random_state": 42,
        "n_jobs": -1,
    })
    lgbm_params: dict = field(default_factory=lambda: {
        "n_estimators": 400,
        "max_depth": 5,
        "learning_rate": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "random_state": 42,
        "n_jobs": -1,
        "verbose": -1,
    })


# ---------------------------------------------------------------------------
# Backtesting defaults
# ---------------------------------------------------------------------------
@dataclass
class BacktestConfig:
    initial_capital: float = 100_000.0
    position_size: float = 1.0        # fraction of capital per trade
    turbulent_size: float = 0.0       # position size during turbulent regime (0 = flat)
    transaction_cost_bps: float = 0.5 # round-trip cost in basis points
    signal_window: int = 10           # bars for momentum / mean-reversion signal
    strategy: str = "momentum"        # "momentum" | "mean_reversion"
    regime_threshold: float = 0.50    # ML probability threshold → turbulent


FEATURE_CFG = FeatureConfig()
LABEL_CFG = LabelConfig()
MODEL_CFG = ModelConfig()
BACKTEST_CFG = BacktestConfig()

"""
MarketScintillation — Robinhood-Style Trading Dashboard
========================================================
Launch:
    streamlit run app/dashboard.py

Panels
------
1. Signal buzz card  — BUY / SELL / HOLD with confidence meter
2. Portfolio card     — equity curve, P&L, Robinhood-style stats
3. Price chart        — candlestick + regime bands + signal markers
4. Turbulence index   — ML probability + threshold
5. Trade log          — every completed trade with P&L
6. Feature importance — top scintillation drivers
"""

from __future__ import annotations

import io
import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from datetime import datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from config import FeatureConfig, ModelConfig, BacktestConfig
from data.loader import generate_synthetic_hf_data
from features.extractor import ScintillationFeatureExtractor, label_turbulent_regimes
from models.classifier import TurbulenceClassifier, train_test_split_ts
from signals.engine import TradingSignalEngine, SignalConfig, simulate_signal_pnl
from signals.forecaster import RegimeForecaster
from backtester.engine import BacktestEngine
from utils.helpers import get_logger, log_returns

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Robinhood colour palette
# ---------------------------------------------------------------------------
RH_GREEN      = "#00C805"
RH_RED        = "#FF5000"
RH_GOLD       = "#F0B429"
RH_BG         = "#0A0A0A"
RH_CARD       = "#111111"
RH_BORDER     = "#1E1E1E"
RH_TEXT       = "#FFFFFF"
RH_SUBTEXT    = "#8C8C8C"
RH_CHART_LINE = "#FFFFFF"

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="MarketScintillation",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Global CSS — Robinhood feel
# ---------------------------------------------------------------------------
st.markdown(f"""
<style>
  /* ── Base ── */
  html, body, [class*="css"] {{
      font-family: 'Inter', 'Helvetica Neue', Arial, sans-serif;
      background-color: {RH_BG};
      color: {RH_TEXT};
  }}
  .block-container {{ padding-top: 1.2rem; padding-bottom: 0; }}

  /* ── Cards ── */
  .rh-card {{
      background: {RH_CARD};
      border: 1px solid {RH_BORDER};
      border-radius: 12px;
      padding: 18px 22px;
      margin-bottom: 10px;
  }}

  /* ── Price display ── */
  .rh-price {{
      font-size: 2.8rem;
      font-weight: 700;
      letter-spacing: -0.5px;
      line-height: 1.1;
      color: {RH_TEXT};
  }}
  .rh-change-pos {{
      font-size: 1rem;
      color: {RH_GREEN};
      font-weight: 600;
  }}
  .rh-change-neg {{
      font-size: 1rem;
      color: {RH_RED};
      font-weight: 600;
  }}
  .rh-label {{
      font-size: 0.72rem;
      color: {RH_SUBTEXT};
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 2px;
  }}

  /* ── Signal buzz ── */
  .buzz-buy {{
      background: linear-gradient(135deg, #003A02 0%, #004D03 100%);
      border: 2px solid {RH_GREEN};
      border-radius: 14px;
      padding: 22px 26px;
      text-align: center;
  }}
  .buzz-sell {{
      background: linear-gradient(135deg, #3A0000 0%, #4D0000 100%);
      border: 2px solid {RH_RED};
      border-radius: 14px;
      padding: 22px 26px;
      text-align: center;
  }}
  .buzz-hold {{
      background: linear-gradient(135deg, #1A1A1A 0%, #222222 100%);
      border: 2px solid #444;
      border-radius: 14px;
      padding: 22px 26px;
      text-align: center;
  }}
  .buzz-label {{
      font-size: 2.2rem;
      font-weight: 800;
      letter-spacing: 0.15em;
  }}
  .buzz-sub {{
      font-size: 0.78rem;
      color: {RH_SUBTEXT};
      margin-top: 4px;
  }}

  /* ── Metric pill ── */
  .rh-metric {{
      background: #161616;
      border-radius: 8px;
      padding: 10px 14px;
      display: inline-block;
      min-width: 110px;
  }}
  .rh-metric-value {{
      font-size: 1.1rem;
      font-weight: 700;
  }}

  /* ── Trade table ── */
  .trade-win  {{ color: {RH_GREEN}; font-weight: 600; }}
  .trade-loss {{ color: {RH_RED};   font-weight: 600; }}

  /* ── Confidence bar ── */
  .conf-track {{
      background: #222;
      border-radius: 4px;
      height: 6px;
      overflow: hidden;
      margin-top: 6px;
  }}
  .conf-fill-g {{
      background: {RH_GREEN};
      height: 100%;
      border-radius: 4px;
  }}
  .conf-fill-r {{
      background: {RH_RED};
      height: 100%;
      border-radius: 4px;
  }}
  .conf-fill-y {{
      background: {RH_GOLD};
      height: 100%;
      border-radius: 4px;
  }}

  /* ── Sidebar ── */
  [data-testid="stSidebar"] {{
      background-color: #0D0D0D;
      border-right: 1px solid {RH_BORDER};
  }}
  [data-testid="stSidebar"] .stSelectbox label,
  [data-testid="stSidebar"] .stSlider label,
  [data-testid="stSidebar"] .stCheckbox label {{
      font-size: 0.78rem;
      color: {RH_SUBTEXT};
      text-transform: uppercase;
      letter-spacing: 0.05em;
  }}
  div[data-testid="stMetric"] {{
      background: {RH_CARD};
      border-radius: 10px;
      padding: 10px 14px;
      border: 1px solid {RH_BORDER};
  }}
  div[data-testid="stMetric"] label {{
      font-size: 0.68rem !important;
      color: {RH_SUBTEXT} !important;
      text-transform: uppercase;
      letter-spacing: 0.07em;
  }}
  div[data-testid="stMetric"] [data-testid="stMetricValue"] {{
      font-size: 1.2rem !important;
      font-weight: 700 !important;
  }}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Preset configurations
# ---------------------------------------------------------------------------
_PRESETS = {
    "📡 UAMY — US Antimony (137% vol)": {
        "ticker": "UAMY", "use_synthetic": False,
        "windows": [5, 15, 30, 60], "detrend_window": 30,
        "label_method": "future_vol", "future_window": 15,
        "turbulence_quantile": 0.70,
        "entry_threshold": 0.40, "exit_threshold": 0.55,
        "momentum_window": 5, "stop_loss_pct": 0.02,
        "profit_target_pct": 0.03, "allow_short": False,
    },
    "🟢 HOOD — Robinhood (84% vol)": {
        "ticker": "HOOD", "use_synthetic": False,
        "windows": [5, 15, 30, 60], "detrend_window": 30,
        "label_method": "future_vol", "future_window": 15,
        "turbulence_quantile": 0.72,
        "entry_threshold": 0.38, "exit_threshold": 0.55,
        "momentum_window": 5, "stop_loss_pct": 0.025,
        "profit_target_pct": 0.035, "allow_short": False,
    },
    "🟩 NVDA — Nvidia (38% vol)": {
        "ticker": "NVDA", "use_synthetic": False,
        "windows": [5, 15, 30, 60], "detrend_window": 30,
        "label_method": "future_vol", "future_window": 20,
        "turbulence_quantile": 0.75,
        "entry_threshold": 0.42, "exit_threshold": 0.58,
        "momentum_window": 8, "stop_loss_pct": 0.015,
        "profit_target_pct": 0.025, "allow_short": False,
    },
    "🚀 RKLB — Rocket Lab (93% vol)": {
        "ticker": "RKLB", "use_synthetic": False,
        "windows": [5, 15, 30, 60], "detrend_window": 30,
        "label_method": "future_vol", "future_window": 15,
        "turbulence_quantile": 0.72,
        "entry_threshold": 0.40, "exit_threshold": 0.55,
        "momentum_window": 5, "stop_loss_pct": 0.025,
        "profit_target_pct": 0.035, "allow_short": False,
    },
    "🔬 Synthetic demo (no API key)": {
        "ticker": "SYNTHETIC", "use_synthetic": True,
        "windows": [10, 30, 60, 300], "detrend_window": 60,
        "label_method": "future_vol", "future_window": 60,
        "turbulence_quantile": 0.75,
        "entry_threshold": 0.40, "exit_threshold": 0.55,
        "momentum_window": 10, "stop_loss_pct": 0.02,
        "profit_target_pct": 0.03, "allow_short": False,
    },
}


# ---------------------------------------------------------------------------
# Cached pipeline
# ---------------------------------------------------------------------------

def _yf_to_df(raw: pd.DataFrame, tag_session: bool = False) -> pd.DataFrame:
    """Normalise a raw yfinance DataFrame to the project schema.

    When tag_session=True adds a 'session' column:
      'pre'     04:00–09:29 ET
      'regular' 09:30–16:00 ET
      'post'    16:01–20:00 ET
    """
    raw = raw.copy()
    raw.index = pd.to_datetime(raw.index, utc=True)
    raw.index.name = "timestamp"
    raw.columns = [c.lower() for c in raw.columns]
    raw["returns"] = log_returns(raw["close"]).fillna(0.0)
    raw["volume"]  = raw["volume"].fillna(0.0)
    df = raw[[c for c in ["open","high","low","close","volume","returns"] if c in raw.columns]]
    if tag_session:
        # Convert to ET for session classification
        et = df.index.tz_convert("America/New_York")
        h  = et.hour + et.minute / 60.0
        sess = pd.Series("regular", index=df.index)
        sess[h < 9.5]  = "pre"
        sess[h >= 16.0] = "post"
        df = df.copy()
        df["session"] = sess.values
    return df


@st.cache_data(show_spinner=False, ttl=3600)
def load_data(ticker: str, period: str, use_synthetic: bool) -> pd.DataFrame:
    """Historical training data — cached for 1 h so the model stays stable.
    Fetches pre/post-market bars (prepost=True) so the full 4 AM–8 PM
    session is visible on the chart.
    """
    if use_synthetic:
        return generate_synthetic_hf_data(n_bars=23_400, seed=42)
    try:
        import yfinance as yf
        raw = yf.Ticker(ticker).history(
            period=period, interval="1m", auto_adjust=True, prepost=True
        )
        if raw.empty:
            raise ValueError("empty")
        return _yf_to_df(raw, tag_session=True)
    except Exception as exc:
        st.warning(f"Could not fetch {ticker}: {exc} — using synthetic data.")
        return generate_synthetic_hf_data(n_bars=23_400, seed=42)


@st.cache_data(show_spinner=False, ttl=15)   # 15-second live cache
def load_live_bar(ticker: str, use_synthetic: bool) -> pd.DataFrame:
    """
    Fetch the most recent 1-day 1-minute bars including pre/post market.
    Short TTL so the dashboard refreshes every ~15 s in live mode.
    """
    if use_synthetic:
        return pd.DataFrame()
    try:
        import yfinance as yf
        raw = yf.Ticker(ticker).history(
            period="1d", interval="1m", auto_adjust=True, prepost=True
        )
        if raw.empty:
            return pd.DataFrame()
        return _yf_to_df(raw, tag_session=True)
    except Exception:
        return pd.DataFrame()


@st.cache_data(show_spinner=False, ttl=3600)
def run_pipeline(
    df_json: str,
    windows: list, detrend_window: int,
    label_method: str, future_window: int, quantile: float,
    entry_threshold: float, exit_threshold: float,
    momentum_window: int, stop_loss_pct: float,
    profit_target_pct: float, allow_short: bool,
) -> dict:
    """Full pipeline: features → classifier → signals → backtest."""
    df = pd.read_json(io.StringIO(df_json), orient="split")
    df.index = pd.to_datetime(df.index, utc=True)

    # Strip non-numeric session tag before ML pipeline; keep only regular-hours
    # bars for training so the classifier isn't confused by thinner pre/post markets.
    ohlcv_cols = ["open", "high", "low", "close", "volume", "returns"]
    if "session" in df.columns:
        df_regular = df[df["session"] == "regular"][ohlcv_cols]
    else:
        df_regular = df[[c for c in ohlcv_cols if c in df.columns]]

    # 1. Features
    feat_cfg = FeatureConfig(
        windows=windows, detrend_window=detrend_window,
        psd_nperseg=min(32, windows[0]),
    )
    features = ScintillationFeatureExtractor(cfg=feat_cfg).transform(df_regular)

    # 2. Labels + classifier
    labels = label_turbulent_regimes(
        df_regular, method=label_method, future_window=future_window, quantile=quantile,
    )
    clf = TurbulenceClassifier(cfg=ModelConfig(
        model_type="xgboost", n_splits=5,
        xgb_params={"n_estimators": 300, "max_depth": 4, "learning_rate": 0.05,
                    "subsample": 0.8, "colsample_bytree": 0.8,
                    "eval_metric": "logloss", "random_state": 42, "n_jobs": -1},
    ))
    X_tr, X_te, y_tr, y_te = train_test_split_ts(features, labels, test_frac=0.20)
    clf.fit(X_tr, y_tr)
    test_metrics = clf.evaluate(X_te, y_te)

    proba, regime = clf.predict_series(features)
    importance    = clf.feature_importance(X=features, use_shap=False)

    # 3. Signal engine (runs on regular-hours bars only)
    sig_cfg = SignalConfig(
        entry_threshold=entry_threshold,
        exit_threshold=exit_threshold,
        momentum_window=momentum_window,
        stop_loss_pct=stop_loss_pct,
        profit_target_pct=profit_target_pct if profit_target_pct > 0 else None,
        allow_short=allow_short,
        min_hold_bars=2,
    )
    engine  = TradingSignalEngine(cfg=sig_cfg)
    signals = engine.generate(df_regular, proba)
    pnl_df  = simulate_signal_pnl(df_regular, signals, initial_capital=10_000.0)

    from signals.engine import TradingSignalEngine as _E
    latest  = _E.latest_signal(signals)
    trade_log = _E.trade_log(signals, df_regular)

    # 4. Comparison backtest (regime-filtered momentum)
    bt_cfg  = BacktestConfig(strategy="momentum", signal_window=momentum_window,
                              regime_threshold=entry_threshold, turbulent_size=0.0)
    bt_res  = BacktestEngine(cfg=bt_cfg).run(df_regular, turbulence_proba=proba, regime_label=regime)

    # 5. Regime forecast (AR-1 projection forward)
    forecaster = RegimeForecaster(
        entry_threshold=entry_threshold,
        exit_threshold=exit_threshold,
        lookback=min(60, len(proba) // 4),
        horizons_min=[1, 5, 15],
    )
    fc = forecaster.forecast(proba, current_position=latest["position"])
    forecast_dict = {
        "horizons":        fc.horizons_min,
        "proba_forecast":  fc.proba_forecast,
        "signal_forecast": fc.signal_forecast,
        "next_signal_bar": fc.next_signal_bar,
        "next_signal_type": fc.next_signal_type,
        "confidence":      fc.confidence,
        "summary":         fc.summary,
    }

    return {
        "proba":        proba.to_json(orient="split", date_format="iso"),
        "regime":       regime.to_json(orient="split", date_format="iso"),
        "signals_json": signals.to_json(orient="split", date_format="iso"),
        "pnl_json":     pnl_df.to_json(orient="split", date_format="iso"),
        "importance":   importance.to_json(orient="split"),
        "latest":       latest,
        "forecast":     forecast_dict,
        "trade_log":    trade_log.to_json(orient="split") if not trade_log.empty else "{}",
        "test_metrics": {k: v for k, v in test_metrics.items() if k != "classification_report"},
        "cv_scores":    clf.cv_scores_,
        "bt_baseline":  bt_res["baseline"]["equity"].to_json(orient="split", date_format="iso"),
        "bt_filtered":  bt_res["filtered"]["equity"].to_json(orient="split", date_format="iso"),
        "bt_metrics":   bt_res["metrics"],
        "turb_rate":    float(regime.mean() * 100),
        "clf_json":     None,   # placeholder for live inference
    }


# ---------------------------------------------------------------------------
# Chart builders
# ---------------------------------------------------------------------------

def _rj(s: str, typ="frame"):
    """Safely read JSON using StringIO (pandas 2.x compat)."""
    if typ == "series":
        out = pd.read_json(io.StringIO(s), orient="split", typ="series")
        out.index = pd.to_datetime(out.index, utc=True)
        return out
    out = pd.read_json(io.StringIO(s), orient="split")
    out.index = pd.to_datetime(out.index, utc=True)
    return out


def _shade_extended_hours(fig, df, row=1, col=1):
    """
    Add translucent bands for pre-market (blue) and after-hours (purple)
    so viewers instantly see which bars are outside regular trading.
    Works even when df has no 'session' column (no-op then).
    """
    if "session" not in df.columns:
        return
    kw = dict(row=row, col=col)
    for sess, color in [("pre", "rgba(30,144,255,0.07)"), ("post", "rgba(160,32,240,0.07)")]:
        mask = df["session"] == sess
        if not mask.any():
            continue
        # Group consecutive bars into blocks
        idx  = df.index[mask]
        blks, s, p = [], idx[0], idx[0]
        for t in idx[1:]:
            gap = (t - p).total_seconds()
            if gap > 300:          # >5-min gap → new block
                blks.append((s, p))
                s = t
            p = t
        blks.append((s, p))
        label = "Pre-market" if sess == "pre" else "After-hours"
        for i, (x0, x1) in enumerate(blks):
            fig.add_vrect(
                x0=x0.strftime("%Y-%m-%d %H:%M:%S"),
                x1=x1.strftime("%Y-%m-%d %H:%M:%S"),
                fillcolor=color, line_width=0,
                annotation_text=label if i == 0 else "",
                annotation_position="top left",
                annotation_font=dict(color="#6699cc" if sess == "pre" else "#aa77ff", size=9),
                **kw,
            )


def chart_price(df, signals_df, regime, ticker):
    """Candlestick + session bands + regime bands + BUY/SELL markers."""
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        row_heights=[0.75, 0.25], vertical_spacing=0.02,
    )

    # Extended-hours shading (drawn first so it's behind candles)
    _shade_extended_hours(fig, df, row=1, col=1)

    # Candlestick
    if all(c in df.columns for c in ["open","high","low","close"]):
        fig.add_trace(go.Candlestick(
            x=df.index, open=df["open"], high=df["high"],
            low=df["low"], close=df["close"],
            increasing_line_color=RH_GREEN, decreasing_line_color=RH_RED,
            increasing_fillcolor=RH_GREEN, decreasing_fillcolor=RH_RED,
            name=ticker, showlegend=False,
        ), row=1, col=1)
    else:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["close"],
            line=dict(color=RH_GREEN, width=1.5), name=ticker,
        ), row=1, col=1)

    # Regime bands
    _add_bands(fig, regime, row=1, col=1)

    # BUY markers ▲
    buys = signals_df[signals_df["signal"] == 1]
    if not buys.empty:
        buy_close = df["close"].reindex(buys.index, method="nearest")
        fig.add_trace(go.Scatter(
            x=buys.index,
            y=buy_close * 0.995,
            mode="markers",
            marker=dict(symbol="triangle-up", size=10, color=RH_GREEN,
                        line=dict(color="white", width=1)),
            name="BUY", hovertemplate="%{x}<br>BUY @ $%{y:.2f}<extra></extra>",
        ), row=1, col=1)

    # SELL markers ▼
    sells = signals_df[signals_df["signal"] == -1]
    if not sells.empty:
        sell_close = df["close"].reindex(sells.index, method="nearest")
        fig.add_trace(go.Scatter(
            x=sells.index,
            y=sell_close * 1.005,
            mode="markers",
            marker=dict(symbol="triangle-down", size=10, color=RH_RED,
                        line=dict(color="white", width=1)),
            name="SELL", hovertemplate="%{x}<br>SELL @ $%{y:.2f}<extra></extra>",
        ), row=1, col=1)

    # Volume (colour by session when available)
    if "session" in df.columns:
        vol_colors = []
        for r, sess in zip(df["returns"].fillna(0), df["session"]):
            if sess == "pre":
                vol_colors.append("rgba(30,144,255,0.5)")
            elif sess == "post":
                vol_colors.append("rgba(160,32,240,0.5)")
            else:
                vol_colors.append(RH_GREEN if r >= 0 else RH_RED)
    else:
        vol_colors = [RH_GREEN if r >= 0 else RH_RED for r in df["returns"].fillna(0)]

    fig.add_trace(go.Bar(
        x=df.index, y=df["volume"],
        marker_color=vol_colors, opacity=0.7, showlegend=False,
    ), row=2, col=1)

    # Legend rows for session colours
    for label, color in [("Pre-market", "rgba(30,144,255,0.5)"),
                          ("After-hours", "rgba(160,32,240,0.5)")]:
        fig.add_trace(go.Scatter(
            x=[None], y=[None], mode="markers",
            marker=dict(color=color, size=8, symbol="square"),
            name=label, showlegend=True,
        ), row=1, col=1)

    fig.update_layout(
        height=520, template="plotly_dark",
        paper_bgcolor=RH_BG, plot_bgcolor="#0D0D0D",
        margin=dict(l=0, r=0, t=8, b=0),
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", y=1.04, font=dict(size=10)),
        font=dict(color=RH_TEXT),
    )
    fig.update_yaxes(gridcolor="#1A1A1A", zerolinecolor="#1A1A1A")
    fig.update_xaxes(gridcolor="#1A1A1A")
    return fig


def chart_turbulence(proba, entry_thr, exit_thr):
    fig = go.Figure()

    # Gradient fill — green below entry, gold between, red above exit
    fig.add_trace(go.Scatter(
        x=proba.index, y=proba.values,
        fill="tozeroy",
        fillcolor="rgba(0,200,5,0.08)",
        line=dict(color=RH_GREEN, width=1.5),
        name="P(Turbulent)",
        hovertemplate="%{x}<br>P(Turb)=%{y:.3f}<extra></extra>",
    ))

    fig.add_hline(y=entry_thr, line=dict(color=RH_GREEN, dash="dot", width=1.2),
                  annotation_text=f"Entry gate {entry_thr:.2f}",
                  annotation_font=dict(color=RH_GREEN, size=10),
                  annotation_position="top left")
    fig.add_hline(y=exit_thr, line=dict(color=RH_RED, dash="dot", width=1.2),
                  annotation_text=f"Exit gate {exit_thr:.2f}",
                  annotation_font=dict(color=RH_RED, size=10),
                  annotation_position="top left")

    fig.update_layout(
        height=200, template="plotly_dark",
        paper_bgcolor=RH_BG, plot_bgcolor="#0D0D0D",
        yaxis=dict(title="P(Turbulent)", range=[0, 1], gridcolor="#1A1A1A"),
        xaxis=dict(gridcolor="#1A1A1A"),
        margin=dict(l=0, r=0, t=8, b=0),
        showlegend=False,
        font=dict(color=RH_TEXT),
    )
    return fig


def chart_equity(signal_equity, baseline_equity, filtered_equity, regime):
    fig = go.Figure()
    _add_bands(fig, regime)

    if filtered_equity is not None:
        fig.add_trace(go.Scatter(
            x=filtered_equity.index, y=filtered_equity.values,
            name="Regime-Filtered", line=dict(color=RH_GOLD, width=1.5, dash="dot"),
        ))
    fig.add_trace(go.Scatter(
        x=signal_equity.index, y=signal_equity.values,
        name="Signal Engine", line=dict(color=RH_GREEN, width=2.2),
        fill="tozeroy", fillcolor="rgba(0,200,5,0.06)",
    ))
    if baseline_equity is not None:
        fig.add_trace(go.Scatter(
            x=baseline_equity.index, y=baseline_equity.values,
            name="Baseline", line=dict(color=RH_SUBTEXT, width=1.2, dash="dash"),
        ))

    fig.add_hline(y=10_000, line=dict(color="#333", dash="dot", width=1))
    fig.update_layout(
        height=300, template="plotly_dark",
        paper_bgcolor=RH_BG, plot_bgcolor="#0D0D0D",
        yaxis=dict(title="Portfolio Value ($)", tickprefix="$", gridcolor="#1A1A1A"),
        xaxis=dict(gridcolor="#1A1A1A"),
        margin=dict(l=0, r=0, t=8, b=0),
        legend=dict(orientation="h", y=1.06, font=dict(size=11)),
        font=dict(color=RH_TEXT),
    )
    return fig


def chart_importance(importance, top_n=15):
    top = importance.nlargest(top_n).iloc[::-1]
    colors = [RH_GREEN if "s4" in n or "sigma" in n or "psd" in n or "hp_" in n
                       or "refl" in n or "det_" in n or "range" in n
              else RH_GOLD for n in top.index]
    fig = go.Figure(go.Bar(
        x=top.values, y=top.index,
        orientation="h",
        marker=dict(color=colors, line=dict(width=0)),
    ))
    fig.update_layout(
        height=max(280, top_n * 19),
        template="plotly_dark",
        paper_bgcolor=RH_BG, plot_bgcolor="#0D0D0D",
        xaxis=dict(title="Importance", gridcolor="#1A1A1A"),
        yaxis=dict(gridcolor="#1A1A1A"),
        margin=dict(l=0, r=0, t=8, b=0),
        font=dict(color=RH_TEXT, size=11),
    )
    return fig


def _add_bands(fig, regime, row=None, col=None):
    """Shade turbulent periods red."""
    turb_idx = regime[regime == 1].index if hasattr(regime, "values") else pd.Index([])
    if turb_idx.empty:
        return
    blocks, start, prev = [], turb_idx[0], turb_idx[0]
    for ts in turb_idx[1:]:
        if (ts - prev).total_seconds() > 180:
            blocks.append((start, prev))
            start = ts
        prev = ts
    blocks.append((start, prev))
    kw = dict(row=row, col=col if col is not None else 1) if row is not None else {}
    for x0, x1 in blocks:
        fig.add_vrect(x0=x0, x1=x1,
                      fillcolor="rgba(255,80,0,0.08)",
                      layer="below", line_width=0, **kw)


def chart_forecast(proba: pd.Series, forecast: dict, entry_thr: float, exit_thr: float) -> go.Figure:
    """
    Combine recent P(turbulent) history with the AR-1 forward projection.
    Historical section: solid green line.
    Forecast section:   dashed line with uncertainty band, BUY/SELL zone colouring.
    """
    # Last 60 bars of history
    hist = proba.iloc[-60:]
    last_ts = hist.index[-1]

    # Build forecast timestamps (approximate — 1 bar ≈ 1 minute)
    freq_sec = 60  # default to 1 min
    if len(proba) >= 2:
        freq_sec = max(1, int((proba.index[1] - proba.index[0]).total_seconds()))

    fc_times = [last_ts + pd.Timedelta(seconds=freq_sec * k)
                for k in range(1, max(forecast["horizons"]) + 2)]

    # Interpolate forecast values at the named horizons
    h_max  = max(forecast["horizons"])
    fc_arr = np.interp(
        range(1, h_max + 2),
        [0] + forecast["horizons"],
        [float(hist.iloc[-1])] + forecast["proba_forecast"],
    )

    # Uncertainty band (simple ±0.08 widening)
    sigma = np.array([0.0] + [0.04 * np.sqrt(k) for k in range(1, h_max + 2)])
    upper = np.clip(fc_arr + sigma[:len(fc_arr)], 0, 1)
    lower = np.clip(fc_arr - sigma[:len(fc_arr)], 0, 1)

    fig = go.Figure()

    # Historical P(turbulent)
    fig.add_trace(go.Scatter(
        x=hist.index, y=hist.values,
        name="P(Turbulent) — history",
        line=dict(color=RH_GREEN, width=2),
        hovertemplate="%{x|%H:%M}<br>P=%{y:.3f}<extra></extra>",
    ))

    # Forecast uncertainty band
    fig.add_trace(go.Scatter(
        x=fc_times + fc_times[::-1],
        y=list(upper) + list(lower[::-1]),
        fill="toself",
        fillcolor="rgba(240,180,41,0.12)",
        line=dict(width=0),
        showlegend=False,
        hoverinfo="skip",
    ))

    # Forecast centre line
    fig.add_trace(go.Scatter(
        x=fc_times, y=fc_arr,
        name="Forecast (AR-1)",
        line=dict(color=RH_GOLD, width=2, dash="dash"),
        hovertemplate="+%{pointNumber}min<br>P=%{y:.3f}<extra></extra>",
    ))

    # Horizon markers
    for h, p, s in zip(forecast["horizons"], forecast["proba_forecast"], forecast["signal_forecast"]):
        ts = last_ts + pd.Timedelta(seconds=freq_sec * h)
        col = RH_GREEN if "BUY" in s else (RH_RED if "SELL" in s else RH_SUBTEXT)
        fig.add_annotation(
            x=ts, y=p,
            text=f"+{h}m<br>{p:.2f}",
            showarrow=True, arrowhead=2, arrowsize=0.8,
            arrowcolor=col, font=dict(color=col, size=10),
            bgcolor=RH_CARD, bordercolor=col,
        )

    # Threshold lines
    fig.add_hline(y=entry_thr, line=dict(color=RH_GREEN, dash="dot", width=1),
                  annotation_text=f"BUY zone <{entry_thr:.2f}",
                  annotation_font=dict(color=RH_GREEN, size=9),
                  annotation_position="bottom right")
    fig.add_hline(y=exit_thr, line=dict(color=RH_RED, dash="dot", width=1),
                  annotation_text=f"SELL zone >{exit_thr:.2f}",
                  annotation_font=dict(color=RH_RED, size=9),
                  annotation_position="top right")

    # Vertical "now" line — add_vline(x=Timestamp) triggers a Plotly 6 bug
    # (its internal _mean([ts, ts]) calls ts.__radd__(int)). Use add_shape instead.
    now_str = last_ts.strftime("%Y-%m-%d %H:%M:%S")
    fig.add_shape(type="line", x0=now_str, x1=now_str, y0=0, y1=1,
                  xref="x", yref="paper",
                  line=dict(color="#555", dash="dot", width=1))
    fig.add_annotation(x=now_str, y=1.04, text="NOW", showarrow=False,
                       xref="x", yref="paper",
                       font=dict(color="#888", size=9), yanchor="bottom")

    fig.update_layout(
        height=260,
        template="plotly_dark",
        paper_bgcolor=RH_BG, plot_bgcolor="#0D0D0D",
        yaxis=dict(title="P(Turbulent)", range=[0, 1], gridcolor="#1A1A1A"),
        xaxis=dict(gridcolor="#1A1A1A"),
        margin=dict(l=0, r=0, t=8, b=0),
        legend=dict(orientation="h", y=1.08, font=dict(size=10)),
        font=dict(color=RH_TEXT),
    )
    return fig


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------

def _fmt_dollar(v: float) -> str:
    return f"${v:,.2f}"


def _fmt_pct(v: float, sign=True) -> str:
    return f"{'+' if v >= 0 and sign else ''}{v:.2f}%"


def _color(v: float) -> str:
    return RH_GREEN if v >= 0 else RH_RED


def _render_prediction_card(
    fc: dict, price: float, entry_thr: float, exit_thr: float, latest: dict
) -> None:
    """
    Concrete, opinionated forward-looking prediction card.

    Derives a single plain-language call (STRONG BUY / BUY / HOLD / SELL /
    STRONG SELL) from the AR-1 forecast, the current turbulence level, and
    the signal engine's current position.  Shows an implied price target and
    stop-loss level based on the signal-engine parameters embedded in `latest`.
    """
    p_now   = fc["proba_forecast"][0] if fc["proba_forecast"] else 0.5
    p_15    = fc["proba_forecast"][-1] if fc["proba_forecast"] else 0.5
    conf    = fc["confidence"]
    nb      = fc["next_signal_bar"]
    nt      = fc["next_signal_type"]
    pos     = latest["position"]          # "LONG" / "FLAT" / "SHORT"
    sig     = latest["direction"]         # "BUY" / "SELL" / "HOLD"
    sig_conf = latest["confidence"]

    # ── Derive verdict ────────────────────────────────────────────────────
    # Momentum score: combine current signal confidence with regime trajectory
    trending_down = p_15 > p_now + 0.03   # turbulence rising → bearish
    trending_up   = p_15 < p_now - 0.03   # turbulence falling → bullish

    if p_now < entry_thr and sig_conf > 0.65 and not trending_down:
        verdict      = "STRONG BUY"
        verdict_col  = RH_GREEN
        verdict_icon = "▲▲"
        action_text  = ("Regime is quiet and momentum is positive. "
                        "The model expects turbulence to stay low — "
                        "conditions favour entering or holding a long position.")
    elif p_now < entry_thr and not trending_down:
        verdict      = "BUY"
        verdict_col  = RH_GREEN
        verdict_icon = "▲"
        action_text  = ("Turbulence is below the entry gate. "
                        "Momentum conditions support a long entry. "
                        "Watch for regime shift above {:.2f}.".format(exit_thr))
    elif p_now > exit_thr and sig_conf < 0.40:
        verdict      = "STRONG SELL"
        verdict_col  = RH_RED
        verdict_icon = "▼▼"
        action_text  = ("High turbulence detected — the regime is clearly stressed. "
                        "Close any open long and stay flat until P(turb) drops "
                        "back below {:.2f}.".format(entry_thr))
    elif p_now > exit_thr or trending_down:
        verdict      = "SELL / EXIT"
        verdict_col  = RH_RED
        verdict_icon = "▼"
        action_text  = ("Turbulence is elevated or rising. "
                        "The model recommends reducing exposure. "
                        "Re-enter only after regime cools below {:.2f}.".format(entry_thr))
    else:
        verdict      = "HOLD"
        verdict_col  = RH_GOLD
        verdict_icon = "◆"
        action_text  = ("Regime is transitioning — neither clearly quiet nor turbulent. "
                        "Stay in current position and monitor for a decisive move "
                        "through {:.2f} or {:.2f}.".format(entry_thr, exit_thr))

    # ── Implied price levels ──────────────────────────────────────────────
    stop_pct    = 0.02    # mirror SignalConfig default
    target_pct  = 0.03
    if verdict in ("STRONG BUY", "BUY"):
        price_target = price * (1 + target_pct)
        stop_price   = price * (1 - stop_pct)
        risk_icon    = "🎯"
    elif verdict in ("STRONG SELL", "SELL / EXIT"):
        price_target = price * (1 - target_pct)
        stop_price   = price * (1 + stop_pct)
        risk_icon    = "🛑"
    else:
        price_target = None
        stop_price   = None
        risk_icon    = ""

    # ── ETA for next signal crossing ─────────────────────────────────────
    if nb and nt:
        eta_col  = RH_GREEN if nt == "BUY" else RH_RED
        eta_html = (f'<span style="color:{eta_col};font-weight:700;">'
                    f'{nt} signal expected in ~{nb} min</span>')
    else:
        eta_html = f'<span style="color:{RH_SUBTEXT};">No imminent signal crossing</span>'

    # ── Confidence bar ────────────────────────────────────────────────────
    conf_pct = int(conf * 100)
    bar_col  = RH_GREEN if conf > 0.65 else (RH_GOLD if conf > 0.40 else RH_RED)

    # ── Horizon table ─────────────────────────────────────────────────────
    rows_html = "".join(
        f'<tr>'
        f'<td style="color:{RH_SUBTEXT};padding:2px 8px 2px 0;font-size:0.78rem;">+{h} min</td>'
        f'<td style="font-weight:700;padding:2px 4px;font-size:0.78rem;">{p:.2f}</td>'
        f'<td style="color:{"#00C805" if "BUY" in s else ("#FF5000" if "SELL" in s else RH_SUBTEXT)};'
        f'font-size:0.78rem;padding:2px 0;">{s}</td>'
        f'</tr>'
        for h, p, s in zip(fc["horizons"], fc["proba_forecast"], fc["signal_forecast"])
    )

    # ── Price target block ────────────────────────────────────────────────
    if price_target is not None:
        tgt_col  = RH_GREEN if verdict in ("STRONG BUY","BUY") else RH_RED
        stop_col = RH_RED   if verdict in ("STRONG BUY","BUY") else RH_GREEN
        price_block = (f'<div style="margin-top:10px;display:flex;gap:16px;">'
                       f'<div><div style="font-size:0.62rem;color:{RH_SUBTEXT};text-transform:uppercase;">Target</div>'
                       f'<div style="font-weight:700;color:{tgt_col};">{_fmt_dollar(price_target)}</div></div>'
                       f'<div><div style="font-size:0.62rem;color:{RH_SUBTEXT};text-transform:uppercase;">Stop</div>'
                       f'<div style="font-weight:700;color:{stop_col};">{_fmt_dollar(stop_price)}</div></div>'
                       f'<div><div style="font-size:0.62rem;color:{RH_SUBTEXT};text-transform:uppercase;">R:R</div>'
                       f'<div style="font-weight:700;color:{RH_TEXT};">1 : {target_pct/stop_pct:.1f}</div></div>'
                       f'</div>')
    else:
        price_block = ""

    border_col = verdict_col
    st.markdown(
        f'<div style="background:{RH_CARD};border:2px solid {border_col}33;'
        f'border-radius:12px;padding:16px;">'
        # Verdict headline
        f'<div style="font-size:0.62rem;color:{RH_SUBTEXT};text-transform:uppercase;letter-spacing:.08em;">Model Verdict</div>'
        f'<div style="font-size:1.55rem;font-weight:800;color:{verdict_col};'
        f'letter-spacing:-0.5px;margin:2px 0 6px;">'
        f'{verdict_icon}&nbsp;{verdict}</div>'
        # Action explanation
        f'<div style="font-size:0.8rem;color:{RH_SUBTEXT};line-height:1.45;margin-bottom:10px;">{action_text}</div>'
        # ETA
        f'<div style="font-size:0.8rem;margin-bottom:8px;">{eta_html}</div>'
        # Price levels
        f'{price_block}'
        # Horizon table
        f'<div style="margin-top:10px;">'
        f'<table style="width:100%;border-collapse:collapse;">{rows_html}</table>'
        f'</div>'
        # Confidence bar
        f'<div style="margin-top:10px;background:#222;border-radius:4px;height:5px;">'
        f'<div style="background:{bar_col};height:100%;border-radius:4px;width:{conf_pct}%;"></div>'
        f'</div>'
        f'<div style="font-size:0.65rem;color:{RH_SUBTEXT};margin-top:3px;">'
        f'Forecast confidence&nbsp;{conf_pct}% &nbsp;·&nbsp; Position: <b style="color:{RH_TEXT};">{pos}</b>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def buzz_card(latest: dict, current_price: float) -> None:
    """
    Signal buzz card.  All HTML is built as a single flat string — no
    multi-line variable interpolation — so Streamlit's Markdown parser
    cannot break it into paragraphs and render it as raw text.
    """
    sig  = latest["direction"]
    conf = latest["confidence"]
    reason = latest["reason"]
    pnl  = latest["pnl_pct"]
    entry = latest["entry_price"]
    pos  = latest["position"]

    cls     = {"BUY": "buzz-buy", "SELL": "buzz-sell", "HOLD": "buzz-hold"}[sig]
    col_txt = {"BUY": RH_GREEN,   "SELL": RH_RED,      "HOLD": RH_GOLD}[sig]
    icon    = {"BUY": "&#9650; BUY", "SELL": "&#9660; SELL", "HOLD": "&#9670; HOLD"}[sig]
    fill_col = {"BUY": RH_GREEN, "SELL": RH_RED, "HOLD": RH_GOLD}[sig]
    conf_pct = int(conf * 100)

    # Build optional blocks as single-line strings (no leading newlines)
    pnl_block = ""
    if pnl is not None:
        pnl_col = RH_GREEN if pnl >= 0 else RH_RED
        pnl_block = (f'<div style="margin-top:10px;">'
                     f'<div style="font-size:0.68rem;color:{RH_SUBTEXT};text-transform:uppercase;letter-spacing:.08em;">Open P&amp;L</div>'
                     f'<div style="font-size:1.4rem;font-weight:700;color:{pnl_col};">{_fmt_pct(pnl * 100)}</div>'
                     f'</div>')

    entry_block = ""
    if entry:
        chg = (current_price / entry - 1) * 100
        chg_col = RH_GREEN if chg >= 0 else RH_RED
        entry_block = (f'<div style="margin-top:6px;font-size:0.82rem;color:{RH_SUBTEXT};">'
                       f'Entry <b style="color:{RH_TEXT};">{_fmt_dollar(entry)}</b>'
                       f' &rarr; Now <b style="color:{RH_TEXT};">{_fmt_dollar(current_price)}</b>'
                       f' <span style="color:{chg_col};">({_fmt_pct(chg)})</span>'
                       f'</div>')

    html = (f'<div class="{cls}">'
            f'<div class="buzz-label" style="color:{col_txt};">{icon}</div>'
            f'<div style="font-size:0.78rem;color:{RH_SUBTEXT};margin-top:4px;">{reason}</div>'
            f'<div style="background:#222;border-radius:4px;height:6px;overflow:hidden;margin-top:12px;">'
            f'<div style="background:{fill_col};height:100%;border-radius:4px;width:{conf_pct}%;"></div>'
            f'</div>'
            f'<div style="font-size:0.72rem;color:{RH_SUBTEXT};margin-top:3px;">'
            f'Confidence {conf_pct}% &nbsp;&middot;&nbsp; Position: <b style="color:{RH_TEXT};">{pos}</b>'
            f'</div>'
            f'{pnl_block}'
            f'{entry_block}'
            f'</div>')

    st.markdown(html, unsafe_allow_html=True)


def price_card(df: pd.DataFrame, ticker: str) -> None:
    last  = df["close"].iloc[-1]
    first = df["close"].iloc[0]
    chg   = last - first
    chg_p = (chg / first) * 100
    col   = _color(chg)
    lo    = df["low"].min() if "low" in df.columns else df["close"].min()
    hi    = df["high"].max() if "high" in df.columns else df["close"].max()

    st.markdown(f"""
    <div class="rh-card">
      <div class="rh-label">{ticker} · 1-MIN BARS</div>
      <div class="rh-price">{_fmt_dollar(last)}</div>
      <div style="color:{col};font-size:1rem;font-weight:600;margin-top:2px;">
        {'+' if chg>=0 else ''}{_fmt_dollar(chg)}
        &nbsp;({_fmt_pct(chg_p)})
      </div>
      <div style="margin-top:10px;display:flex;gap:24px;">
        <div>
          <div class="rh-label">Day Low</div>
          <div style="font-weight:600;">{_fmt_dollar(lo)}</div>
        </div>
        <div>
          <div class="rh-label">Day High</div>
          <div style="font-weight:600;">{_fmt_dollar(hi)}</div>
        </div>
        <div>
          <div class="rh-label">Bars</div>
          <div style="font-weight:600;">{len(df):,}</div>
        </div>
        <div>
          <div class="rh-label">Period</div>
          <div style="font-weight:600;">{df.index[0].strftime('%b %d')} – {df.index[-1].strftime('%b %d')}</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)


def portfolio_card(pnl_df: pd.DataFrame, initial: float = 10_000.0) -> None:
    current = pnl_df["equity"].iloc[-1]
    chg     = current - initial
    chg_p   = (chg / initial) * 100
    mdd     = (pnl_df["drawdown"].min()) * 100
    col     = _color(chg)

    st.markdown(f"""
    <div class="rh-card">
      <div class="rh-label">Portfolio Value</div>
      <div class="rh-price">{_fmt_dollar(current)}</div>
      <div style="color:{col};font-size:1rem;font-weight:600;margin-top:2px;">
        {'+' if chg>=0 else ''}{_fmt_dollar(chg)}
        &nbsp;({_fmt_pct(chg_p)})
      </div>
      <div style="margin-top:10px;display:flex;gap:20px;">
        <div>
          <div class="rh-label">Invested</div>
          <div style="font-weight:600;">{_fmt_dollar(initial)}</div>
        </div>
        <div>
          <div class="rh-label">Total Return</div>
          <div style="font-weight:600;color:{col};">{_fmt_pct(chg_p)}</div>
        </div>
        <div>
          <div class="rh-label">Max Drawdown</div>
          <div style="font-weight:600;color:{RH_RED};">{_fmt_pct(mdd)}</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:

    # ── Sidebar ───────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown(
            f"<div style='font-size:1.3rem;font-weight:800;letter-spacing:0.04em;"
            f"color:{RH_GREEN};'>📡 MarketScintillation</div>"
            f"<div style='font-size:0.7rem;color:{RH_SUBTEXT};margin-bottom:8px;'>"
            f"GNSS scintillation · ML regime detection · live signals</div>",
            unsafe_allow_html=True,
        )

        preset_key = st.selectbox("Ticker preset", list(_PRESETS.keys()), index=1)
        p = _PRESETS[preset_key]

        use_synthetic = st.checkbox("Synthetic data (no API)", value=p["use_synthetic"])
        ticker  = st.text_input("Ticker", value=p["ticker"], disabled=use_synthetic)
        period  = st.selectbox("Period", ["5d","7d","14d","1mo"], index=1,
                               disabled=use_synthetic)

        st.divider()
        st.markdown(f"<span style='font-size:0.7rem;color:{RH_SUBTEXT};text-transform:uppercase;letter-spacing:0.08em;'>Feature Windows</span>", unsafe_allow_html=True)
        dw = p["windows"]
        w5   = st.checkbox("5",   value=5   in dw)
        w15  = st.checkbox("15",  value=15  in dw)
        w30  = st.checkbox("30",  value=30  in dw)
        w60  = st.checkbox("60",  value=60  in dw)
        w300 = st.checkbox("300", value=300 in dw)
        windows = [w for w,c in [(5,w5),(15,w15),(30,w30),(60,w60),(300,w300)] if c] or [30]
        detrend_w = st.slider("Detrend window", 5, 120, p["detrend_window"])

        st.divider()
        st.markdown(f"<span style='font-size:0.7rem;color:{RH_SUBTEXT};text-transform:uppercase;letter-spacing:0.08em;'>Labeling</span>", unsafe_allow_html=True)
        label_method = st.selectbox("Method", ["future_vol","sharp_move","combined"],
            index=["future_vol","sharp_move","combined"].index(p["label_method"]))
        future_w  = st.slider("Future window (bars)", 5, 120, p["future_window"])
        turb_q    = st.slider("Turbulence quantile", 0.50, 0.95,
                              float(p["turbulence_quantile"]), step=0.01)

        st.divider()
        st.markdown(f"<span style='font-size:0.7rem;color:{RH_SUBTEXT};text-transform:uppercase;letter-spacing:0.08em;'>Signal Engine</span>", unsafe_allow_html=True)
        entry_thr  = st.slider("Entry threshold (P<x → BUY zone)", 0.20, 0.60,
                               float(p["entry_threshold"]), step=0.01)
        exit_thr   = st.slider("Exit threshold  (P>x → SELL zone)", 0.40, 0.80,
                               float(p["exit_threshold"]), step=0.01)
        mom_w      = st.slider("Momentum window (bars)", 2, 30, p["momentum_window"])
        sl_pct     = st.slider("Stop-loss %", 0.5, 5.0,
                               float(p["stop_loss_pct"] * 100), step=0.5) / 100
        pt_pct     = st.slider("Profit target %", 0.0, 10.0,
                               float(p["profit_target_pct"] * 100), step=0.5) / 100
        allow_short = st.checkbox("Allow short trades", value=p["allow_short"])

        st.divider()
        st.markdown(f"<span style='font-size:0.7rem;color:{RH_SUBTEXT};text-transform:uppercase;letter-spacing:0.08em;'>Live Mode</span>", unsafe_allow_html=True)
        live_mode    = st.toggle("Auto-refresh (30 s)", value=False)
        refresh_secs = st.slider("Refresh interval (s)", 15, 120, 30, disabled=not live_mode)

    # ── Live refresh loop ──────────────────────────────────────────────────
    if live_mode and not use_synthetic:
        time.sleep(refresh_secs)
        st.rerun()

    # ── Load data ──────────────────────────────────────────────────────────
    display_ticker = "SYNTHETIC" if use_synthetic else ticker
    with st.spinner(f"Loading {display_ticker} …"):
        df = load_data(display_ticker, period, use_synthetic)

    # ── Overlay live bar on top of historical training data ────────────────
    live_df = pd.DataFrame()
    if not use_synthetic:
        live_df = load_live_bar(display_ticker, use_synthetic)
        if not live_df.empty:
            # Append any bars newer than the training window
            new_bars = live_df[~live_df.index.isin(df.index)]
            if not new_bars.empty:
                df = pd.concat([df, new_bars]).sort_index()
                df = df[~df.index.duplicated(keep="last")]

    if df.empty:
        st.error("No data loaded.")
        return

    df_json = df.to_json(orient="split", date_format="iso")

    # ── Run pipeline ───────────────────────────────────────────────────────
    with st.spinner("Running scintillation pipeline + ML classifier …"):
        out = run_pipeline(
            df_json=df_json,
            windows=windows, detrend_window=detrend_w,
            label_method=label_method, future_window=future_w, quantile=turb_q,
            entry_threshold=entry_thr, exit_threshold=exit_thr,
            momentum_window=mom_w, stop_loss_pct=sl_pct,
            profit_target_pct=pt_pct, allow_short=allow_short,
        )

    # Deserialise
    proba_s   = _rj(out["proba"],    "series")
    regime_s  = _rj(out["regime"],  "series")
    signals_d = _rj(out["signals_json"])
    pnl_d     = _rj(out["pnl_json"])
    base_eq   = _rj(out["bt_baseline"], "series")
    filt_eq   = _rj(out["bt_filtered"], "series")
    imp       = pd.read_json(io.StringIO(out["importance"]), orient="split", typ="series")
    latest    = out["latest"]
    tm        = out["test_metrics"]
    bm        = out["bt_metrics"].get("baseline", {})
    fm        = out["bt_metrics"].get("filtered", {})

    trade_log_raw = out["trade_log"]
    trade_log = (pd.read_json(io.StringIO(trade_log_raw), orient="split")
                 if trade_log_raw != "{}" else pd.DataFrame())

    current_price = float(df["close"].iloc[-1])
    n_buys  = int((signals_d["signal"] ==  1).sum())
    n_sells = int((signals_d["signal"] == -1).sum())

    # ── Header ────────────────────────────────────────────────────────────
    st.markdown(
        f"<div style='font-size:1.8rem;font-weight:800;letter-spacing:-0.5px;"
        f"margin-bottom:0;'>{display_ticker}</div>"
        f"<div style='font-size:0.72rem;color:{RH_SUBTEXT};margin-bottom:4px;'>"
        f"MarketScintillation · Ionospheric signal detection → HF trading</div>",
        unsafe_allow_html=True,
    )

    # ── Top row: price card + signal buzz ─────────────────────────────────
    col_price, col_buzz = st.columns([1.6, 1])
    with col_price:
        price_card(df, display_ticker)
    with col_buzz:
        buzz_card(latest, current_price)

    st.divider()

    # ── KPI strip ─────────────────────────────────────────────────────────
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("Model AUC",    f"{tm.get('roc_auc',0):.3f}")
    k2.metric("Model F1",     f"{tm.get('f1',0):.3f}")
    k3.metric("Turbulent %",  f"{out['turb_rate']:.1f}%")
    k4.metric("BUY signals",  str(n_buys))
    k5.metric("SELL signals", str(n_sells))

    pnl_pct = (pnl_d["equity"].iloc[-1] / 10_000 - 1) * 100
    k6.metric(
        "Signal P&L",
        f"{_fmt_pct(pnl_pct)}",
        delta=f"vs baseline {_fmt_pct(bm.get('total_return_pct',0))}",
    )

    # Last-updated timestamp
    last_bar_ts = df.index[-1]
    now_utc     = datetime.now(timezone.utc)
    lag_secs    = int((now_utc - last_bar_ts).total_seconds())
    lag_str     = f"{lag_secs}s ago" if lag_secs < 120 else f"{lag_secs//60}m ago"
    live_badge  = (f'<span style="color:{RH_GREEN};font-weight:700;">● LIVE</span>'
                   if live_mode and not use_synthetic else
                   f'<span style="color:{RH_SUBTEXT};">○ STATIC</span>')
    st.markdown(
        f'<div style="font-size:0.7rem;color:{RH_SUBTEXT};text-align:right;margin-bottom:6px;">'
        f'{live_badge} &nbsp; Last bar: <b style="color:{RH_TEXT};">'
        f'{last_bar_ts.strftime("%H:%M:%S UTC")}</b> &nbsp;({lag_str})'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.divider()

    # ── Price chart ───────────────────────────────────────────────────────
    st.markdown(f"<div style='font-size:0.72rem;color:{RH_SUBTEXT};text-transform:uppercase;letter-spacing:0.08em;margin-bottom:4px;'>PRICE CHART · REGIME OVERLAY · BUY/SELL SIGNALS</div>", unsafe_allow_html=True)
    st.plotly_chart(chart_price(df, signals_d, regime_s, display_ticker),
                    use_container_width=True)

    # ── Turbulence index ──────────────────────────────────────────────────
    st.markdown(f"<div style='font-size:0.72rem;color:{RH_SUBTEXT};text-transform:uppercase;letter-spacing:0.08em;margin-bottom:4px;'>SCINTILLATION TURBULENCE INDEX · ML PROBABILITY</div>", unsafe_allow_html=True)
    st.plotly_chart(chart_turbulence(proba_s, entry_thr, exit_thr),
                    use_container_width=True)

    # ── Forward prediction panel ──────────────────────────────────────────
    fc = out["forecast"]
    st.markdown(
        f"<div style='font-size:0.72rem;color:{RH_SUBTEXT};text-transform:uppercase;"
        f"letter-spacing:0.08em;margin-bottom:4px;'>"
        f"FORWARD PREDICTION · AR-1 REGIME FORECAST</div>",
        unsafe_allow_html=True,
    )

    pred_cols = st.columns([2, 1])
    with pred_cols[0]:
        st.plotly_chart(chart_forecast(proba_s, fc, entry_thr, exit_thr),
                        use_container_width=True)

    with pred_cols[1]:
        _render_prediction_card(fc, current_price, entry_thr, exit_thr, latest)

    st.divider()

    # ── Portfolio + Feature importance ────────────────────────────────────
    col_port, col_imp = st.columns([1.4, 1])

    with col_port:
        st.markdown(f"<div style='font-size:0.72rem;color:{RH_SUBTEXT};text-transform:uppercase;letter-spacing:0.08em;margin-bottom:4px;'>PORTFOLIO · SIGNAL ENGINE vs BASELINE</div>", unsafe_allow_html=True)
        portfolio_card(pnl_d)
        st.plotly_chart(chart_equity(pnl_d["equity"], base_eq, filt_eq, regime_s),
                        use_container_width=True)

    with col_imp:
        st.markdown(f"<div style='font-size:0.72rem;color:{RH_SUBTEXT};text-transform:uppercase;letter-spacing:0.08em;margin-bottom:4px;'>SCINTILLATION FEATURE IMPORTANCE <span style='color:{RH_GREEN};'>■</span> GNSS-derived <span style='color:{RH_GOLD};'>■</span> Statistical</div>", unsafe_allow_html=True)
        top_n = st.slider("Top features", 8, 30, 15, key="imp_n")
        st.plotly_chart(chart_importance(imp, top_n=top_n), use_container_width=True)

    st.divider()

    # ── Trade log ─────────────────────────────────────────────────────────
    st.markdown(f"<div style='font-size:0.72rem;color:{RH_SUBTEXT};text-transform:uppercase;letter-spacing:0.08em;margin-bottom:6px;'>TRADE LOG</div>", unsafe_allow_html=True)

    if trade_log.empty:
        st.info("No completed round-trips in this window. Adjust thresholds or widen the period.")
    else:
        display_cols = [c for c in trade_log.columns if not c.startswith("_")]

        def _style_row(row):
            raw = trade_log.at[row.name, "_pnl_raw"] if "_pnl_raw" in trade_log.columns else 0
            color = "rgba(0,200,5,0.08)" if raw >= 0 else "rgba(255,80,0,0.08)"
            return [f"background-color:{color}"] * len(row)

        st.dataframe(
            trade_log[display_cols].style.apply(_style_row, axis=1),
            use_container_width=True,
            height=min(400, 36 + 36 * len(trade_log)),
        )

        wins    = int((trade_log["_pnl_raw"] > 0).sum()) if "_pnl_raw" in trade_log.columns else 0
        losses  = len(trade_log) - wins
        avg_win = trade_log[trade_log["_pnl_raw"] > 0]["_pnl_raw"].mean() if wins else 0
        avg_los = trade_log[trade_log["_pnl_raw"] <= 0]["_pnl_raw"].mean() if losses else 0

        tw1, tw2, tw3, tw4 = st.columns(4)
        tw1.metric("Trades",    str(len(trade_log)))
        tw2.metric("Win rate",  f"{wins/max(len(trade_log),1):.0%}")
        tw3.metric("Avg win",   f"{avg_win:+.2f}%", delta=None)
        tw4.metric("Avg loss",  f"{avg_los:+.2f}%", delta=None)

    # ── Strategy comparison ───────────────────────────────────────────────
    with st.expander("Strategy comparison table"):
        rows = []
        for lbl, m in [("Baseline (full momentum)", bm), ("ML-Filtered momentum", fm)]:
            rows.append({
                "Strategy":        lbl,
                "Total Return":    _fmt_pct(m.get("total_return_pct",0)),
                "Sharpe":          f"{m.get('sharpe',0):.3f}",
                "Sortino":         f"{m.get('sortino',0):.3f}",
                "Max Drawdown":    _fmt_pct(m.get("max_drawdown_pct",0)),
                "Calmar":          f"{m.get('calmar',0):.3f}",
                "Ann Vol":         _fmt_pct(m.get("ann_vol_pct",0)),
                "# Trades":        f"{m.get('n_trades',0):,}",
                "Win Rate":        _fmt_pct(m.get("win_rate_pct",0)),
            })
        st.dataframe(pd.DataFrame(rows).set_index("Strategy"), use_container_width=True)

    with st.expander("Cross-validation detail"):
        cv = out["cv_scores"]
        st.dataframe(
            pd.DataFrame({"Fold": range(1, len(cv["auc"])+1),
                          "AUC": cv["auc"], "F1": cv["f1"]}).set_index("Fold")
            .style.format("{:.4f}"),
            use_container_width=True,
        )
        st.metric("Mean AUC", f"{np.mean(cv['auc']):.4f} ± {np.std(cv['auc']):.4f}")
        st.metric("Mean F1",  f"{np.mean(cv['f1']):.4f} ± {np.std(cv['f1']):.4f}")

    # ── Footer ────────────────────────────────────────────────────────────
    st.markdown(
        f"<div style='margin-top:24px;font-size:0.68rem;color:{RH_SUBTEXT};text-align:center;'>"
        f"MarketScintillation · S4 · σφ · PSD slope · Deterministic index · Reflective index"
        f" · adapted from GNSS ionospheric scintillation detection (GPS Solutions)</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()

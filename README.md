# 📡 MarketScintillation

> **Detecting market turbulence with ionospheric scintillation techniques**

A portfolio-grade quantitative research tool that adapts signal-processing
methods from a *GPS Solutions* paper on ionospheric scintillation detection
to identify turbulent market regimes in high-frequency financial data,
then uses an XGBoost / LightGBM classifier on top of the derived features
to produce a real-time turbulence probability score.

---

## Conceptual Bridge: GNSS → Markets

| GNSS Scintillation Concept | Financial Analog |
|---|---|
| Signal intensity `I(t)` | `|return(t)|` — magnitude of price move |
| Carrier phase `φ(t)` | Cumulative log-return (price "phase") |
| Ionospheric scintillation | Market turbulence / microstructure noise |
| **S4 index** `σ(I)/μ(I)` | **S4_mkt** — normalized volatility-of-volatility |
| **σφ index** | **σφ_mkt** — detrended phase volatility |
| Adaptive detrending filter | Rolling MA subtraction / high-pass Butterworth |
| Power-law PSD slope `p` | PSD slope of returns (flat = turbulent) |
| Spectral entropy | Frequency-domain disorder measure |
| Deterministic index | 1 − `|AC₁|` — unpredictability index |
| Reflective index | −AC₁ — bid-ask bounce / mean-reversion measure |
| High-frequency T-index | HF power ratio in Welch PSD |

---

## Project Structure

```
market_scintillation/
├── config.py              # All hyperparameters & API keys
├── requirements.txt
├── README.md
│
├── data/
│   └── loader.py          # Polygon.io + yfinance + synthetic data generator
│
├── features/
│   └── extractor.py       # ScintillationFeatureExtractor + labeling
│
├── models/
│   └── classifier.py      # TurbulenceClassifier (XGBoost / LightGBM)
│
├── backtester/
│   └── engine.py          # Regime-aware vectorised backtester
│
├── app/
│   └── dashboard.py       # Streamlit interactive dashboard
│
└── utils/
    └── helpers.py         # Shared DSP and finance utilities
```

---

## Quickstart

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. (Optional) Set your Polygon.io API key

```bash
export POLYGON_API_KEY="your_key_here"
```
Or edit `config.py`. Without a key the tool uses **yfinance** (minute bars)
or the built-in **synthetic data generator** (second bars, no API needed).

### 3. Launch the dashboard

```bash
streamlit run app/dashboard.py
```

The default launches with **synthetic demo data** (no API key required).
Toggle "Use synthetic demo data" off in the sidebar to use real market data.

---

## Feature Engineering Details

### S4-like Amplitude Scintillation Index

```
I(t)   = |r(t)|                    # signal "intensity"
S4(w)  = sqrt( [<I²> - <I>²] / <I>² )
```

Computed over rolling windows `w ∈ {10, 30, 60, 300}` seconds.
Also computed on high-pass-filtered intensity (`s4_hp`) to isolate
the fluctuation component only.

### σφ-like Phase Scintillation

```
φ(t)          = cumsum(r(t))       # cumulative return = "phase"
φ_det(t)      = φ(t) - MA(φ, w)   # detrend with rolling mean
σφ(w)         = rolling_std(φ_det, w)
```

### Detrending

- Rolling MA subtraction (`rolling_detrend`) applied to both the close
  price (log-scale) and cumulative return.
- Zero-phase Butterworth high-pass filter (`high_pass_filter`) at
  cut-off 5–10% of Nyquist to isolate the scintillation component.

### Power Spectral Density features

Computed via Welch's method on rolling windows:

| Feature | Description |
|---|---|
| `psd_slope` | Power-law slope p of S(f) ~ f^-p (flat → turbulent) |
| `psd_entropy` | Normalised spectral entropy (high → broad-band noise) |
| `psd_hf_ratio` | Fraction of power in upper half of spectrum |

### Deterministic Index (DI)

```
DI = 1 - |AC₁(r, w)|
```
High DI → low autocorrelation → unpredictable (turbulent).

### Reflective Index (RI)

```
RI = -AC₁(r, w)
```
Positive RI → serial anti-correlation → bid-ask bounce microstructure noise.

### Volume-weighted Scintillation

```
vol_ratio = volume / rolling_mean(volume, w)   # volume spike indicator
av_scint  = S4 × vol_ratio                     # combined signal
```

### Cross-window Ratios

For each feature `f` and consecutive scale pair `(w_fast, w_slow)`:
```
f_ratio = f(w_fast) / f(w_slow)   # acute burst vs background
f_diff  = f(w_fast) - f(w_slow)   # regime change velocity
```

Total feature count: **~80–100 features** across 4 window sizes.

---

## ML Classifier

- **Algorithm**: XGBoost (default) or LightGBM
- **Validation**: `TimeSeriesSplit` (5 folds, no shuffling, no leakage)
- **Class balancing**: `scale_pos_weight = n_quiet / n_turbulent`
- **Threshold tuning**: F1-maximising threshold on OOF predictions
- **Explainability**: SHAP TreeExplainer (or native gain importance)

### Labeling strategy

**`future_vol` (default)**:
```
fut_vol(t) = rolling_std(r, future_window) shifted -future_window bars
label(t)   = 1  if fut_vol(t) > quantile(fut_vol, 0.75)
```
This labels a bar as turbulent if the *next* N bars will be highly volatile —
exactly what a risk-aware trader needs to know in advance.

**`sharp_move`**:
```
label(t)   = 1  if |r(t)| > z_thresh × rolling_std(r, 60)
```

**`combined`**: OR of both above.

---

## Backtesting

### Strategies

**Momentum**: long if `sum(r, signal_window) > 0`, short otherwise.
**Mean-reversion**: inverse of momentum signal.

### Regime filter

| Regime | Position size |
|---|---|
| Quiet  (label=0) | `position_size` (default 1.0 = full) |
| Turbulent (label=1) | `turbulent_size` (default 0.0 = flat) |

### Metrics

Sharpe, Sortino, Max Drawdown, Calmar, Win Rate, Annualized Vol.
All computed on net-of-transaction-cost returns (0.5 bps round-trip default).

---

## Dashboard Controls

| Control | Effect |
|---|---|
| Ticker / date range | Market data selection |
| Feature windows | Toggle 10/30/60/300 bar scales |
| Detrend window | MA window for phase detrending |
| Label method | Regime labeling approach |
| Regime threshold | ML probability cut-off (0–1) |
| Position size (turbulent) | Risk reduction in turbulent regime |
| Top N features | Feature importance chart depth |

---

## Interpretation of Results

A well-calibrated classifier should show:
- **Higher Sharpe** in the filtered strategy (risk-adjusted return improves
  because we avoid the worst volatility bursts).
- **Smaller max drawdown** (regime filter prevents holding positions into
  sharp adverse moves).
- **Lower annualized vol** (position reduction during turbulence dampens
  the equity curve noise).
- **Feature importance**: S4, σφ, PSD slope, and HF power ratio are
  expected to rank highly — exactly as they do in GNSS scintillation studies.

---

## Citation / Methodology Note

The scintillation indices (S4, σφ, spectral slope, T-index) are adapted
from peer-reviewed GNSS ionospheric research. The key insight is that
both ionospheric plasma irregularities and financial market microstructure
noise produce **amplitude and phase fluctuations** on an underlying carrier
signal, making the same class of statistical signal-processing tools applicable
in both domains.

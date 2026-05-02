"""
ML Turbulence Classifier
========================
XGBoost / LightGBM classifier trained on scintillation-derived features.

Key design choices
------------------
* TimeSeriesSplit cross-validation  — no look-ahead leakage.
* Class-weight balancing            — turbulent bars are rare; prevent bias.
* SHAP values                       — explain which scintillation features drive the label.
* Probability output                — continuous turbulence score, not just 0/1.
* Threshold tuning via F1           — regime threshold is a tunable hyperparameter.
"""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import (
    classification_report,
    f1_score,
    precision_recall_curve,
    roc_auc_score,
)
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler

from config import ModelConfig, MODEL_CFG
from utils.helpers import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Helper: safe import of tree-based libraries
# ---------------------------------------------------------------------------

def _get_xgb():
    try:
        from xgboost import XGBClassifier
        return XGBClassifier
    except ImportError as e:
        raise ImportError("Install xgboost: pip install xgboost") from e


def _get_lgbm():
    try:
        from lightgbm import LGBMClassifier
        return LGBMClassifier
    except ImportError as e:
        raise ImportError("Install lightgbm: pip install lightgbm") from e


def _get_shap():
    try:
        import shap
        return shap
    except ImportError:
        logger.warning("SHAP not installed. Feature importance will use native importances.")
        return None


# ---------------------------------------------------------------------------
# Main classifier class
# ---------------------------------------------------------------------------

class TurbulenceClassifier:
    """
    Regime classifier trained on scintillation features.

    Parameters
    ----------
    cfg : ModelConfig
        Model hyperparameters and cross-validation settings.

    Usage
    -----
    >>> clf = TurbulenceClassifier()
    >>> clf.fit(features_df, labels)
    >>> proba = clf.predict_proba(features_df)
    """

    def __init__(self, cfg: ModelConfig = MODEL_CFG) -> None:
        self.cfg = cfg
        self.model: Any = None
        self.scaler = StandardScaler()
        self.feature_names_: List[str] = []
        self.threshold_: float = cfg.xgb_params.get("_threshold", 0.50)
        self.cv_scores_: Dict[str, List[float]] = {}
        self.shap_values_: Optional[np.ndarray] = None
        self._is_fitted = False

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def fit(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        optimize_threshold: bool = True,
    ) -> "TurbulenceClassifier":
        """
        Fit the classifier with time-series cross-validation.

        Parameters
        ----------
        X : feature DataFrame (output of ScintillationFeatureExtractor.transform)
        y : binary label Series (0=quiet, 1=turbulent)
        optimize_threshold : tune the classification threshold on CV predictions.
        """
        # ------ Clean: drop rows where label or any feature is NaN ------
        mask = y.notna() & X.notna().all(axis=1)
        X_clean = X[mask].copy()
        y_clean = y[mask].copy()
        logger.info("Training on %d samples (%d turbulent)", len(y_clean), y_clean.sum())

        self.feature_names_ = list(X_clean.columns)

        # ------ Scale features (helps some tree algorithms) ------
        X_scaled = self.scaler.fit_transform(X_clean)
        X_scaled = pd.DataFrame(X_scaled, columns=self.feature_names_, index=X_clean.index)

        # ------ Class weights ------
        pos_weight = float((y_clean == 0).sum() / max((y_clean == 1).sum(), 1))

        # ------ Build model ------
        self.model = self._build_model(pos_weight)

        # ------ Time-series cross-validation ------
        tscv = TimeSeriesSplit(n_splits=self.cfg.n_splits)
        oof_proba = np.zeros(len(y_clean))
        auc_scores, f1_scores = [], []

        X_arr = X_scaled.values
        y_arr = y_clean.values

        for fold, (train_idx, val_idx) in enumerate(tscv.split(X_arr)):
            X_tr, X_val = X_arr[train_idx], X_arr[val_idx]
            y_tr, y_val = y_arr[train_idx], y_arr[val_idx]

            self.model.fit(
                X_tr, y_tr,
                eval_set=[(X_val, y_val)],
                verbose=False,
            )

            val_proba = self.model.predict_proba(X_val)[:, 1]
            oof_proba[val_idx] = val_proba

            auc = roc_auc_score(y_val, val_proba) if y_val.sum() > 0 else 0.5
            f1 = f1_score(y_val, (val_proba >= 0.5).astype(int), zero_division=0)
            auc_scores.append(auc)
            f1_scores.append(f1)
            logger.info("  Fold %d — AUC %.4f  F1 %.4f", fold + 1, auc, f1)

        self.cv_scores_ = {"auc": auc_scores, "f1": f1_scores}
        logger.info(
            "CV mean — AUC %.4f ± %.4f   F1 %.4f ± %.4f",
            np.mean(auc_scores), np.std(auc_scores),
            np.mean(f1_scores), np.std(f1_scores),
        )

        # ------ Retrain on full data ------
        self.model.fit(X_arr, y_arr, verbose=False)

        # ------ Optimize threshold ------
        if optimize_threshold and y_clean.sum() > 0:
            self.threshold_ = self._optimize_threshold(oof_proba, y_arr)
            logger.info("Optimized classification threshold: %.3f", self.threshold_)

        self._is_fitted = True
        return self

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Return probability of turbulent regime for each row."""
        self._check_fitted()
        X_aligned = self._align_and_fill(X)
        X_scaled = self.scaler.transform(X_aligned)
        return self.model.predict_proba(X_scaled)[:, 1]

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Return binary regime label (0 quiet / 1 turbulent)."""
        proba = self.predict_proba(X)
        return (proba >= self.threshold_).astype(int)

    def predict_series(
        self,
        X: pd.DataFrame,
        index: Optional[pd.Index] = None,
    ) -> Tuple[pd.Series, pd.Series]:
        """
        Return (proba_series, label_series) aligned to the input DataFrame index.
        """
        proba = self.predict_proba(X)
        label = (proba >= self.threshold_).astype(int)
        idx = X.index if index is None else index
        return (
            pd.Series(proba, index=idx, name="turbulence_proba"),
            pd.Series(label, index=idx, name="regime_label"),
        )

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate(self, X: pd.DataFrame, y: pd.Series) -> Dict[str, Any]:
        """Compute test-set metrics."""
        self._check_fitted()
        mask = y.notna() & X.notna().all(axis=1)
        X_c, y_c = X[mask], y[mask]
        proba = self.predict_proba(X_c)
        pred = (proba >= self.threshold_).astype(int)

        auc = roc_auc_score(y_c, proba) if y_c.sum() > 0 else 0.5
        f1 = f1_score(y_c, pred, zero_division=0)
        report = classification_report(y_c, pred, output_dict=True, zero_division=0)

        metrics = {
            "roc_auc": auc,
            "f1": f1,
            "precision_turbulent": report.get("1", {}).get("precision", 0),
            "recall_turbulent": report.get("1", {}).get("recall", 0),
            "classification_report": report,
        }
        logger.info("Test AUC %.4f  F1 %.4f", auc, f1)
        return metrics

    # ------------------------------------------------------------------
    # Feature importance
    # ------------------------------------------------------------------

    def feature_importance(
        self,
        X: Optional[pd.DataFrame] = None,
        use_shap: bool = True,
    ) -> pd.Series:
        """
        Return feature importance (SHAP values or native gain importance).

        Parameters
        ----------
        X : sample data for SHAP TreeExplainer (optional if use_shap=False).
        use_shap : prefer SHAP-based importance when available.
        """
        self._check_fitted()

        if use_shap and X is not None:
            shap = _get_shap()
            if shap is not None:
                try:
                    X_aligned = self._align_and_fill(X)
                    X_scaled = self.scaler.transform(X_aligned)
                    explainer = shap.TreeExplainer(self.model)
                    sample = X_scaled[: min(2000, len(X_scaled))]
                    shap_vals = explainer.shap_values(sample)
                    if isinstance(shap_vals, list):
                        shap_vals = shap_vals[1]  # class 1 (turbulent)
                    self.shap_values_ = shap_vals
                    importance = pd.Series(
                        np.abs(shap_vals).mean(axis=0),
                        index=self.feature_names_,
                    ).sort_values(ascending=False)
                    return importance
                except Exception as exc:
                    logger.warning("SHAP failed (%s), falling back to gain.", exc)

        # Native gain importance
        try:
            imp = self.model.feature_importances_
            return pd.Series(imp, index=self.feature_names_).sort_values(ascending=False)
        except AttributeError:
            return pd.Series(dtype=float)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: str) -> None:
        """Pickle the classifier to disk."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self, f)
        logger.info("Classifier saved to %s", path)

    @classmethod
    def load(cls, path: str) -> "TurbulenceClassifier":
        """Load a pickled classifier from disk."""
        with open(path, "rb") as f:
            clf = pickle.load(f)
        logger.info("Classifier loaded from %s", path)
        return clf

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_model(self, pos_weight: float) -> Any:
        if self.cfg.model_type == "xgboost":
            XGBClassifier = _get_xgb()
            params = dict(self.cfg.xgb_params)
            params.pop("_threshold", None)
            params["scale_pos_weight"] = pos_weight
            return XGBClassifier(**params)
        elif self.cfg.model_type == "lightgbm":
            LGBMClassifier = _get_lgbm()
            params = dict(self.cfg.lgbm_params)
            params["class_weight"] = {0: 1.0, 1: pos_weight}
            return LGBMClassifier(**params)
        else:
            raise ValueError(f"Unknown model_type: {self.cfg.model_type}")

    @staticmethod
    def _optimize_threshold(proba: np.ndarray, y_true: np.ndarray) -> float:
        """Find threshold maximizing F1 on OOF predictions."""
        precision, recall, thresholds = precision_recall_curve(y_true, proba)
        f1 = 2 * precision * recall / (precision + recall + 1e-12)
        best_idx = np.argmax(f1[:-1])
        return float(thresholds[best_idx])

    def _align_and_fill(self, X: pd.DataFrame) -> pd.DataFrame:
        """Align feature columns to training schema; fill missing with 0."""
        X_aligned = X.reindex(columns=self.feature_names_, fill_value=0.0)
        X_aligned = X_aligned.fillna(0.0)
        return X_aligned

    def _check_fitted(self) -> None:
        if not self._is_fitted:
            raise RuntimeError("Classifier is not fitted yet. Call fit() first.")


# ---------------------------------------------------------------------------
# Convenience: end-to-end train/test split respecting time order
# ---------------------------------------------------------------------------

def train_test_split_ts(
    X: pd.DataFrame,
    y: pd.Series,
    test_frac: float = 0.20,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """Time-ordered train/test split (no shuffling)."""
    n = len(X)
    split = int(n * (1 - test_frac))
    return X.iloc[:split], X.iloc[split:], y.iloc[:split], y.iloc[split:]

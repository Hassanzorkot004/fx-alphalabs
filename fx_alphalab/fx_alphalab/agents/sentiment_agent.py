"""
agents/sentiment_agent.py
────────────────────────────────────────────────────────────────────────────
Sentiment Agent — XGBoost classifier + direct lexical gate.

ARCHITECTURE v4 (5-stage pipeline):
  Stage 3 of 5. Receives macro regime context from Stage 1 (MacroAgent)
  as additional features, improving calibration in risk-off regimes.

  Model: XGBoost (replaces LogisticRegression)
    - Handles nonlinear interactions (e.g. pressure × flow_accel)
    - Better calibrated probabilities via isotonic regression
    - class_weight='balanced' equivalent via scale_pos_weight

  Features: 9 stable nws_* features + 3 macro context features
    - nws_* features: stable between training and live
    - macro context: regime_bearish, regime_bullish, mac_vix_z
    - EXCLUDED: nws_news_flow (constant=5 in training, variable live → OOD)
    - EXCLUDED: nws_flow_imbalance (duplicate of nws_sent_mom in v3)

  Per-agent LLM: produces analyst_text explaining the sentiment reading.
  Decision stays deterministic Python — LLM only explains.
"""
from __future__ import annotations

import pickle
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import pandas as pd
from loguru import logger

try:
    from xgboost import XGBClassifier
    XGB_AVAILABLE = True
except ImportError:
    XGB_AVAILABLE = False
    logger.warning("xgboost not installed — run: pip install xgboost")

from sklearn.preprocessing import RobustScaler
from sklearn.calibration import CalibratedClassifierCV


# ── Feature sets ──────────────────────────────────────────────────────────────

# Core sentiment features — stable between training proxy and live real news
NWS_FEATURES = [
    "nws_sent_signal",
    "nws_sent_mom",
    "nws_sent_fast",
    "nws_sent_slow",
    "nws_sent_pressure",
    "nws_pressure_change",
    "nws_flow_accel",
    "nws_trend_strength",
]

# Macro context features injected from Stage 1 output
# These help the sentiment model calibrate in risk-off/risk-on regimes
MACRO_CONTEXT_FEATURES = [
    "ctx_regime_bearish",   # 1 if macro regime is bearish, else 0
    "ctx_regime_bullish",   # 1 if macro regime is bullish, else 0
    "ctx_vix_z",            # VIX z-score (risk-off signal)
]

ALL_FEATURES = NWS_FEATURES + MACRO_CONTEXT_FEATURES

TARGET_MAP = {-1: 0, 0: 1, 1: 2}
LABEL_MAP  = {0: "SELL", 1: "HOLD", 2: "BUY"}

NEUTRAL_OUTPUT = {
    "direction":    0,
    "p_buy":        0.33,
    "p_hold":       0.34,
    "p_sell":       0.33,
    "confidence":   0.0,
    "uncertainty":  1.0,
    "signal":       "HOLD [LOW-NEWS]",
    "analyst_text": "Insufficient news coverage to form a sentiment view.",
}

# Lexical gate thresholds — clear signal bypasses model
BULL_THRESHOLD = 0.12
BEAR_THRESHOLD = -0.12


class SentimentAgent:

    def __init__(self, cfg: dict):
        self.model_dir = Path(cfg["paths"]["sent_model"])
        self._scaler:  Optional[RobustScaler]  = None
        self._model                            = None   # XGBClassifier or calibrated
        self._feature_cols                     = ALL_FEATURES
        self.fitted                            = False

    # ── Fit ──────────────────────────────────────────────────────────────────

    def fit(self, df: pd.DataFrame) -> "SentimentAgent":
        """
        Train XGBoost sentiment classifier.

        df must have columns: nws_* features + target (-1/0/1)
        Macro context columns are optional (zeroed if missing).
        """
        if not XGB_AVAILABLE:
            logger.error("xgboost not available — cannot train SentimentAgent")
            return self

        logger.info("SentimentAgent.fit() — XGBoost …")

        # Add macro context columns if missing (zeros = no context)
        for col in MACRO_CONTEXT_FEATURES:
            if col not in df.columns:
                df[col] = 0.0

        present = [c for c in ALL_FEATURES if c in df.columns]
        missing = [c for c in ALL_FEATURES if c not in df.columns]
        if missing:
            logger.warning(f"  Missing features (will be zeroed): {missing}")

        if "target" not in df.columns:
            raise ValueError("df must have 'target' column (-1, 0, 1)")

        valid = df["target"].isin([-1, 0, 1])
        X_raw = df.loc[valid, present].fillna(0).values.astype(np.float32)
        y_raw = df.loc[valid, "target"].values
        y     = np.array([TARGET_MAP[int(t)] for t in y_raw])

        counts = np.bincount(y, minlength=3)
        logger.info(f"  SELL={counts[0]:,}  HOLD={counts[1]:,}  BUY={counts[2]:,}")

        # Scale
        self._scaler = RobustScaler(quantile_range=(5, 95))
        X = np.clip(self._scaler.fit_transform(X_raw), -5, 5)

        # Class weights: SELL and BUY are minority classes
        # XGBoost handles imbalance via scale_pos_weight per class
        # We use sample_weight instead for multi-class
        class_counts = np.bincount(y, minlength=3)
        total        = len(y)
        sample_weight = np.array([
            total / (3 * class_counts[yi]) for yi in y
        ])

        xgb = XGBClassifier(
            n_estimators=400,
            max_depth=5,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            min_child_weight=10,
            gamma=0.1,
            reg_alpha=0.1,
            reg_lambda=1.0,
            use_label_encoder=False,
            eval_metric="mlogloss",
            random_state=42,
            n_jobs=-1,
            verbosity=0,
        )

        # Calibrate probabilities with isotonic regression
        # Use 3-fold CV to avoid overfitting calibration
        self._model = CalibratedClassifierCV(xgb, method="isotonic", cv=3)
        self._model.fit(X, y, sample_weight=sample_weight)

        # Quick train accuracy
        preds = self._model.predict(X)
        acc   = float((preds == y).mean())
        logger.success(f"SentimentAgent.fit() complete. Train acc={acc:.3f}")

        self._feature_cols = present
        self.fitted        = True
        return self

    # ── Live prediction ───────────────────────────────────────────────────────

    def predict_live(self, nws_features: Dict,
                     macro_context: Optional[Dict] = None) -> Dict:
        """
        nws_features: dict from NewsFeed.fetch()["nws_features"]
        macro_context: optional dict from MacroAgent.predict_live() output
          Expected keys: regime_label, mac_features.mac_vix_z

        Pipeline:
          Gate 1: < 2 articles → HOLD [LOW-NEWS]
          Gate 2: |lexical_score| > threshold → direct signal
          Gate 3: XGBoost calibrated probabilities
        """
        n_articles  = int(nws_features.get("nws_news_flow", 0))
        sent_signal = float(nws_features.get("nws_sent_signal", 0.0))

        # Gate 1: not enough news
        if n_articles < 2:
            return NEUTRAL_OUTPUT.copy()

        # Build macro context features
        ctx = self._build_macro_context(macro_context)

        # Gate 2: clear lexical signal — trust it directly
        if abs(sent_signal) >= BULL_THRESHOLD:
            return self._lexical_signal(sent_signal, n_articles)

        # Gate 3: XGBoost calibrated model
        if self.fitted and self._model is not None:
            return self._model_signal(nws_features, ctx)

        # Fallback: weak signal, no model
        return {
            "direction":    0,
            "p_buy":        0.33,
            "p_hold":       0.34,
            "p_sell":       0.33,
            "confidence":   0.0,
            "uncertainty":  1.0,
            "signal":       "HOLD",
            "analyst_text": "Weak sentiment signal — model unavailable.",
        }

    def _build_macro_context(self, macro_context: Optional[Dict]) -> Dict:
        """Extract macro context features for injection into sentiment model."""
        if macro_context is None:
            return {
                "ctx_regime_bearish": 0.0,
                "ctx_regime_bullish": 0.0,
                "ctx_vix_z":          0.0,
            }
        regime   = macro_context.get("regime_label", "neutral")
        mac_feat = macro_context.get("mac_features", {})
        return {
            "ctx_regime_bearish": 1.0 if regime == "bearish" else 0.0,
            "ctx_regime_bullish": 1.0 if regime == "bullish" else 0.0,
            "ctx_vix_z":          float(mac_feat.get("mac_vix_z", 0.0)),
        }

    def _lexical_signal(self, sent_signal: float, n_articles: int) -> Dict:
        """Direct lexical gate — clear signal bypasses model."""
        if sent_signal > 0:
            direction  = 1
            signal_str = "BUY"
            p_buy      = min(0.5 + sent_signal * 1.5, 0.85)
            p_sell     = max(0.15, 0.5 - sent_signal * 1.5)
            p_hold     = max(0.0, 1.0 - p_buy - p_sell)
        else:
            direction  = -1
            signal_str = "SELL"
            p_sell     = min(0.5 + abs(sent_signal) * 1.5, 0.85)
            p_buy      = max(0.15, 0.5 - abs(sent_signal) * 1.5)
            p_hold     = max(0.0, 1.0 - p_buy - p_sell)

        confidence  = float(abs(sent_signal) * min(n_articles / 10.0, 1.0))
        confidence  = round(max(confidence, 0.25), 3)
        entropy     = float(-sum(p * np.log(p + 1e-9) for p in [p_buy, p_hold, p_sell]))
        uncertainty = entropy / np.log(3)

        return {
            "direction":    direction,
            "p_buy":        round(p_buy, 3),
            "p_hold":       round(p_hold, 3),
            "p_sell":       round(p_sell, 3),
            "confidence":   confidence,
            "uncertainty":  round(uncertainty, 3),
            "signal":       signal_str,
            "analyst_text": "",   # filled by orchestrator LLM
        }

    def _model_signal(self, nws_features: Dict, ctx: Dict) -> Dict:
        """XGBoost model prediction for borderline cases."""
        feat_dict = {**nws_features, **ctx}
        x = np.array(
            [feat_dict.get(c, 0.0) for c in self._feature_cols],
            dtype=np.float32
        ).reshape(1, -1)
        x = np.clip(self._scaler.transform(x), -5, 5)

        probs  = self._model.predict_proba(x)[0]
        # CalibratedClassifierCV preserves class order [0,1,2] = [SELL,HOLD,BUY]
        p_sell = float(probs[0])
        p_hold = float(probs[1])
        p_buy  = float(probs[2])

        max_p = max(p_buy, p_sell)
        if max_p < 0.45:
            return {
                "direction":    0,
                "p_buy":        round(p_buy, 3),
                "p_hold":       round(p_hold, 3),
                "p_sell":       round(p_sell, 3),
                "confidence":   0.0,
                "uncertainty":  1.0,
                "signal":       "HOLD",
                "analyst_text": "",
            }

        direction   = 1 if p_buy > p_sell else -1
        confidence  = round(max(float(max_p - p_hold), 0.0), 3)
        entropy     = float(-np.sum(probs * np.log(probs + 1e-9)))
        uncertainty = round(entropy / np.log(3), 3)
        signal_str  = "BUY" if direction == 1 else "SELL"

        return {
            "direction":    direction,
            "p_buy":        round(p_buy, 3),
            "p_hold":       round(p_hold, 3),
            "p_sell":       round(p_sell, 3),
            "confidence":   confidence,
            "uncertainty":  uncertainty,
            "signal":       signal_str,
            "analyst_text": "",
        }

    # ── Persistence ───────────────────────────────────────────────────────────

    def save(self) -> None:
        self.model_dir.mkdir(parents=True, exist_ok=True)
        with open(self.model_dir / "sent_model.pkl", "wb") as f:
            pickle.dump({
                "model":        self._model,
                "scaler":       self._scaler,
                "fitted":       self.fitted,
                "feature_cols": self._feature_cols,
            }, f)
        logger.success(f"SentimentAgent saved → {self.model_dir}")

    def load(self) -> "SentimentAgent":
        path = self.model_dir / "sent_model.pkl"
        with open(path, "rb") as f:
            state = pickle.load(f)
        self._model        = state["model"]
        self._scaler       = state["scaler"]
        self.fitted        = state["fitted"]
        self._feature_cols = state.get("feature_cols", NWS_FEATURES)
        logger.info(f"SentimentAgent loaded from {self.model_dir}")
        return self

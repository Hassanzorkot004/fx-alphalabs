"""
agents/sentiment_agent.py
────────────────────────────────────────────────────────────────────────────
Sentiment Agent — combines direct lexical scoring with a learned calibrator.

ROOT CAUSE OF PREVIOUS BUG:
  The logistic regression was trained with nws_news_flow=5.0 (hardcoded constant).
  In live mode nws_news_flow=31 (real article count) → OUT OF DISTRIBUTION.
  The model saw an anomalous feature and misclassified mildly bullish news as SELL.

FIX:
  Primary signal = direct lexical score from news_feed (sent_signal: -1 to +1).
  The logistic regression is kept as a CALIBRATOR only, using features that are
  stable between training and live (sent_fast, sent_slow, sent_mom, sent_pressure).
  nws_news_flow is REMOVED from the feature set entirely.

  If n_articles < 2 → HOLD [LOW-NEWS] as before.
  If lexical score is clear (|score| > 0.15) → trust it directly.
  Otherwise → use calibrator for borderline cases.
"""
from __future__ import annotations

import pickle
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import pandas as pd
from loguru import logger
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import RobustScaler


# Features that are stable between training proxy and live real news
# Removed: nws_news_flow (constant=5.0 in training, variable in live)
FEATURE_COLS = [
    "nws_sent_signal",
    "nws_sent_mom",
    "nws_sent_fast",
    "nws_sent_slow",
    "nws_sent_pressure",
    "nws_pressure_change",
    "nws_flow_accel",
    "nws_flow_imbalance",
    "nws_trend_strength",
]

TARGET_MAP = {-1: 0, 0: 1, 1: 2}
LABEL_MAP  = {0: "SELL", 1: "HOLD", 2: "BUY"}

NEUTRAL_OUTPUT = {
    "direction":   0,
    "p_buy":       0.33,
    "p_hold":      0.34,
    "p_sell":      0.33,
    "confidence":  0.0,
    "uncertainty": 1.0,
    "signal":      "HOLD [LOW-NEWS]",
}

# Lexical score thresholds for direct signal
BULL_THRESHOLD = 0.12   # sent_signal > +0.12 → lean BUY
BEAR_THRESHOLD = -0.12  # sent_signal < -0.12 → lean SELL


class SentimentAgent:

    def __init__(self, cfg: dict):
        self.model_dir = Path(cfg["paths"]["sent_model"])
        self._scaler:  Optional[RobustScaler]       = None
        self._model:   Optional[LogisticRegression] = None
        self.fitted    = False

    def fit(self, df: pd.DataFrame) -> "SentimentAgent":
        logger.info("SentimentAgent.fit() starting …")

        present = [c for c in FEATURE_COLS if c in df.columns]
        if len(present) < 3:
            logger.warning(
                f"Only {len(present)} sentiment features found — "
                "SentimentAgent will output direct lexical signals in live mode."
            )
            self.fitted = False
            return self

        if "target" not in df.columns:
            raise ValueError("df must have a 'target' column (-1, 0, 1)")

        valid = df["target"].isin([-1, 0, 1])
        X_raw = df.loc[valid, present].fillna(0).values.astype(np.float32)
        y_raw = df.loc[valid, "target"].values

        self._scaler = RobustScaler(quantile_range=(5, 95))
        X = np.clip(self._scaler.fit_transform(X_raw), -5, 5)
        y = np.array([TARGET_MAP[int(t)] for t in y_raw])

        counts = np.bincount(y, minlength=3)
        logger.info(f"  SELL={counts[0]}  HOLD={counts[1]}  BUY={counts[2]}")

        self._model = LogisticRegression(
            C=0.5,
            max_iter=1000,
            class_weight="balanced",
            solver="lbfgs",
            random_state=42,
        )
        self._model.fit(X, y)
        train_acc = self._model.score(X, y)
        logger.success(f"SentimentAgent.fit() complete. Train acc={train_acc:.3f}")
        self.fitted = True
        return self

    def predict_live(self, nws_features: Dict) -> Dict:
        """
        nws_features: dict from NewsFeed.fetch()["nws_features"]

        Logic:
          1. If < 2 articles → HOLD [LOW-NEWS]
          2. If |lexical_score| > threshold → use lexical signal directly
          3. Otherwise → use calibrator for borderline cases
        """
        n_articles  = int(nws_features.get("nws_news_flow", 0))
        sent_signal = float(nws_features.get("nws_sent_signal", 0.0))

        # Gate 1: not enough news
        if n_articles < 2:
            return NEUTRAL_OUTPUT

        # Gate 2: clear lexical signal — trust it directly without the model
        if abs(sent_signal) >= BULL_THRESHOLD:
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
                "direction":   direction,
                "p_buy":       round(p_buy, 3),
                "p_hold":      round(p_hold, 3),
                "p_sell":      round(p_sell, 3),
                "confidence":  confidence,
                "uncertainty": round(uncertainty, 3),
                "signal":      signal_str,
            }

        # Gate 3: weak signal — use calibrator if available
        if self.fitted and self._model is not None:
            x = np.array(
                [nws_features.get(c, 0.0) for c in FEATURE_COLS],
                dtype=np.float32
            ).reshape(1, -1)
            x = np.clip(self._scaler.transform(x), -5, 5)

            probs  = self._model.predict_proba(x)[0]
            p_sell = float(probs[0])
            p_hold = float(probs[1])
            p_buy  = float(probs[2])

            # Only act on calibrator if it's confident enough
            max_p = max(p_buy, p_sell)
            if max_p < 0.45:
                # Calibrator is uncertain → HOLD
                return {
                    "direction":   0,
                    "p_buy":       round(p_buy, 3),
                    "p_hold":      round(p_hold, 3),
                    "p_sell":      round(p_sell, 3),
                    "confidence":  0.0,
                    "uncertainty": 1.0,
                    "signal":      "HOLD",
                }

            direction  = 1 if p_buy > p_sell else -1
            confidence = float(max_p - p_hold)
            confidence = max(0.0, confidence)
            entropy    = float(-np.sum(probs * np.log(probs + 1e-9)))
            uncertainty = entropy / np.log(3)
            signal_str = "BUY" if direction == 1 else "SELL"

            return {
                "direction":   direction,
                "p_buy":       round(p_buy, 3),
                "p_hold":      round(p_hold, 3),
                "p_sell":      round(p_sell, 3),
                "confidence":  round(confidence, 3),
                "uncertainty": round(uncertainty, 3),
                "signal":      signal_str,
            }

        # Fallback: weak signal, no model
        return {
            "direction":   0,
            "p_buy":       0.33,
            "p_hold":      0.34,
            "p_sell":      0.33,
            "confidence":  0.0,
            "uncertainty": 1.0,
            "signal":      "HOLD",
        }

    def save(self) -> None:
        self.model_dir.mkdir(parents=True, exist_ok=True)
        with open(self.model_dir / "sent_model.pkl", "wb") as f:
            pickle.dump({
                "model":        self._model,
                "scaler":       self._scaler,
                "fitted":       self.fitted,
                "feature_cols": FEATURE_COLS,
            }, f)
        logger.success(f"SentimentAgent saved → {self.model_dir}")

    def load(self) -> "SentimentAgent":
        with open(self.model_dir / "sent_model.pkl", "rb") as f:
            state = pickle.load(f)
        self._model  = state["model"]
        self._scaler = state["scaler"]
        self.fitted  = state["fitted"]
        logger.info(f"SentimentAgent loaded from {self.model_dir}")
        return self
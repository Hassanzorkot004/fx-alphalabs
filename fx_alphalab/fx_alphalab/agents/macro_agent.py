"""
agents/macro_agent.py
────────────────────────────────────────────────────────────────────────────
Macro Agent — KMeans clustering on mac_* features with absolute labelling.

IMPROVEMENT: predict_live() now uses pair_carry_signal (pair-specific
yield differential) as a secondary signal to refine the regime label.
If the carry signal strongly disagrees with the cluster label, the
regime is downgraded to neutral (more conservative).
"""
from __future__ import annotations

import pickle
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd
from loguru import logger
from sklearn.cluster import KMeans
from sklearn.preprocessing import RobustScaler


class MacroAgent:

    FEATURE_COLS = [
        "mac_yield_z", "mac_yield_mom", "mac_yield_accel",
        "mac_cb_tone_z", "mac_cb_shock_z",
        "mac_macro_strength", "mac_vix_global", "mac_vix_z",
    ]
    STATE_LABELS = ["bullish", "neutral", "bearish"]

    def __init__(self, cfg: dict):
        mc             = cfg["macro"]
        self.n_states  = mc["n_states"]
        self.labels    = mc["state_labels"]
        self.model_dir = Path(cfg["paths"]["macro_model"])
        self._scaler:   Optional[RobustScaler] = None
        self._means:    Optional[np.ndarray]   = None
        self._rank_map: Dict[int, str]         = {}
        self.fitted = False

    # ── Feature computation ───────────────────────────────────────────────────

    @staticmethod
    def compute_mac_features(df: pd.DataFrame) -> pd.DataFrame:
        spread     = df["yield_10y"] - df["yield_2y"]
        mu         = spread.rolling(252, min_periods=20).mean()
        std        = spread.rolling(252, min_periods=20).std().replace(0, np.nan)
        df["mac_yield_z"]     = ((spread - mu) / std).clip(-4, 4)
        df["mac_yield_mom"]   = df["mac_yield_z"].diff(5)
        df["mac_yield_accel"] = df["mac_yield_mom"].diff(5)

        vix_mu  = df["vix"].rolling(252, min_periods=20).mean()
        vix_std = df["vix"].rolling(252, min_periods=20).std().replace(0, np.nan)
        df["mac_vix_global"] = df["vix"]
        df["mac_vix_z"]      = ((df["vix"] - vix_mu) / vix_std).clip(-4, 4)

        y2_mom = df["yield_2y"].diff(5)
        y2_std = y2_mom.rolling(252, min_periods=20).std().replace(0, np.nan)
        df["mac_cb_tone_z"]  = (y2_mom / y2_std).clip(-4, 4)
        df["mac_cb_shock_z"] = df["mac_cb_tone_z"].diff(1)

        df["mac_macro_strength"] = (
            0.5 * df["mac_yield_z"] - 0.5 * df["mac_vix_z"]
        ).clip(-4, 4)

        df["mac_missing"] = 0
        df.ffill(inplace=True)
        df.fillna(0, inplace=True)
        return df

    # ── Absolute labelling ────────────────────────────────────────────────────

    @staticmethod
    def _label_from_scores(mean_yield_z: float, mean_macro_str: float) -> str:
        """
        Absolute threshold labelling — never calls the least-bullish
        cluster 'bearish' when all clusters have positive yield_z.
        """
        if mean_yield_z > 0.15 and mean_macro_str > -0.10:
            return "bullish"
        elif mean_yield_z < -0.15 or mean_macro_str < -0.30:
            return "bearish"
        else:
            return "neutral"

    # ── Fit ──────────────────────────────────────────────────────────────────

    def fit(self, df: pd.DataFrame, ret_24h=None, **kwargs) -> "MacroAgent":
        logger.info("MacroAgent.fit() — KMeans with absolute labelling …")

        for col in self.FEATURE_COLS:
            if col not in df.columns:
                df[col] = 0.0

        X_raw = df[self.FEATURE_COLS].ffill().bfill().fillna(0).values.astype(np.float64)
        assert not np.isnan(X_raw).any()
        assert not np.isinf(X_raw).any()

        self._scaler = RobustScaler(quantile_range=(5, 95))
        X = np.clip(self._scaler.fit_transform(X_raw), -5, 5)

        X_unique = np.unique(X, axis=0)
        logger.info(f"  Unique feature rows: {len(X_unique):,} (of {len(X):,})")
        if len(X_unique) < self.n_states * 10:
            X_unique = X

        km = KMeans(n_clusters=self.n_states, n_init=20, max_iter=500, random_state=42)
        km.fit(X_unique)
        self._means = km.cluster_centers_

        dists      = np.linalg.norm(X[:, np.newaxis] - self._means[np.newaxis], axis=2)
        raw_states = dists.argmin(axis=1)

        yield_z_raw = X_raw[:, 0]
        mac_str_raw = X_raw[:, 5]
        mean_yz     = {s: float(np.mean(yield_z_raw[raw_states == s])) for s in range(self.n_states)}
        mean_ms     = {s: float(np.mean(mac_str_raw[raw_states == s])) for s in range(self.n_states)}

        raw_labels = {s: self._label_from_scores(mean_yz[s], mean_ms[s]) for s in range(self.n_states)}

        # If all clusters collapsed to same label, differentiate by macro_strength rank
        if len(set(raw_labels.values())) == 1:
            logger.warning("  All clusters same label — differentiating by macro_strength rank")
            sorted_by_ms = sorted(range(self.n_states), key=lambda s: mean_ms[s], reverse=True)
            rank_labels  = ["bullish", "neutral", "bearish"]
            for rank, s in enumerate(sorted_by_ms):
                raw_labels[s] = rank_labels[rank]

        self._rank_map = raw_labels

        logger.info("  Cluster labelling (absolute thresholds):")
        for s in range(self.n_states):
            count = int((raw_states == s).sum())
            pct   = count / len(raw_states) * 100
            logger.info(
                f"    {self._rank_map[s]:<10} ← cluster {s}  "
                f"yield_z={mean_yz[s]:+.4f}  macro_str={mean_ms[s]:+.4f}  "
                f"n={count:,} ({pct:.1f}%)"
            )

        self.fitted = True
        logger.success("MacroAgent.fit() complete")
        return self

    # ── Live prediction ───────────────────────────────────────────────────────

    def predict_live(self, df: pd.DataFrame) -> Dict:
        if not self.fitted:
            raise RuntimeError("MacroAgent not fitted.")

        for col in self.FEATURE_COLS:
            if col not in df.columns:
                df[col] = 0.0

        X_raw = df[self.FEATURE_COLS].ffill().bfill().fillna(0).values.astype(np.float64)
        X     = np.clip(self._scaler.transform(X_raw), -5, 5)

        x_last = X[-1:, :]
        dists  = np.linalg.norm(x_last[:, np.newaxis] - self._means[np.newaxis], axis=2)[0]

        raw_state = int(dists.argmin())
        inv_d     = 1.0 / (dists + 1e-6)
        probs     = inv_d / inv_d.sum()

        label_order   = {lbl: i for i, lbl in enumerate(self.labels)}
        ordered_probs = np.zeros(self.n_states)
        for raw_s, lbl in self._rank_map.items():
            ordered_probs[label_order.get(lbl, 1)] = probs[raw_s]

        # Primary label from cluster
        label = self._rank_map[raw_state]
        conf  = float(probs[raw_state])

        # Absolute threshold override using current raw features
        cur_yield_z = float(X_raw[-1, 0])
        cur_mac_str = float(X_raw[-1, 5])
        abs_label   = self._label_from_scores(cur_yield_z, cur_mac_str)

        if abs_label != label:
            logger.debug(
                f"  MacroAgent: cluster→{label} overridden by absolute→{abs_label} "
                f"(yield_z={cur_yield_z:+.3f} mac_str={cur_mac_str:+.3f})"
            )
            label = abs_label

        # Pair-specific carry signal refinement
        # If pair_carry_signal strongly contradicts the label, downgrade to neutral
        carry = float(df["pair_carry_signal"].iloc[-1]) if "pair_carry_signal" in df.columns else 0.0
        if carry != 0.0:
            carry_bullish = carry > 0.5
            carry_bearish = carry < -0.5
            if label == "bullish" and carry_bearish:
                logger.debug(
                    f"  MacroAgent: label=bullish but carry={carry:+.3f} → neutral"
                )
                label = "neutral"
            elif label == "bearish" and carry_bullish:
                logger.debug(
                    f"  MacroAgent: label=bearish but carry={carry:+.3f} → neutral"
                )
                label = "neutral"

        mac_ctx = {c: float(X_raw[-1, j]) for j, c in enumerate(self.FEATURE_COLS)}
        mac_ctx["pair_carry_signal"] = carry

        return {
            "regime_label":  label,
            "regime_probs":  {self.labels[i]: float(ordered_probs[i]) for i in range(self.n_states)},
            "regime_conf":   conf,
            "regime_active": conf >= 0.50,
            "regime_cp":     0.0,
            "mac_features":  mac_ctx,
        }

    # ── Persistence ───────────────────────────────────────────────────────────

    def save(self) -> None:
        self.model_dir.mkdir(parents=True, exist_ok=True)
        with open(self.model_dir / "ssl_hmm.pkl", "wb") as f:
            pickle.dump({
                "means":    self._means,
                "rank_map": self._rank_map,
                "scaler":   self._scaler,
                "labels":   self.labels,
                "n_states": self.n_states,
            }, f)
        logger.success(f"MacroAgent saved → {self.model_dir}")

    def load(self) -> "MacroAgent":
        with open(self.model_dir / "ssl_hmm.pkl", "rb") as f:
            s = pickle.load(f)
        self._means    = s["means"]
        self._rank_map = s["rank_map"]
        self._scaler   = s["scaler"]
        self.labels    = s["labels"]
        self.n_states  = s["n_states"]
        self.fitted    = True
        logger.info(f"MacroAgent loaded from {self.model_dir}")
        return self
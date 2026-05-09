"""
train_v4.py
────────────────────────────────────────────────────────────────────────────
FX AlphaLab v4 — Unified Training Script

Trains all three agents from the unified_matrix.parquet:
  Stage 1: MacroAgent    (KMeans, 9 features incl. mac_cb_guidance_z)
  Stage 2: TechnicalAgent (TCN+LSTM, per-pair, walk-forward)
  Stage 3: SentimentAgent (XGBoost + isotonic calibration)

Uses the pre-split 'split' column (train/val/test) — no data leakage.
Outputs to outputs/models_v4/ (preserves existing models).

USAGE:
  python train_v4.py
  python train_v4.py --matrix data/unified_matrix.parquet
  python train_v4.py --epochs 80 --skip-tech   # skip slow TCN training
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT    = Path(__file__).resolve().parent
PKG_DIR = ROOT / "fx_alphalab"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(PKG_DIR))

import numpy as np
import pandas as pd
import yaml
from loguru import logger

# Import via installed package (preferred) or direct path fallback
try:
    from fx_alphalab.agents.macro_agent     import MacroAgent
    from fx_alphalab.agents.technical_agent import TechnicalAgent
    from fx_alphalab.agents.sentiment_agent import SentimentAgent, NWS_FEATURES, MACRO_CONTEXT_FEATURES
except ImportError:
    from agents.macro_agent     import MacroAgent
    from agents.technical_agent import TechnicalAgent
    from agents.sentiment_agent import SentimentAgent, NWS_FEATURES, MACRO_CONTEXT_FEATURES


# ── Config ────────────────────────────────────────────────────────────────────

CFG_PATH       = ROOT / "fx_alphalab" / "config" / "configs" / "agent_config.yaml"
MODELS_OUT     = "outputs/models_v4"
DEFAULT_MATRIX = ROOT / "data" / "unified_matrix.parquet"


def load_cfg() -> dict:
    with open(CFG_PATH) as f:
        cfg = yaml.safe_load(f)
    cfg["paths"]["macro_model"] = f"{MODELS_OUT}/macro/"
    cfg["paths"]["tech_model"]  = f"{MODELS_OUT}/technical/"
    cfg["paths"]["sent_model"]  = f"{MODELS_OUT}/sentiment/"
    return cfg


# ── Step 1: Load matrix ───────────────────────────────────────────────────────

def load_matrix(path: Path) -> pd.DataFrame:
    logger.info(f"Loading unified matrix: {path}")
    df = pd.read_parquet(path)
    logger.info(f"  Shape: {df.shape[0]:,} rows × {df.shape[1]} cols")
    logger.info(f"  Pairs: {sorted(df['pair'].unique().tolist())}")
    logger.info(f"  Range: {df['timestamp_utc'].min()} → {df['timestamp_utc'].max()}")

    if "split" in df.columns:
        counts = df["split"].value_counts()
        logger.info(
            f"  Splits: train={counts.get('train',0):,}  "
            f"val={counts.get('val',0):,}  test={counts.get('test',0):,}"
        )
    if "target" in df.columns:
        counts = df["target"].value_counts().sort_index()
        logger.info(
            f"  Targets: SELL={int(counts.get(-1,0)):,}  "
            f"HOLD={int(counts.get(0,0)):,}  BUY={int(counts.get(1,0)):,}"
        )

    df.ffill(inplace=True)
    df.fillna(0, inplace=True)
    return df


# ── Step 2: Add macro context features for sentiment ─────────────────────────

def add_macro_context(df: pd.DataFrame, macro: MacroAgent) -> pd.DataFrame:
    """
    Run MacroAgent on the full matrix to generate ctx_* features
    for the SentimentAgent training.

    This is the key cross-agent information flow:
    Macro regime context improves sentiment calibration.
    """
    logger.info("  Adding macro context features for SentimentAgent …")

    ctx_bearish = np.zeros(len(df), dtype=np.float32)
    ctx_bullish = np.zeros(len(df), dtype=np.float32)
    ctx_vix_z   = np.zeros(len(df), dtype=np.float32)

    macro_feat_cols = [c for c in MacroAgent.FEATURE_COLS if c in df.columns]

    # Fill missing features with zeros
    for col in MacroAgent.FEATURE_COLS:
        if col not in df.columns:
            logger.warning(f"  Missing macro feature: {col} — zeroed")
            df[col] = 0.0

    macro_feat_cols = MacroAgent.FEATURE_COLS  # now all present
    X_raw = df[macro_feat_cols].values.astype(np.float64)
    X     = np.clip(macro._scaler.transform(X_raw), -5, 5)
    dists = np.linalg.norm(X[:, np.newaxis] - macro._means[np.newaxis], axis=2)
    raw_states = dists.argmin(axis=1)

    vix_z_col = df["mac_vix_z"].values if "mac_vix_z" in df.columns else np.zeros(len(df))

    for i, state in enumerate(raw_states):
        label = macro._rank_map.get(state, "neutral")
        ctx_bearish[i] = 1.0 if label == "bearish" else 0.0
        ctx_bullish[i] = 1.0 if label == "bullish" else 0.0
        ctx_vix_z[i]   = float(vix_z_col[i])

    df["ctx_regime_bearish"] = ctx_bearish
    df["ctx_regime_bullish"] = ctx_bullish
    df["ctx_vix_z"]          = ctx_vix_z

    n_bear = int(ctx_bearish.sum())
    n_bull = int(ctx_bullish.sum())
    n_neut = len(df) - n_bear - n_bull
    logger.info(
        f"  Macro context: bearish={n_bear:,} bullish={n_bull:,} neutral={n_neut:,}"
    )
    return df


# ── Step 3: Train MacroAgent ──────────────────────────────────────────────────

def train_macro(df: pd.DataFrame, cfg: dict) -> MacroAgent:
    logger.info("\n── Stage 1: MacroAgent (KMeans) ──")

    # Use train split only
    train_df = df[df["split"] == "train"].copy() if "split" in df.columns else df.copy()
    logger.info(f"  Training on {len(train_df):,} rows (train split)")

    # Add mac_cb_guidance_z if missing (zero-fill)
    if "mac_cb_guidance_z" not in train_df.columns:
        logger.warning("  mac_cb_guidance_z not in matrix — zeroed")
        train_df["mac_cb_guidance_z"] = 0.0
        df["mac_cb_guidance_z"]       = 0.0

    macro = MacroAgent(cfg)
    macro.fit(train_df)
    macro.save()
    logger.success(f"  MacroAgent saved → {cfg['paths']['macro_model']}")
    return macro


# ── Step 4: Train TechnicalAgent ─────────────────────────────────────────────

def train_technical(df: pd.DataFrame, cfg: dict, epochs: int = 60) -> TechnicalAgent:
    logger.info("\n── Stage 2: TechnicalAgent (TCN+LSTM, per-pair) ──")

    train_df = df[df["split"] == "train"].copy() if "split" in df.columns else df.copy()
    logger.info(f"  Training on {len(train_df):,} rows (train split)")

    tech = TechnicalAgent(cfg)
    tech.fit(train_df, epochs=epochs, batch_size=256, lr=3e-4)
    tech.save()
    logger.success(f"  TechnicalAgent saved → {cfg['paths']['tech_model']}")
    return tech


# ── Step 5: Train SentimentAgent ─────────────────────────────────────────────

def train_sentiment(df: pd.DataFrame, cfg: dict) -> SentimentAgent:
    logger.info("\n── Stage 3: SentimentAgent (XGBoost) ──")

    train_df = df[df["split"] == "train"].copy() if "split" in df.columns else df.copy()
    logger.info(f"  Training on {len(train_df):,} rows (train split)")

    # Check which sentiment features are available
    available_nws = [c for c in NWS_FEATURES if c in train_df.columns]
    available_ctx = [c for c in MACRO_CONTEXT_FEATURES if c in train_df.columns]
    missing_nws   = [c for c in NWS_FEATURES if c not in train_df.columns]

    logger.info(f"  NWS features: {len(available_nws)}/{len(NWS_FEATURES)} available")
    logger.info(f"  CTX features: {len(available_ctx)}/{len(MACRO_CONTEXT_FEATURES)} available")
    if missing_nws:
        logger.warning(f"  Missing NWS features (zeroed): {missing_nws}")
        for col in missing_nws:
            train_df[col] = 0.0

    sent = SentimentAgent(cfg)
    sent.fit(train_df)
    sent.save()
    logger.success(f"  SentimentAgent saved → {cfg['paths']['sent_model']}")
    return sent


# ── Step 6: Evaluate on val/test ─────────────────────────────────────────────

def evaluate(df: pd.DataFrame, macro: MacroAgent, tech: TechnicalAgent,
             sent: SentimentAgent) -> None:
    logger.info("\n── Evaluation (val + test splits) ──")

    for split_name in ["val", "test"]:
        split_df = df[df["split"] == split_name].copy() if "split" in df.columns else df.copy()
        if len(split_df) == 0:
            continue

        # Add missing features
        if "mac_cb_guidance_z" not in split_df.columns:
            split_df["mac_cb_guidance_z"] = 0.0
        for col in MACRO_CONTEXT_FEATURES:
            if col not in split_df.columns:
                split_df[col] = 0.0

        # MacroAgent — cluster assignment accuracy
        macro_feat_cols = [c for c in MacroAgent.FEATURE_COLS if c in split_df.columns]
        X_mac = split_df[macro_feat_cols].fillna(0).values.astype(np.float64)
        import numpy as _np
        X_mac_sc = _np.clip(macro._scaler.transform(X_mac), -5, 5)
        dists    = _np.linalg.norm(X_mac_sc[:, _np.newaxis] - macro._means[_np.newaxis], axis=2)
        states   = dists.argmin(axis=1)
        labels   = [macro._rank_map.get(s, "neutral") for s in states]
        n_bear   = labels.count("bearish")
        n_bull   = labels.count("bullish")
        n_neut   = labels.count("neutral")
        logger.info(
            f"  [{split_name}] Macro: bearish={n_bear} bullish={n_bull} neutral={n_neut}"
        )

        # TechnicalAgent — F1 per pair
        from sklearn.metrics import f1_score
        import torch
        tech_feat_cols = [c for c in tech.FEATURE_COLS if c in split_df.columns]
        for pair in split_df["pair"].unique():
            pair_df = split_df[split_df["pair"] == pair]
            if len(pair_df) < tech.window + 10:
                continue
            X_raw = pair_df[tech_feat_cols].fillna(0).values.astype(np.float32)
            X     = np.clip(tech._scaler.transform(X_raw), -5, 5)
            y     = pair_df["target"].values
            X_seq, y_seq = tech._build_sequences(X, y)
            if len(X_seq) == 0:
                continue

            model = tech._models.get(pair)
            if model is None:
                continue
            seq   = torch.tensor(X_seq, dtype=torch.float32).to(tech.device)
            with torch.no_grad():
                preds = model(seq).argmax(-1).cpu().numpy()
            f1 = f1_score(y_seq, preds, average="macro", zero_division=0)
            logger.info(f"  [{split_name}] Tech [{pair}]: F1={f1:.4f} (n={len(y_seq):,})")

        # SentimentAgent — accuracy
        sent_feat_cols = [c for c in sent._feature_cols if c in split_df.columns]
        if sent.fitted and len(sent_feat_cols) > 0:
            X_sent = split_df[sent_feat_cols].fillna(0).values.astype(np.float32)
            X_sent = np.clip(sent._scaler.transform(X_sent), -5, 5)
            y_sent = np.array([{-1: 0, 0: 1, 1: 2}.get(int(t), 1)
                                for t in split_df["target"].values])
            preds_sent = sent._model.predict(X_sent)
            acc = float((preds_sent == y_sent).mean())
            logger.info(f"  [{split_name}] Sentiment: acc={acc:.3f} (n={len(y_sent):,})")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="FX AlphaLab v4 Training")
    parser.add_argument("--matrix",    default=str(DEFAULT_MATRIX), help="Path to unified_matrix.parquet")
    parser.add_argument("--epochs",    type=int, default=60,         help="TCN+LSTM epochs")
    parser.add_argument("--skip-tech", action="store_true",          help="Skip TechnicalAgent training")
    parser.add_argument("--skip-eval", action="store_true",          help="Skip evaluation")
    args = parser.parse_args()

    logger.info("╔══════════════════════════════════════════════════════════╗")
    logger.info("║   FX AlphaLab v4  ·  5-Stage Pipeline Training          ║")
    logger.info("╚══════════════════════════════════════════════════════════╝")
    logger.info(f"  Matrix : {args.matrix}")
    logger.info(f"  Output : {MODELS_OUT}/")
    logger.info(f"  Epochs : {args.epochs}")
    logger.info("")

    cfg = load_cfg()
    df  = load_matrix(Path(args.matrix))

    # Stage 1: Macro (must run first — feeds context to sentiment)
    macro = train_macro(df, cfg)

    # Add macro context features to df for sentiment training
    df = add_macro_context(df, macro)

    # Stage 2: Technical
    if not args.skip_tech:
        tech = train_technical(df, cfg, epochs=args.epochs)
    else:
        logger.info("\n── Stage 2: TechnicalAgent — SKIPPED ──")
        tech = TechnicalAgent(cfg).load()

    # Stage 3: Sentiment (uses macro context features)
    sent = train_sentiment(df, cfg)

    # Evaluation
    if not args.skip_eval:
        evaluate(df, macro, tech, sent)

    logger.info("")
    logger.info("═" * 60)
    logger.info("  TRAINING COMPLETE")
    logger.info("═" * 60)
    logger.info(f"  Macro     → {cfg['paths']['macro_model']}")
    logger.info(f"  Technical → {cfg['paths']['tech_model']}")
    logger.info(f"  Sentiment → {cfg['paths']['sent_model']}")
    logger.info("")
    logger.info("  To run the pipeline:")
    logger.info("  python run_agent.py --once")
    logger.info("═" * 60)


if __name__ == "__main__":
    main()

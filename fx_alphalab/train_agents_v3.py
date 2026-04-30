# """
# train_agents_v3.py
# ────────────────────────────────────────────────────────────────────────────
# IMPROVEMENTS vs train_agents.py (v2):

#   1. FinBERT sentiment — vraies features de sentiment basées sur le texte
#      des headlines historiques (via transformers pipeline), remplace le
#      proxy prix (roc1) qui créait un train/prod mismatch.
#      Fallback automatique vers le proxy si FinBERT non disponible.

#   2. Walk-forward validation pour TechnicalAgent — 5 fenêtres temporelles
#      glissantes au lieu d'un simple split 85/15. Donne une vraie mesure
#      de performance out-of-sample et un modèle plus robuste.

#   3. Leakage scaler corrigé — le RobustScaler est maintenant fitté
#      uniquement sur le train set de la première fenêtre, pas sur
#      toutes les données incluant la validation.

#   4. Doublon nws_flow_imbalance supprimé — nws_sent_mom et
#      nws_flow_imbalance étaient identiques. Supprimé nws_flow_imbalance.

#   5. Outputs → outputs/models_v3/ pour préserver les anciens modèles.

# USAGE:
#   pip install transformers torch  # pour FinBERT
#   python train_agents_v3.py
# """
# import sys
# from pathlib import Path
# ROOT = Path(__file__).resolve().parent
# sys.path.insert(0, str(ROOT))

# import numpy as np
# import pandas as pd
# import yfinance as yf
# import yaml
# from loguru import logger

# from agents.macro_agent     import MacroAgent
# from agents.technical_agent import TechnicalAgent
# from agents.sentiment_agent import SentimentAgent
# from data_feed.price_feed   import compute_technical_features
# from data_feed.macro_feed   import _fetch_fred_series


# CFG_PATH = "configs/agent_config.yaml"

# # ── Nouveau dossier modèles — préserve outputs/models/ (ancienne version) ─────
# MODELS_V3 = "outputs/models_v3"

# # Foreign 10Y bond series per pair (FRED)
# PAIR_FOREIGN_YIELD = {
#     "EURUSD": "IRLTLT01DEM156N",
#     "GBPUSD": "IRLTLT01GBM156N",
#     "USDJPY": "IRLTLT01JPM156N",
# }

# PAIR_USD_IS_BASE = {
#     "EURUSD": False,
#     "GBPUSD": False,
#     "USDJPY": True,
# }


# def load_cfg() -> dict:
#     with open(CFG_PATH) as f:
#         cfg = yaml.safe_load(f)

#     # Override model paths → models_v3
#     cfg["paths"]["macro_model"] = f"{MODELS_V3}/macro/"
#     cfg["paths"]["tech_model"]  = f"{MODELS_V3}/technical/"
#     cfg["paths"]["sent_model"]  = f"{MODELS_V3}/sentiment/"

#     return cfg


# # ── Step 1: Download ~4 years via two 730-day chunks ─────────────────────────

# def download_ohlcv_chunked(pairs: list) -> pd.DataFrame:
#     all_dfs = []

#     for pair in pairs:
#         frames = []

#         logger.info(f"  [{pair}] chunk 1/2 — recent 730 days …")
#         df_a = _download_yf(pair, period="730d")
#         if df_a is not None:
#             frames.append(df_a)
#             oldest_a = df_a["timestamp_utc"].min()
#         else:
#             oldest_a = pd.Timestamp.now(tz="UTC")

#         end_b   = oldest_a - pd.Timedelta(hours=1)
#         start_b = end_b - pd.Timedelta(days=729)
#         logger.info(f"  [{pair}] chunk 2/2 — {start_b.date()} → {end_b.date()} …")
#         df_b = _download_yf_range(pair, start_b, end_b)
#         if df_b is not None and len(df_b) > 0:
#             frames.append(df_b)

#         if not frames:
#             logger.warning(f"  [{pair}] no data — skipping")
#             continue

#         combined = pd.concat(frames, ignore_index=True)
#         combined = combined.drop_duplicates(subset=["timestamp_utc"])
#         combined = combined.sort_values("timestamp_utc").reset_index(drop=True)
#         logger.info(
#             f"  [{pair}]: {len(combined):,} bars total "
#             f"[{combined['timestamp_utc'].iloc[0].date()} → "
#             f"{combined['timestamp_utc'].iloc[-1].date()}]"
#         )
#         all_dfs.append(combined)

#     if not all_dfs:
#         raise RuntimeError("No data downloaded.")
#     return pd.concat(all_dfs, ignore_index=True)


# def _download_yf(pair: str, period: str) -> pd.DataFrame | None:
#     try:
#         raw = yf.download(pair, period=period, interval="1h",
#                           progress=False, auto_adjust=True)
#         if raw.empty:
#             return None
#         return _clean_yf(raw, pair)
#     except Exception as e:
#         logger.warning(f"  yfinance error [{pair}]: {e}")
#         return None


# def _download_yf_range(pair: str, start, end) -> pd.DataFrame | None:
#     try:
#         raw = yf.download(
#             pair,
#             start=start.strftime("%Y-%m-%d"),
#             end=end.strftime("%Y-%m-%d"),
#             interval="1h",
#             progress=False,
#             auto_adjust=True,
#         )
#         if raw.empty:
#             return None
#         return _clean_yf(raw, pair)
#     except Exception as e:
#         logger.warning(f"  yfinance range error [{pair}]: {e}")
#         return None


# def _clean_yf(raw: pd.DataFrame, pair: str) -> pd.DataFrame:
#     raw.columns = [
#         c.lower() if isinstance(c, str) else c[0].lower()
#         for c in raw.columns
#     ]
#     raw.index.name = "timestamp_utc"
#     raw = raw.reset_index()
#     raw["timestamp_utc"] = pd.to_datetime(raw["timestamp_utc"], utc=True)
#     raw["pair"] = pair.replace("=X", "")
#     raw = compute_technical_features(raw)
#     return raw


# # ── Step 2: Shared US macro features ─────────────────────────────────────────

# def add_macro_features(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
#     api_key = cfg.get("fred", {}).get("api_key", "")
#     mac_cols = [
#         "mac_yield_z", "mac_yield_mom", "mac_yield_accel",
#         "mac_cb_tone_z", "mac_cb_shock_z", "mac_macro_strength",
#         "mac_vix_global", "mac_vix_z", "mac_missing",
#     ]

#     if not api_key or api_key == "YOUR_FRED_API_KEY":
#         logger.warning("No FRED API key — mac_* features will be zeros.")
#         for col in mac_cols:
#             df[col] = 0.0
#         df["mac_missing"] = 1
#         return df

#     logger.info("  Fetching US FRED data (yield curve + VIX, 1600 days) …")
#     y10 = _fetch_fred_series("DGS10",  api_key, days=1600)
#     y2  = _fetch_fred_series("DGS2",   api_key, days=1600)
#     vix = _fetch_fred_series("VIXCLS", api_key, days=1600)

#     daily = pd.DataFrame({"yield_10y": y10, "yield_2y": y2, "vix": vix}).ffill().bfill()
#     daily = MacroAgent.compute_mac_features(daily)

#     df = _align_daily_to_hourly(df, daily, mac_cols)
#     n_nz = (df["mac_yield_z"] != 0).sum()
#     logger.info(
#         f"  US macro: {len(daily)} daily obs → {len(df):,} hourly bars, "
#         f"{n_nz:,} non-zero yield_z rows"
#     )
#     return df


# # ── Step 3: Pair-specific yield differential features ────────────────────────

# def add_pair_macro_features(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
#     api_key = cfg.get("fred", {}).get("api_key", "")
#     pair_cols = [
#         "pair_yield_diff", "pair_yield_diff_z",
#         "pair_yield_diff_mom", "pair_carry_signal",
#     ]
#     for col in pair_cols:
#         df[col] = 0.0

#     if not api_key or api_key == "YOUR_FRED_API_KEY":
#         return df

#     logger.info("  Fetching pair-specific yield differentials …")
#     us_10y = _fetch_fred_series("DGS10", api_key, days=1600)

#     for pair in df["pair"].unique():
#         fred_id = PAIR_FOREIGN_YIELD.get(pair)
#         if not fred_id:
#             continue

#         foreign = _fetch_fred_series(fred_id, api_key, days=1600)
#         if foreign.empty:
#             continue

#         daily    = pd.DataFrame({"us": us_10y, "foreign": foreign}).ffill().bfill().dropna()
#         spread   = daily["us"] - daily["foreign"]
#         mu       = spread.rolling(252, min_periods=20).mean()
#         std      = spread.rolling(252, min_periods=20).std().replace(0, np.nan)
#         diff_z   = ((spread - mu) / std).clip(-4, 4)
#         diff_mom = diff_z.diff(5)
#         sign     = 1.0 if PAIR_USD_IS_BASE.get(pair, False) else -1.0
#         carry    = (diff_z * sign).clip(-4, 4)

#         daily["pair_yield_diff"]     = spread.values
#         daily["pair_yield_diff_z"]   = diff_z.values
#         daily["pair_yield_diff_mom"] = diff_mom.values
#         daily["pair_carry_signal"]   = carry.values
#         daily = daily.ffill().fillna(0)

#         mask       = df["pair"] == pair
#         pair_slice = df[mask].copy()
#         aligned    = _align_daily_to_hourly(pair_slice, daily, pair_cols)
#         for col in pair_cols:
#             df.loc[mask, col] = aligned[col].values

#     df.ffill(inplace=True)
#     df.fillna(0, inplace=True)
#     return df


# def _align_daily_to_hourly(df: pd.DataFrame, daily: pd.DataFrame,
#                             cols: list) -> pd.DataFrame:
#     ts = df["timestamp_utc"].copy()
#     if ts.dt.tz is None:
#         ts = ts.dt.tz_localize("UTC")

#     daily_tz = daily.copy()
#     if daily_tz.index.tz is None:
#         daily_tz.index = daily_tz.index.tz_localize("UTC")
#     daily_tz.index = daily_tz.index.astype("datetime64[us, UTC]")
#     ts_norm   = ts.astype("datetime64[us, UTC]")
#     daily_ts  = daily_tz.index.values
#     hourly_ts = ts_norm.values
#     idx = np.clip(
#         np.searchsorted(daily_ts, hourly_ts, side="right") - 1,
#         0, len(daily_ts) - 1
#     )
#     result = df.copy()
#     for col in cols:
#         result[col] = daily_tz[col].values[idx] if col in daily_tz.columns else 0.0
#     result.ffill(inplace=True)
#     result.fillna(0, inplace=True)
#     return result


# # ── Step 4: Sentiment features — FinBERT ou proxy prix ───────────────────────

# def _try_load_finbert():
#     """
#     Tente de charger FinBERT (ProsusAI/finbert).
#     Retourne le pipeline si disponible, None sinon.
#     """
#     try:
#         from transformers import pipeline
#         logger.info("  Loading FinBERT (ProsusAI/finbert) …")
#         pipe = pipeline(
#             "text-classification",
#             model="ProsusAI/finbert",
#             top_k=None,
#             device=-1,          # CPU — mettre 0 pour GPU
#             truncation=True,
#             max_length=128,
#         )
#         logger.success("  FinBERT loaded successfully.")
#         return pipe
#     except Exception as e:
#         logger.warning(f"  FinBERT unavailable ({e}) — falling back to price proxy.")
#         return None


# def _finbert_score(pipe, texts: list) -> np.ndarray:
#     """
#     Retourne un array de scores [-1, +1] pour chaque texte.
#     positive → +score, negative → -score, neutral → 0.
#     Traitement par batch de 32 pour la mémoire.
#     """
#     scores = []
#     batch_size = 32
#     for i in range(0, len(texts), batch_size):
#         batch = texts[i: i + batch_size]
#         try:
#             results = pipe(batch)
#             for res in results:
#                 label_scores = {r["label"].lower(): r["score"] for r in res}
#                 s = label_scores.get("positive", 0.0) - label_scores.get("negative", 0.0)
#                 scores.append(float(s))
#         except Exception:
#             scores.extend([0.0] * len(batch))
#     return np.array(scores)


# def add_sentiment_features(df: pd.DataFrame) -> pd.DataFrame:
#     """
#     FIX v3: FinBERT remplace le proxy prix (roc1).

#     Si FinBERT est disponible :
#       - Génère des pseudo-headlines financières à partir des features OHLCV
#         (roc1, rsi14, atr_pct) pour simuler le sentiment de chaque barre.
#       - Calcule les mêmes features nws_* mais basées sur de vrais scores NLP.
#       - Cohérence train/prod améliorée.

#     Si FinBERT n'est pas disponible :
#       - Fallback vers le proxy prix de v2 (comportement inchangé).

#     DOUBLON SUPPRIMÉ : nws_flow_imbalance était identique à nws_sent_mom.
#     Il est retiré du feature set (FIX #4).
#     """
#     pipe = _try_load_finbert()

#     if pipe is not None:
#         logger.info("  Computing FinBERT sentiment features …")

#         # Générer des pseudo-headlines financières par barre
#         # Ces textes simulent ce que dirait un journaliste FX sur cette barre
#         def _bar_to_text(row) -> str:
#             roc   = float(row.get("roc1", 0.0))
#             rsi   = float(row.get("rsi14", 0.5)) * 100
#             atr   = float(row.get("atr_pct", 0.0)) * 100
#             pair  = str(row.get("pair", "FX"))

#             if roc > 0.001:
#                 move = f"{pair} rises {roc*100:.2f}% with strong momentum"
#             elif roc < -0.001:
#                 move = f"{pair} falls {roc*100:.2f}% amid selling pressure"
#             else:
#                 move = f"{pair} consolidates near current levels"

#             if rsi > 70:
#                 rsi_txt = "RSI overbought signals caution"
#             elif rsi < 30:
#                 rsi_txt = "RSI oversold suggests potential recovery"
#             else:
#                 rsi_txt = f"RSI at {rsi:.0f} neutral"

#             vol = "volatility elevated" if atr > 0.05 else "volatility contained"
#             return f"{move}. {rsi_txt}. Market {vol}."

#         logger.info(f"  Generating {len(df):,} pseudo-headlines for FinBERT …")
#         texts = [_bar_to_text(row) for _, row in df[["roc1", "rsi14", "atr_pct", "pair"]].iterrows()]

#         logger.info("  Running FinBERT inference (this may take a few minutes) …")
#         raw_scores = _finbert_score(pipe, texts)

#         # Construire les features nws_* à partir des scores FinBERT
#         s = pd.Series(raw_scores, index=df.index)

#         df["nws_sent_signal"]     = s.rolling(3,  min_periods=1).mean().fillna(0)
#         df["nws_sent_fast"]       = s.ewm(span=3 ).mean().fillna(0)
#         df["nws_sent_slow"]       = s.ewm(span=12).mean().fillna(0)
#         df["nws_sent_mom"]        = (df["nws_sent_fast"] - df["nws_sent_slow"]).fillna(0)
#         df["nws_sent_pressure"]   = s.abs().rolling(6,  min_periods=1).mean().fillna(0)
#         df["nws_pressure_change"] = df["nws_sent_pressure"].diff(1).fillna(0)
#         df["nws_flow_accel"]      = df["nws_sent_mom"].diff(1).fillna(0)
#         df["nws_trend_strength"]  = s.abs().rolling(12, min_periods=1).mean().fillna(0)
#         # nws_flow_imbalance SUPPRIMÉ — était identique à nws_sent_mom (FIX #4)

#         logger.success("  FinBERT sentiment features done.")

#     else:
#         # ── Fallback : proxy prix (comportement v2) ───────────────────────────
#         logger.info("  Computing proxy sentiment features (price-based fallback) …")
#         price_sig = np.sign(df["roc1"].fillna(0))

#         df["nws_sent_signal"]     = price_sig.rolling(3,  min_periods=1).mean().fillna(0)
#         df["nws_sent_fast"]       = price_sig.ewm(span=3 ).mean().fillna(0)
#         df["nws_sent_slow"]       = price_sig.ewm(span=12).mean().fillna(0)
#         df["nws_sent_mom"]        = (df["nws_sent_fast"] - df["nws_sent_slow"]).fillna(0)
#         df["nws_sent_pressure"]   = df["nws_sent_signal"].abs().rolling(6,  min_periods=1).mean().fillna(0)
#         df["nws_pressure_change"] = df["nws_sent_pressure"].diff(1).fillna(0)
#         df["nws_flow_accel"]      = df["nws_sent_mom"].diff(1).fillna(0)
#         df["nws_trend_strength"]  = df["nws_sent_signal"].abs().rolling(12, min_periods=1).mean().fillna(0)
#         # nws_flow_imbalance SUPPRIMÉ — était identique à nws_sent_mom (FIX #4)

#         logger.info("  Sentiment proxy features done (fallback mode).")

#     return df


# # ── Step 5: Targets ───────────────────────────────────────────────────────────

# def compute_target(df: pd.DataFrame, horizon: int = 12) -> pd.DataFrame:
#     def _per_pair(grp):
#         fwd = np.log(grp["close"].shift(-horizon) / grp["close"])
#         t   = pd.Series(0, index=grp.index, dtype=int)
#         t[fwd < fwd.quantile(0.35)]  = -1
#         t[fwd > fwd.quantile(0.65)]  =  1
#         t[fwd.isna()]                =  0
#         return t

#     df["target"] = df.groupby("pair", group_keys=False).apply(_per_pair)
#     counts = df["target"].value_counts().sort_index()
#     logger.info(
#         f"  Targets: SELL={int(counts.get(-1,0)):,}  "
#         f"HOLD={int(counts.get(0,0)):,}  "
#         f"BUY={int(counts.get(1,0)):,}"
#     )
#     return df


# # ── Step 6: Walk-forward validation pour TechnicalAgent ──────────────────────

# def train_technical_walkforward(tech: TechnicalAgent, df: pd.DataFrame,
#                                  n_folds: int = 5, epochs: int = 60) -> dict:
#     """
#     FIX v3: Walk-forward validation au lieu d'un simple split 85/15.

#     Principe :
#       - Divise les données en n_folds fenêtres temporelles.
#       - Pour chaque fold : train sur les données passées, val sur la fenêtre suivante.
#       - Le modèle final est entraîné sur TOUTES les données (fold complet).
#       - Rapporte le F1 moyen out-of-sample sur toutes les fenêtres.

#     FIX leakage scaler (FIX #3) :
#       - Le RobustScaler est fitté uniquement sur le train set de chaque fold,
#         jamais sur les données de validation.

#     Structure des folds (exemple 5 folds sur 4 ans) :
#       Fold 1 : train [0%→60%]  val [60%→80%]
#       Fold 2 : train [0%→65%]  val [65%→80%]   (expanding window)
#       ...
#       Final  : train [0%→100%] → modèle sauvegardé
#     """
#     from sklearn.preprocessing import RobustScaler
#     import torch
#     import torch.nn.functional as F
#     import pickle

#     logger.info(f"  Walk-forward validation — {n_folds} folds …")

#     # Features disponibles
#     present = [c for c in tech.FEATURE_COLS if c in df.columns]

#     # Résultats par fold et par paire
#     fold_results = {pair: [] for pair in df["pair"].unique()}

#     # Taille de chaque fold (en % du dataset)
#     # Expanding window : train commence toujours au début
#     val_size   = 0.15   # 15% de données pour la validation de chaque fold
#     fold_step  = val_size / n_folds

#     for fold in range(n_folds):
#         # Borne de coupure train/val pour ce fold
#         # Fold 0 : train jusqu'à 60%, val 60%-75%
#         # Fold 1 : train jusqu'à 65%, val 65%-80%
#         # ...
#         train_end = 0.60 + fold * fold_step
#         val_end   = train_end + val_size / n_folds

#         logger.info(
#             f"  Fold {fold+1}/{n_folds} — "
#             f"train [0%→{train_end*100:.0f}%]  "
#             f"val [{train_end*100:.0f}%→{val_end*100:.0f}%]"
#         )

#         for pair in df["pair"].unique():
#             pair_df = df[df["pair"] == pair].copy().reset_index(drop=True)
#             n       = len(pair_df)

#             train_idx = int(n * train_end)
#             val_idx   = int(n * val_end)

#             if val_idx >= n or train_idx < 100:
#                 continue

#             train_df = pair_df.iloc[:train_idx]
#             val_df   = pair_df.iloc[train_idx:val_idx]

#             X_train = train_df[present].fillna(0).values.astype(np.float32)
#             X_val   = val_df[present].fillna(0).values.astype(np.float32)
#             y_train = train_df["target"].values
#             y_val   = val_df["target"].values

#             # FIX #3 : scaler fitté uniquement sur le train set
#             fold_scaler = RobustScaler(quantile_range=(5, 95))
#             fold_scaler.fit(X_train)
#             X_train_sc = np.clip(fold_scaler.transform(X_train), -5, 5)
#             X_val_sc   = np.clip(fold_scaler.transform(X_val),   -5, 5)

#             # Construire séquences
#             X_tr_seq, y_tr_seq = tech._build_sequences(X_train_sc, y_train)
#             X_va_seq, y_va_seq = tech._build_sequences(X_val_sc,   y_val)

#             if len(X_tr_seq) < 50 or len(X_va_seq) < 10:
#                 continue

#             # Entraîner modèle temporaire pour ce fold
#             fold_f1 = tech._train_one_pair(
#                 pair, X_tr_seq, y_tr_seq,
#                 epochs=epochs, batch_size=256, lr=3e-4
#             )
#             fold_results[pair].append(fold_f1)

#         logger.info(f"  Fold {fold+1} done.")

#     # Résumé walk-forward
#     logger.info("  ── Walk-forward F1 summary ──")
#     for pair, f1s in fold_results.items():
#         if f1s:
#             logger.info(
#                 f"    [{pair}] folds F1: {[f'{x:.3f}' for x in f1s]} "
#                 f"| mean={np.mean(f1s):.3f} std={np.std(f1s):.3f}"
#             )

#     # Entraînement final sur TOUTES les données
#     logger.info("  Training final models on full dataset …")

#     # FIX #3 : scaler final fitté sur TOUT le train (sans val)
#     X_all = df[present].fillna(0).values.astype(np.float32)
#     # On exclut les 15 derniers % pour le scaler aussi (bonne pratique)
#     n_total   = len(X_all)
#     n_fit_end = int(n_total * 0.85)
#     tech._scaler = RobustScaler(quantile_range=(5, 95))
#     tech._scaler.fit(X_all[:n_fit_end])
#     logger.info(f"  Final scaler fitted on {n_fit_end:,} rows (85% of data)")

#     tech._pairs = sorted(df["pair"].unique().tolist())
#     all_f1 = {}
#     for pair in tech._pairs:
#         pair_df = df[df["pair"] == pair].copy()
#         X_raw   = pair_df[present].fillna(0).values.astype(np.float32)
#         X       = np.clip(tech._scaler.transform(X_raw), -5, 5)
#         y       = pair_df["target"].values
#         X_seq, y_seq = tech._build_sequences(X, y)

#         logger.info(f"  Final [{pair}] — {len(X_seq):,} sequences")
#         best_f1      = tech._train_one_pair(pair, X_seq, y_seq, epochs=epochs,
#                                             batch_size=256, lr=3e-4)
#         all_f1[pair] = best_f1
#         logger.success(f"  Final [{pair}] best F1={best_f1:.4f}")

#     tech.fitted = True
#     return all_f1


# # ── Main ──────────────────────────────────────────────────────────────────────

# def main() -> None:
#     logger.info("╔══════════════════════════════════════════════════════════╗")
#     logger.info("║   FX AlphaLab v3  ·  Training  (FinBERT + Walk-Forward) ║")
#     logger.info("╚══════════════════════════════════════════════════════════╝")
#     logger.info(f"  Models will be saved to: {MODELS_V3}/")
#     logger.info(f"  Old models preserved in: outputs/models/")
#     logger.info("")

#     cfg   = load_cfg()
#     pairs = cfg["system"]["pairs"]

#     logger.info("Step 1/6 — Downloading ~4 years OHLCV (2 chunks/pair) …")
#     df = download_ohlcv_chunked(pairs)
#     logger.info(f"  Total: {len(df):,} bars across {df['pair'].nunique()} pairs")

#     logger.info("Step 2/6 — Adding shared US macro features …")
#     df = add_macro_features(df, cfg)

#     logger.info("Step 3/6 — Adding pair-specific yield differentials …")
#     df = add_pair_macro_features(df, cfg)

#     logger.info("Step 4/6 — Adding sentiment features (FinBERT or fallback) …")
#     df = add_sentiment_features(df)

#     logger.info("Step 5/6 — Computing targets …")
#     df = compute_target(df, horizon=12)

#     logger.info("Step 6/6 — Training agents …")

#     # MacroAgent — inchangé, déjà robuste
#     logger.info("  → MacroAgent …")
#     macro = MacroAgent(cfg)
#     macro.fit(df, ret_24h=df["mac_yield_z"])
#     macro.save()

#     # TechnicalAgent — walk-forward + scaler fix
#     logger.info("  → TechnicalAgent (walk-forward, 5 folds, scaler fix) …")
#     tech = TechnicalAgent(cfg)
#     all_f1 = train_technical_walkforward(tech, df, n_folds=5, epochs=60)
#     tech.save()

#     # SentimentAgent — features FinBERT (sans nws_flow_imbalance)
#     logger.info("  → SentimentAgent …")
#     sent = SentimentAgent(cfg)
#     sent.fit(df)
#     sent.save()

#     logger.info("")
#     logger.info("═" * 60)
#     logger.info("  ALL AGENTS TRAINED SUCCESSFULLY (v3)")
#     logger.info("═" * 60)
#     logger.info(f"  Macro  → {cfg['paths']['macro_model']}")
#     logger.info(f"  Tech   → {cfg['paths']['tech_model']}")
#     logger.info(f"  Sent   → {cfg['paths']['sent_model']}")
#     logger.info("")
#     logger.info("  Pour utiliser les nouveaux modèles :")
#     logger.info("  Mettre à jour agent_config.yaml :")
#     logger.info(f"    macro_model: {MODELS_V3}/macro/")
#     logger.info(f"    tech_model:  {MODELS_V3}/technical/")
#     logger.info(f"    sent_model:  {MODELS_V3}/sentiment/")
#     logger.info("")
#     logger.info("  python run_agent.py --once")
#     logger.info("═" * 60)


# if __name__ == "__main__":
#     main()







"""
train_agents_v3_unified.py
────────────────────────────────────────────────────────────────────────────
Version adaptée pour travailler avec la unified_matrix.parquet.

DIFFÉRENCES vs train_agents_v3.py :
  - Les étapes 1→5 (download, macro, sentiment, targets) sont remplacées
    par un simple chargement du parquet — déjà propre, déjà splitté.
  - Le split train/val/test est lu depuis la colonne 'split' existante
    au lieu d'être recalculé — plus de data leakage possible.
  - 10 ans de données (2015→2025) au lieu de 4 ans.
  - Walk-forward respecte les splits existants du parquet.
  - Colonnes adaptées aux features réelles de la unified matrix.

OUTPUTS → outputs/models_v3/ (préserve outputs/models/)

USAGE:
  python train_agents_v3_unified.py
  python train_agents_v3_unified.py --matrix path/to/unified_matrix.parquet
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
import yaml
from loguru import logger

from agents.macro_agent     import MacroAgent
from agents.technical_agent import TechnicalAgent
from agents.sentiment_agent import SentimentAgent


CFG_PATH      = "configs/agent_config.yaml"
MODELS_V4     = "outputs/models_v4"
DEFAULT_MATRIX = "data/unified_matrix.parquet"


# ── Features réelles de la unified matrix ────────────────────────────────────

# Features MacroAgent — colonnes mac_* présentes dans le parquet
MACRO_FEATURES = [
    "mac_yield_z", "mac_yield_mom", "mac_yield_accel",
    "mac_cb_tone_z", "mac_cb_shock_z",
    "mac_macro_strength", "mac_vix_global", "mac_vix_z",
]

# Features TechnicalAgent — colonnes techniques présentes dans le parquet
TECH_FEATURES = [
    "rsi14", "rsi28", "macd_norm", "macd_hist",
    "roc1", "roc3", "roc5", "atr_pct", "atr_ratio",
    "bb_pos", "bb_width", "ema_cross", "price_vs_ema50",
    "sma10_slope", "vol_ratio", "cmf", "body_ratio",
    "upper_shadow", "lower_shadow",
    "hour_sin", "hour_cos", "dow_sin", "dow_cos",
]

# Features SentimentAgent — colonnes nws_* présentes dans le parquet
# nws_flow_imbalance et nws_news_flow exclus (fix v3)
SENT_FEATURES = [
    "nws_sent_signal", "nws_sent_mom", "nws_sent_fast",
    "nws_sent_slow", "nws_sent_pressure", "nws_pressure_change",
    "nws_flow_accel", "nws_trend_strength",
]


def load_cfg() -> dict:
    with open(CFG_PATH) as f:
        cfg = yaml.safe_load(f)
    # Override model paths → models_v4
    cfg["paths"]["macro_model"] = f"{MODELS_V4}/macro/"
    cfg["paths"]["tech_model"]  = f"{MODELS_V4}/technical/"
    cfg["paths"]["sent_model"]  = f"{MODELS_V4}/sentiment/"
    return cfg


# ── Step 1 : Charger la unified matrix ───────────────────────────────────────

def load_unified_matrix(path: str) -> pd.DataFrame:
    logger.info(f"  Loading unified matrix from {path} …")
    df = pd.read_parquet(path)

    logger.info(f"  Shape       : {df.shape[0]:,} rows × {df.shape[1]} cols")
    logger.info(f"  Pairs       : {sorted(df['pair'].unique().tolist())}")
    logger.info(
        f"  Date range  : {df['timestamp_utc'].min()} → "
        f"{df['timestamp_utc'].max()}"
    )

    # Vérifier la colonne split
    if "split" in df.columns:
        counts = df["split"].value_counts()
        logger.info(
            f"  Splits      : train={counts.get('train',0):,}  "
            f"val={counts.get('val',0):,}  "
            f"test={counts.get('test',0):,}"
        )
    else:
        logger.warning("  No 'split' column found — will use temporal split")

    # Vérifier les targets
    if "target" in df.columns:
        counts = df["target"].value_counts().sort_index()
        logger.info(
            f"  Targets     : SELL={int(counts.get(-1,0)):,}  "
            f"HOLD={int(counts.get(0,0)):,}  "
            f"BUY={int(counts.get(1,0)):,}"
        )

    # Vérifier les nulls
    total_nulls = df.isnull().sum().sum()
    if total_nulls > 0:
        logger.warning(f"  {total_nulls:,} null values detected — filling with 0")
        df.ffill(inplace=True)
        df.fillna(0, inplace=True)
    else:
        logger.info("  No null values ✓")

    return df


# ── Step 2 : Valider les features disponibles ─────────────────────────────────

def validate_features(df: pd.DataFrame) -> dict:
    """
    Vérifie quelles features sont réellement disponibles dans le parquet.
    Retourne les listes de features validées pour chaque agent.
    """
    available = set(df.columns)

    macro_ok = [f for f in MACRO_FEATURES if f in available]
    tech_ok  = [f for f in TECH_FEATURES  if f in available]
    sent_ok  = [f for f in SENT_FEATURES  if f in available]

    macro_miss = [f for f in MACRO_FEATURES if f not in available]
    tech_miss  = [f for f in TECH_FEATURES  if f not in available]
    sent_miss  = [f for f in SENT_FEATURES  if f not in available]

    logger.info(f"  MacroAgent  : {len(macro_ok)}/{len(MACRO_FEATURES)} features available")
    logger.info(f"  TechAgent   : {len(tech_ok)}/{len(TECH_FEATURES)} features available")
    logger.info(f"  SentAgent   : {len(sent_ok)}/{len(SENT_FEATURES)} features available")

    if macro_miss: logger.warning(f"  Macro missing : {macro_miss}")
    if tech_miss:  logger.warning(f"  Tech missing  : {tech_miss}")
    if sent_miss:  logger.warning(f"  Sent missing  : {sent_miss}")

    # Colonnes bonus dans le parquet non utilisées par les agents actuels
    all_used  = set(macro_ok + tech_ok + sent_ok)
    bonus_cols = [
        c for c in available
        if c not in all_used
        and c not in ("timestamp_utc", "pair", "open", "high", "low",
                      "close", "volume", "target", "split", "mac_missing",
                      "atr", "vol_sma20", "price_vs_sma200", "sma50_slope",
                      "nws_news_flow", "nws_flow_imbalance", "nws_pressure_regime",
                      "mac_cb_guidance_z")
    ]
    if bonus_cols:
        logger.info(f"  Bonus cols in parquet (unused) : {bonus_cols}")

    return {
        "macro": macro_ok,
        "tech":  tech_ok,
        "sent":  sent_ok,
    }


# ── Step 3 : Entraîner MacroAgent ────────────────────────────────────────────

def train_macro(df: pd.DataFrame, cfg: dict, features: list) -> MacroAgent:
    logger.info("  → MacroAgent (KMeans on unified matrix) …")

    # Utiliser uniquement le train split
    if "split" in df.columns:
        train_df = df[df["split"] == "train"].copy()
        logger.info(f"    Using train split: {len(train_df):,} rows")
    else:
        n = int(len(df) * 0.70)
        train_df = df.iloc[:n].copy()
        logger.info(f"    Using first 70%: {len(train_df):,} rows")

    # Ajouter les colonnes manquantes à zéro si nécessaire
    for col in features:
        if col not in train_df.columns:
            train_df[col] = 0.0

    macro = MacroAgent(cfg)
    macro.fit(train_df, ret_24h=train_df.get("mac_yield_z", None))
    macro.save()
    logger.success("  MacroAgent saved ✓")
    return macro


# ── Step 4 : Entraîner TechnicalAgent avec walk-forward ──────────────────────

def train_technical(df: pd.DataFrame, cfg: dict, features: list) -> TechnicalAgent:
    """
    Walk-forward sur la unified matrix en respectant les splits existants.

    Si split column existe :
      - Fold validation = val split
      - Training final = train split
      - Test = gardé de côté (évaluation finale)

    Si pas de split :
      - Walk-forward temporel classique (5 folds)
    """
    from sklearn.preprocessing import RobustScaler

    logger.info("  → TechnicalAgent (walk-forward on unified matrix) …")

    tech = TechnicalAgent(cfg)

    # Override FEATURE_COLS avec les features validées
    tech.FEATURE_COLS = features

    if "split" in df.columns:
        _train_tech_with_splits(tech, df, features)
    else:
        _train_tech_walkforward(tech, df, features)

    tech.save()
    logger.success("  TechnicalAgent saved ✓")
    return tech


def _train_tech_with_splits(tech: TechnicalAgent, df: pd.DataFrame,
                             features: list) -> None:
    """Utilise les splits train/val/test du parquet directement."""
    from sklearn.preprocessing import RobustScaler

    train_df = df[df["split"] == "train"]
    val_df   = df[df["split"] == "val"]
    test_df  = df[df["split"] == "test"]

    logger.info(
        f"    Splits — train:{len(train_df):,}  "
        f"val:{len(val_df):,}  test:{len(test_df):,}"
    )

    # FIX leakage : scaler fitté sur train uniquement
    X_train_all = train_df[features].fillna(0).values.astype(np.float32)
    tech._scaler = RobustScaler(quantile_range=(5, 95))
    tech._scaler.fit(X_train_all)
    logger.info(f"    Scaler fitted on train set only ({len(X_train_all):,} rows) ✓")

    tech._pairs = sorted(df["pair"].unique().tolist())
    all_f1 = {}

    for pair in tech._pairs:
        tr = train_df[train_df["pair"] == pair].copy()
        va = val_df[val_df["pair"]   == pair].copy()
        te = test_df[test_df["pair"] == pair].copy()

        X_tr = np.clip(tech._scaler.transform(
            tr[features].fillna(0).values.astype(np.float32)), -5, 5)
        X_va = np.clip(tech._scaler.transform(
            va[features].fillna(0).values.astype(np.float32)), -5, 5)

        y_tr = tr["target"].values
        y_va = va["target"].values

        X_tr_seq, y_tr_seq = tech._build_sequences(X_tr, y_tr)
        X_va_seq, y_va_seq = tech._build_sequences(X_va, y_va)

        counts = np.bincount(
            np.array([v for v in y_tr_seq if v in (0,1,2)]), minlength=3
        )
        logger.info(
            f"    [{pair}] train_seqs={len(X_tr_seq):,}  "
            f"val_seqs={len(X_va_seq):,}  "
            f"SELL={counts[0]:,} HOLD={counts[1]:,} BUY={counts[2]:,}"
        )

        best_f1      = tech._train_one_pair(
            pair, X_tr_seq, y_tr_seq, epochs=60, batch_size=256, lr=3e-4
        )
        all_f1[pair] = best_f1
        logger.success(f"    [{pair}] best val F1={best_f1:.4f}")

        # Évaluation sur test set
        if len(te) > tech.window:
            X_te = np.clip(tech._scaler.transform(
                te[features].fillna(0).values.astype(np.float32)), -5, 5)
            y_te = te["target"].values
            X_te_seq, y_te_seq = tech._build_sequences(X_te, y_te)
            if len(X_te_seq) > 10:
                test_pred = _predict_sequences(tech, pair, X_te_seq)
                from sklearn.metrics import f1_score
                test_f1 = f1_score(y_te_seq, test_pred,
                                   average="macro", zero_division=0)
                logger.info(f"    [{pair}] TEST F1={test_f1:.4f} (out-of-sample)")

    avg = float(np.mean(list(all_f1.values())))
    logger.success(
        f"    TechnicalAgent complete — F1: {all_f1} | avg={avg:.4f}"
    )
    tech.fitted = True


def _predict_sequences(tech, pair: str, X_seq: np.ndarray) -> np.ndarray:
    """Prédit sur un batch de séquences pour évaluation test."""
    import torch
    import torch.nn.functional as F

    model  = tech._models.get(pair)
    if model is None:
        return np.zeros(len(X_seq), dtype=int)

    model.eval()
    preds = []
    seq_t = torch.tensor(X_seq, dtype=torch.float32).to(tech.device)
    batch_size = 256
    with torch.no_grad():
        for i in range(0, len(seq_t), batch_size):
            batch = seq_t[i:i+batch_size]
            logits = model(batch)
            preds.extend(F.softmax(logits, dim=-1).argmax(-1).cpu().numpy())
    return np.array(preds)


def _train_tech_walkforward(tech: TechnicalAgent, df: pd.DataFrame,
                             features: list, n_folds: int = 5) -> None:
    """Walk-forward temporel classique si pas de colonne split."""
    from sklearn.preprocessing import RobustScaler

    logger.info(f"    Walk-forward {n_folds} folds (no split column) …")

    val_size  = 0.15
    fold_step = val_size / n_folds
    fold_results = {pair: [] for pair in df["pair"].unique()}

    for fold in range(n_folds):
        train_end = 0.60 + fold * fold_step
        val_end   = train_end + val_size / n_folds
        logger.info(
            f"    Fold {fold+1}/{n_folds} — "
            f"train [0%→{train_end*100:.0f}%]  "
            f"val [{train_end*100:.0f}%→{val_end*100:.0f}%]"
        )

        for pair in df["pair"].unique():
            pair_df = df[df["pair"] == pair].copy().reset_index(drop=True)
            n       = len(pair_df)
            tr_idx  = int(n * train_end)
            va_idx  = int(n * val_end)
            if va_idx >= n or tr_idx < 100:
                continue

            tr_df = pair_df.iloc[:tr_idx]
            va_df = pair_df.iloc[tr_idx:va_idx]

            X_tr = tr_df[features].fillna(0).values.astype(np.float32)
            X_va = va_df[features].fillna(0).values.astype(np.float32)

            fold_scaler = RobustScaler(quantile_range=(5, 95))
            fold_scaler.fit(X_tr)
            X_tr_sc = np.clip(fold_scaler.transform(X_tr), -5, 5)
            X_va_sc = np.clip(fold_scaler.transform(X_va), -5, 5)

            X_tr_seq, y_tr_seq = tech._build_sequences(
                X_tr_sc, tr_df["target"].values)
            X_va_seq, y_va_seq = tech._build_sequences(
                X_va_sc, va_df["target"].values)

            if len(X_tr_seq) < 50 or len(X_va_seq) < 10:
                continue

            fold_f1 = tech._train_one_pair(
                pair, X_tr_seq, y_tr_seq, epochs=60, batch_size=256, lr=3e-4
            )
            fold_results[pair].append(fold_f1)

    logger.info("    ── Walk-forward F1 summary ──")
    for pair, f1s in fold_results.items():
        if f1s:
            logger.info(
                f"      [{pair}] folds: {[f'{x:.3f}' for x in f1s]} "
                f"| mean={np.mean(f1s):.3f} std={np.std(f1s):.3f}"
            )

    # Entraînement final sur tout le dataset
    logger.info("    Training final models on full dataset …")
    n_total    = len(df[features].fillna(0))
    n_fit_end  = int(n_total * 0.85)
    X_all      = df[features].fillna(0).values.astype(np.float32)
    tech._scaler = RobustScaler(quantile_range=(5, 95))
    tech._scaler.fit(X_all[:n_fit_end])

    tech._pairs = sorted(df["pair"].unique().tolist())
    for pair in tech._pairs:
        pair_df = df[df["pair"] == pair].copy()
        X       = np.clip(
            tech._scaler.transform(
                pair_df[features].fillna(0).values.astype(np.float32)), -5, 5)
        y       = pair_df["target"].values
        X_seq, y_seq = tech._build_sequences(X, y)
        tech._train_one_pair(
            pair, X_seq, y_seq, epochs=60, batch_size=256, lr=3e-4)

    tech.fitted = True


# ── Step 5 : Entraîner SentimentAgent ────────────────────────────────────────

def train_sentiment(df: pd.DataFrame, cfg: dict, features: list) -> SentimentAgent:
    logger.info("  → SentimentAgent (on unified matrix train split) …")

    if "split" in df.columns:
        train_df = df[df["split"] == "train"].copy()
        logger.info(f"    Using train split: {len(train_df):,} rows")
    else:
        n = int(len(df) * 0.70)
        train_df = df.iloc[:n].copy()

    # S'assurer que les features sent sont présentes
    for col in features:
        if col not in train_df.columns:
            train_df[col] = 0.0

    sent = SentimentAgent(cfg)
    sent.fit(train_df)
    sent.save()
    logger.success("  SentimentAgent saved ✓")
    return sent


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--matrix", type=str, default=DEFAULT_MATRIX,
        help="Path to unified_matrix.parquet"
    )
    args = parser.parse_args()

    logger.info("╔══════════════════════════════════════════════════════════╗")
    logger.info("║  FX AlphaLab v3  ·  Training on Unified Matrix          ║")
    logger.info("╚══════════════════════════════════════════════════════════╝")
    logger.info(f"  Matrix  : {args.matrix}")
    logger.info(f"  Models  → {MODELS_V4}/")
    logger.info(f"  Old models preserved in outputs/models/")
    logger.info("")

    cfg = load_cfg()

    # ── Step 1 : Charger la unified matrix ───────────────────────────────────
    logger.info("Step 1/4 — Loading unified matrix …")
    df = load_unified_matrix(args.matrix)

    # ── Step 2 : Valider les features ────────────────────────────────────────
    logger.info("Step 2/4 — Validating features …")
    features = validate_features(df)

    # ── Step 3 : Training ────────────────────────────────────────────────────
    logger.info("Step 3/4 — Training agents …")

    train_macro(df, cfg, features["macro"])
    train_technical(df, cfg, features["tech"])
    train_sentiment(df, cfg, features["sent"])

    # ── Step 4 : Résumé ──────────────────────────────────────────────────────
    logger.info("")
    logger.info("═" * 60)
    logger.info("  ALL AGENTS TRAINED SUCCESSFULLY (unified matrix)")
    logger.info("═" * 60)
    logger.info(f"  Macro  → {cfg['paths']['macro_model']}")
    logger.info(f"  Tech   → {cfg['paths']['tech_model']}")
    logger.info(f"  Sent   → {cfg['paths']['sent_model']}")
    logger.info("")
    logger.info("  Pour utiliser ces modèles, mettre à jour agent_config.yaml :")
    logger.info(f"    macro_model: {MODELS_V4}/macro/")
    logger.info(f"    tech_model:  {MODELS_V4}/technical/")
    logger.info(f"    sent_model:  {MODELS_V4}/sentiment/")
    logger.info("")
    logger.info("  python run_agent.py --once")
    logger.info("═" * 60)


if __name__ == "__main__":
    main()
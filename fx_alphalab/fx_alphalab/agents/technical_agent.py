"""
agents/technical_agent.py
────────────────────────────────────────────────────────────────────────────
Technical Agent — per-pair TCN+LSTM models.

FIX: One model per currency pair instead of one pooled model.
  EURUSD/GBPUSD/USDJPY have different volatility, session patterns,
  and momentum dynamics. Pooling averages them out → F1~0.37.
  Per-pair models expected → F1~0.42-0.48 per pair.

  Shared RobustScaler (fitted on all pairs for robust statistics).
  Separate _TechNet weights per pair, saved as tech_model_EURUSD.pt etc.
"""
from __future__ import annotations

import math
import pickle
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from loguru import logger
from sklearn.metrics import f1_score
from sklearn.preprocessing import RobustScaler
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler


class _TCNBlock(nn.Module):
    def __init__(self, in_ch, out_ch, kernel=3, dilation=1, dropout=0.1):
        super().__init__()
        pad = (kernel - 1) * dilation
        self.conv = nn.Conv1d(in_ch, out_ch, kernel, dilation=dilation, padding=pad)
        self.norm = nn.LayerNorm(out_ch)
        self.drop = nn.Dropout(dropout)
        self.res  = nn.Conv1d(in_ch, out_ch, 1) if in_ch != out_ch else nn.Identity()

    def forward(self, x):
        pad = self.conv.padding[0]
        out = self.conv(x)
        if pad > 0:
            out = out[:, :, :-pad]
        out = self.norm(out.transpose(1, 2)).transpose(1, 2)
        return self.drop(F.gelu(out)) + self.res(x)


class _TechNet(nn.Module):
    def __init__(self, input_dim: int, hidden: int = 64,
                 tcn_ch: int = 32, dropout: float = 0.2):
        super().__init__()
        self.lstm = nn.LSTM(input_dim, hidden, num_layers=2,
                            batch_first=True, dropout=dropout)
        self.tcn = nn.Sequential(
            _TCNBlock(input_dim, tcn_ch, dilation=1, dropout=dropout),
            _TCNBlock(tcn_ch,    tcn_ch, dilation=2, dropout=dropout),
            _TCNBlock(tcn_ch,    tcn_ch, dilation=4, dropout=dropout),
        )
        self.pool = nn.AdaptiveAvgPool1d(1)
        self.head = nn.Sequential(
            nn.Linear(hidden + tcn_ch, hidden),
            nn.LayerNorm(hidden), nn.GELU(), nn.Dropout(dropout),
            nn.Linear(hidden, 3),
        )

    def forward(self, x, mc_dropout=False):
        if mc_dropout:
            self.train()
        lstm_out, _ = self.lstm(x)
        b1 = lstm_out[:, -1, :]
        b2 = self.pool(self.tcn(x.transpose(1, 2))).squeeze(-1)
        return self.head(torch.cat([b1, b2], dim=-1))


class _TechDataset(Dataset):
    def __init__(self, X: np.ndarray, y: np.ndarray):
        self.X = torch.tensor(X, dtype=torch.float32)
        self.y = torch.tensor(y, dtype=torch.long)

    def __len__(self): return len(self.X)
    def __getitem__(self, i): return self.X[i], self.y[i]

    def make_sampler(self):
        counts  = np.bincount(self.y.numpy(), minlength=3)
        weights = 1.0 / np.maximum(counts, 1)
        sw      = weights[self.y.numpy()]
        return WeightedRandomSampler(
            torch.from_numpy(sw).float(), len(self), replacement=True
        )


TARGET_MAP = {-1: 0, 0: 1, 1: 2}


def _lr_schedule(optim, epoch, warmup, total, base_lr, min_lr=1e-6):
    if epoch < warmup:
        lr = base_lr * (epoch + 1) / warmup
    else:
        p  = (epoch - warmup) / max(total - warmup, 1)
        lr = min_lr + 0.5 * (base_lr - min_lr) * (1 + math.cos(math.pi * p))
    for pg in optim.param_groups:
        pg["lr"] = lr
    return lr


class TechnicalAgent:

    FEATURE_COLS = [
        "rsi14", "rsi28", "macd_norm", "macd_hist",
        "roc1", "roc3", "roc5", "atr_pct", "atr_ratio",
        "bb_pos", "bb_width", "ema_cross", "price_vs_ema50",
        "sma10_slope", "vol_ratio", "cmf", "body_ratio",
        "upper_shadow", "lower_shadow",
        "hour_sin", "hour_cos", "dow_sin", "dow_cos",
    ]

    def __init__(self, cfg: dict):
        tc = cfg["technical"]
        self.window    = tc["window_bars"]
        self.hidden    = tc["hidden"]
        self.dropout   = tc["dropout"]
        self.model_dir = Path(cfg["paths"]["tech_model"])
        self.device    = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._models:  Dict[str, _TechNet]    = {}
        self._scaler:  Optional[RobustScaler] = None
        self._pairs:   List[str]              = []
        self.fitted    = False

    def _build_sequences(self, X: np.ndarray, y: np.ndarray
                         ) -> Tuple[np.ndarray, np.ndarray]:
        Xs, ys = [], []
        for i in range(self.window, len(X)):
            t = int(y[i])
            if t not in TARGET_MAP:
                continue
            Xs.append(X[i - self.window: i])
            ys.append(TARGET_MAP[t])
        return np.array(Xs, dtype=np.float32), np.array(ys, dtype=np.int64)

    def _train_one_pair(self, pair: str, X_seq: np.ndarray, y_seq: np.ndarray,
                        epochs: int, batch_size: int, lr: float) -> float:
        n_val        = max(int(len(X_seq) * 0.15), 1)
        X_tr, X_va   = X_seq[:-n_val], X_seq[-n_val:]
        y_tr, y_va   = y_seq[:-n_val], y_seq[-n_val:]

        tr_ds = _TechDataset(X_tr, y_tr)
        va_ds = _TechDataset(X_va, y_va)
        tr_ld = DataLoader(tr_ds, batch_size=batch_size, sampler=tr_ds.make_sampler())
        va_ld = DataLoader(va_ds, batch_size=batch_size, shuffle=False)

        input_dim    = X_seq.shape[-1]
        model        = _TechNet(input_dim, self.hidden, dropout=self.dropout).to(self.device)
        optim        = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
        use_amp      = self.device.type == "cuda"
        amp_scaler   = torch.cuda.amp.GradScaler(enabled=use_amp)

        warmup       = 5
        patience_max = 15
        best_f1      = 0.0
        patience     = 0
        best_path    = self.model_dir / f"tech_best_{pair}.pt"
        self.model_dir.mkdir(parents=True, exist_ok=True)

        for ep in range(1, epochs + 1):
            _lr_schedule(optim, ep - 1, warmup, epochs, lr)
            model.train()
            for xb, yb in tr_ld:
                xb, yb = xb.to(self.device), yb.to(self.device)
                optim.zero_grad()
                with torch.cuda.amp.autocast(enabled=use_amp):
                    loss = F.cross_entropy(model(xb), yb, label_smoothing=0.1)
                amp_scaler.scale(loss).backward()
                nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                amp_scaler.step(optim)
                amp_scaler.update()

            model.eval()
            preds, labels = [], []
            with torch.no_grad():
                for xb, yb in va_ld:
                    preds.extend(model(xb.to(self.device)).argmax(-1).cpu().numpy())
                    labels.extend(yb.numpy())
            f1 = f1_score(labels, preds, average="macro", zero_division=0)

            if ep % 10 == 0 or ep == 1 or ep <= warmup:
                logger.info(f"    [{pair}] ep {ep}/{epochs} | val F1={f1:.4f}")

            if f1 > best_f1:
                best_f1  = f1
                patience = 0
                torch.save(model.state_dict(), best_path)
            else:
                patience += 1
                if patience >= patience_max and ep > warmup:
                    logger.info(f"    [{pair}] early stop ep={ep}, best F1={best_f1:.4f}")
                    break

        model.load_state_dict(torch.load(best_path, map_location=self.device))
        model.eval()
        self._models[pair] = model
        return best_f1

    def fit(self, df: pd.DataFrame, epochs: int = 60,
            batch_size: int = 256, lr: float = 3e-4) -> "TechnicalAgent":
        logger.info("TechnicalAgent.fit() — per-pair models …")

        present = [c for c in self.FEATURE_COLS if c in df.columns]
        if len(present) < 10:
            raise ValueError(f"Too few features: {present}")
        if "target" not in df.columns:
            raise ValueError("df must have 'target' column")

        # Shared scaler — fit on all pairs
        X_all = df[present].fillna(0).values.astype(np.float32)
        self._scaler = RobustScaler(quantile_range=(5, 95))
        self._scaler.fit(X_all)
        logger.info(f"  Shared scaler fitted on {len(X_all):,} rows (all pairs)")

        self._pairs = sorted(df["pair"].unique().tolist())
        logger.info(f"  Pairs to train: {self._pairs} | device: {self.device}")

        all_f1 = {}
        for pair in self._pairs:
            pair_df = df[df["pair"] == pair].copy()
            X_raw   = pair_df[present].fillna(0).values.astype(np.float32)
            X       = np.clip(self._scaler.transform(X_raw), -5, 5)
            y       = pair_df["target"].values
            X_seq, y_seq = self._build_sequences(X, y)

            counts = np.bincount(y_seq, minlength=3)
            logger.info(
                f"  [{pair}] seqs={len(X_seq):,} | "
                f"SELL={counts[0]} HOLD={counts[1]} BUY={counts[2]}"
            )
            best_f1      = self._train_one_pair(pair, X_seq, y_seq, epochs, batch_size, lr)
            all_f1[pair] = best_f1
            logger.success(f"  [{pair}] best F1={best_f1:.4f}")

        self.fitted = True
        avg = float(np.mean(list(all_f1.values())))
        logger.success(
            f"TechnicalAgent.fit() complete. F1 per pair: {all_f1} | avg={avg:.4f}"
        )
        return self

    def predict_live(self, df: pd.DataFrame, mc_passes: int = 10) -> Dict:
        if not self.fitted:
            raise RuntimeError("TechnicalAgent not fitted.")

        # Pick pair-specific model
        pair = df["pair"].iloc[-1] if "pair" in df.columns else None
        if pair not in self._models:
            pair = next(iter(self._models), None)
        if pair is None:
            return {"direction": 0, "p_buy": 0.33, "p_hold": 0.34,
                    "p_sell": 0.33, "confidence": 0.0, "uncertainty": 1.0, "signal": "HOLD"}

        model   = self._models[pair]
        present = [c for c in self.FEATURE_COLS if c in df.columns]
        X       = np.clip(
            self._scaler.transform(df[present].fillna(0).values.astype(np.float32)),
            -5, 5
        )
        if len(X) < self.window:
            return {"direction": 0, "p_buy": 0.33, "p_hold": 0.34,
                    "p_sell": 0.33, "confidence": 0.0, "uncertainty": 1.0, "signal": "HOLD"}

        seq = torch.tensor(X[-self.window:][np.newaxis], dtype=torch.float32).to(self.device)
        pass_probs = []
        with torch.no_grad():
            for _ in range(mc_passes):
                p = F.softmax(model(seq, mc_dropout=True), dim=-1)
                pass_probs.append(p.cpu().numpy()[0])

        arr         = np.stack(pass_probs)
        probs_mean  = arr.mean(0)
        uncertainty = float(arr.std(0).mean())
        p_sell, p_hold, p_buy = probs_mean
        direction  = 1 if p_buy > p_sell else (-1 if p_sell > p_buy else 0)
        confidence = float(max(p_buy, p_sell) - p_hold)
        signal     = "BUY" if direction == 1 else ("SELL" if direction == -1 else "HOLD")

        return {
            "direction":   direction,
            "p_buy":       float(p_buy),
            "p_hold":      float(p_hold),
            "p_sell":      float(p_sell),
            "confidence":  confidence,
            "uncertainty": uncertainty,
            "signal":      signal,
        }

    def save(self) -> None:
        self.model_dir.mkdir(parents=True, exist_ok=True)
        with open(self.model_dir / "tech_scaler.pkl", "wb") as f:
            pickle.dump({"scaler": self._scaler, "pairs": self._pairs}, f)
        for pair, model in self._models.items():
            torch.save(model.state_dict(), self.model_dir / f"tech_model_{pair}.pt")
        logger.success(
            f"TechnicalAgent saved → {self.model_dir} ({len(self._models)} models)"
        )

    def load(self) -> "TechnicalAgent":
        with open(self.model_dir / "tech_scaler.pkl", "rb") as f:
            state = pickle.load(f)
        self._scaler = state["scaler"]
        self._pairs  = state["pairs"]
        input_dim    = len(self.FEATURE_COLS)
        for pair in self._pairs:
            path = self.model_dir / f"tech_model_{pair}.pt"
            if not path.exists():
                logger.warning(f"Missing model file: {path}")
                continue
            m = _TechNet(input_dim, self.hidden, dropout=self.dropout).to(self.device)
            m.load_state_dict(torch.load(path, map_location=self.device))
            m.eval()
            self._models[pair] = m
        self.fitted = len(self._models) > 0
        logger.info(
            f"TechnicalAgent loaded — {len(self._models)} pair models: "
            f"{list(self._models.keys())}"
        )
        return self
"""
memory/context_store.py
────────────────────────────────────────────────────────────────────────────
Rolling context window — stores the last N signals per pair.
The LLM reads this as part of its context window so it can
reason about trends in its own past decisions.
"""
from __future__ import annotations

import json
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class ContextStore:
    """
    Stores last N signals per pair. Persists to disk between runs.
    """

    def __init__(self, max_signals: int = 24, path: str = "outputs/context.json"):
        self.max_signals = max_signals
        self.path        = Path(path)
        self._store: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=self.max_signals)
        )
        self._load()

    def add(self, pair: str, signal: Dict) -> None:
        self._store[pair].append(signal)
        self._save()

    def get_recent(self, pair: str, n: int = 5) -> List[Dict]:
        """Return the last n signals for a pair."""
        signals = list(self._store[pair])
        return signals[-n:]

    def get_summary(self, pair: str) -> str:
        """Return a compact text summary of recent signals for the LLM."""
        recent = self.get_recent(pair, 5)
        if not recent:
            return f"No prior signals for {pair}."
        lines = [f"Last {len(recent)} signals for {pair}:"]
        for s in recent:
            ts  = s.get("timestamp", "")[:16]
            dir = s.get("direction", "?")
            conf = s.get("confidence", 0)
            lines.append(f"  {ts}  {dir:<5} conf={conf:.2f}")
        return "\n".join(lines)

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {pair: list(q) for pair, q in self._store.items()}
        with open(self.path, "w") as f:
            json.dump(data, f, default=str, indent=2)

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            with open(self.path) as f:
                data = json.load(f)
            for pair, signals in data.items():
                self._store[pair] = deque(signals, maxlen=self.max_signals)
        except Exception:
            pass
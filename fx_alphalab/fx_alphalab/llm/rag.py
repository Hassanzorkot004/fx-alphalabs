"""
llm/rag.py
────────────────────────────────────────────────────────────────────────────
Advanced RAG for AlphaBot — persistent, multi-source context retrieval.

Indexes:
  1. Signal history (last N per pair) — for "what's the signal" queries
  2. Macro context snapshots — for "what's the regime" queries
  3. Strategy documentation — for "how does this work" queries

Persistence: ChromaDB stored on disk. Embedding model cached by HuggingFace.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import chromadb
from chromadb.utils import embedding_functions
from loguru import logger

from fx_alphalab.llm.client import get_llm_client, MODEL

# ── Constants ─────────────────────────────────────────────────────────────────

MAX_SIGNALS_PER_PAIR = 50
TOP_K = 8

# Default persist directory — project root / data / chromadb
DEFAULT_PERSIST_DIR = Path(__file__).parent.parent.parent / "data" / "chromadb"

# Strategy doc
STRATEGY_DOC = """
FX AlphaLab v2 Trading System Overview:

ARCHITECTURE: Three specialist ML agents + LLM orchestrator fusion.
- MacroAgent: KMeans clustering on yield curve, VIX, CB tone features.
  Detects market regime: bullish, neutral, or bearish.
- TechnicalAgent: Per-pair TCN+LSTM neural networks trained on 48-bar windows
  of technical indicators (RSI, MACD, ATR, Bollinger, EMA cross, etc).
- SentimentAgent: Lexical scoring + logistic regression calibrator on news flow.
  Handles low-news conditions by outputting HOLD.
- Orchestrator: LLM (Llama 3.1 70B) agentic loop that calls all three models
  as tools, synthesizes outputs, and produces final BUY/SELL/HOLD with reasoning.

SIGNAL GENERATION:
1. Every hour, all three models run on latest data
2. LLM calls each model as a tool via function calling
3. Direction determined by weighted vote:
   - Technical (primary, weight 1.5)
   - Sentiment (confirmation, weight 1.0)
   - Macro (backdrop, weight 0.4)
4. Confidence computed deterministically from agreement pattern
5. Fallback: rule-based direction if LLM unavailable

PAIRS TRADED: EURUSD, GBPUSD, USDJPY

KEY FEATURES:
- yield_z: Yield curve steepness (10Y-2Y spread Z-score). >0 = steepening (USD bullish).
- VIX: Volatility index. Rising = risk-off.
- pair_carry_signal: Pair-specific yield differential.
- Macro regime gates: if cluster label conflicts with absolute yield_z thresholds,
  regime is overridden to neutral.
"""


class AlphaBotRAG:
    """Multi-source RAG store with persistent storage."""

    def __init__(self, persist_dir: Optional[str] = None):
        """
        Args:
            persist_dir: Directory for ChromaDB storage.
                        Defaults to fx_alphalab/data/chromadb/
                        Use None for in-memory (testing only).
        """
        if persist_dir is None:
            # Default: persistent storage in project data dir
            persist_dir = str(DEFAULT_PERSIST_DIR)

        os.makedirs(persist_dir, exist_ok=True)

        self.client = chromadb.PersistentClient(path=persist_dir)
        logger.info(f"AlphaBotRAG: persistent storage at {persist_dir}")

        # Embedding model — downloaded once, cached by HuggingFace
        # Set HF_HOME env var to control cache location if needed
        try:
            self.ef = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="all-MiniLM-L6-v2"
            )
            logger.info("AlphaBotRAG: embedding model loaded (all-MiniLM-L6-v2)")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise

        # Three collections
        self.signals_coll = self.client.get_or_create_collection(
            name="alphalab_signals",
            embedding_function=self.ef,
        )
        self.macro_coll = self.client.get_or_create_collection(
            name="alphalab_macro",
            embedding_function=self.ef,
        )
        self.docs_coll = self.client.get_or_create_collection(
            name="alphalab_docs",
            embedding_function=self.ef,
        )

        # Index strategy doc (only if not already indexed)
        self._index_strategy_doc()

        logger.info(
            f"AlphaBotRAG ready — "
            f"signals: {self.signals_coll.count()}, "
            f"macro: {self.macro_coll.count()}, "
            f"docs: {self.docs_coll.count()}"
        )

    def _index_strategy_doc(self) -> None:
        """Index the strategy documentation (idempotent)."""
        existing = self.docs_coll.get(ids=["strategy_doc_v2"])
        if not existing["ids"]:
            self.docs_coll.add(
                documents=[STRATEGY_DOC],
                ids=["strategy_doc_v2"],
            )
            logger.info("  Strategy doc indexed")

    # ── Indexing ──────────────────────────────────────────────────────────────

    def index_signal(self, signal: dict) -> None:
        """Index a full signal with metadata."""
        pair = signal.get("pair", "unknown")
        doc = self._signal_to_doc(signal)
        doc_id = f"{pair}_{signal.get('timestamp', datetime.now(timezone.utc).isoformat())}"

        metadata = {
            "pair": pair,
            "direction": signal.get("direction", "HOLD"),
            "confidence": float(signal.get("confidence", 0)),
            "regime": signal.get("macro_regime", "unknown"),
        }

        self.signals_coll.add(documents=[doc], metadatas=[metadata], ids=[doc_id])

        # Prune if over limit
        self._prune_pair(pair)

    def index_macro_snapshot(self, macro_features: dict, regime: str, timestamp: str) -> None:
        """Index a macro context snapshot."""
        doc = (
            f"MACRO {timestamp}: regime={regime} "
            f"yield_z={macro_features.get('mac_yield_z', 0):.3f} "
            f"macro_strength={macro_features.get('mac_macro_strength', 0):.3f} "
            f"vix_z={macro_features.get('mac_vix_z', 0):.3f} "
            f"vix_global={macro_features.get('mac_vix_global', 0):.1f} "
            f"cb_tone_z={macro_features.get('mac_cb_tone_z', 0):.3f} "
            f"pair_carry={macro_features.get('pair_carry_signal', 0):.3f}"
        )
        self.macro_coll.add(
            documents=[doc],
            metadatas=[{"regime": regime, "timestamp": timestamp}],
            ids=[f"macro_{timestamp}"],
        )
        self._prune_collection(self.macro_coll, keep=100)

    def index_batch(self, signals: List[dict]) -> None:
        """Index multiple signals (startup loading)."""
        if not signals:
            return
        docs, metadatas, ids = [], [], []
        for s in signals:
            pair = s.get("pair", "unknown")
            docs.append(self._signal_to_doc(s))
            metadatas.append({
                "pair": pair,
                "direction": s.get("direction", "HOLD"),
                "confidence": float(s.get("confidence", 0)),
                "regime": s.get("macro_regime", "unknown"),
            })
            ids.append(f"{pair}_{s.get('timestamp', datetime.now(timezone.utc).isoformat())}")
        self.signals_coll.add(documents=docs, metadatas=metadatas, ids=ids)
        logger.info(f"  RAG batch indexed {len(signals)} signals")
        for pair in set(s.get("pair", "unknown") for s in signals):
            self._prune_pair(pair)

    # ── Retrieval ─────────────────────────────────────────────────────────────

    def retrieve(self, query: str, n: int = TOP_K) -> List[str]:
        """Multi-collection retrieval with pair detection."""
        pair_filter = self._detect_pair(query)

        signal_results = self.signals_coll.query(
            query_texts=[query], n_results=n,
            where={"pair": pair_filter} if pair_filter else None,
        )
        macro_results = self.macro_coll.query(query_texts=[query], n_results=3)
        doc_results = self.docs_coll.query(query_texts=[query], n_results=2)

        all_docs = (
            signal_results.get("documents", [[]])[0] +
            macro_results.get("documents", [[]])[0] +
            doc_results.get("documents", [[]])[0]
        )

        # Deduplicate
        seen = set()
        unique = []
        for d in all_docs:
            if d not in seen:
                seen.add(d)
                unique.append(d)

        return unique[:n]

    def retrieve_by_pair(self, pair: str, n: int = 10) -> List[str]:
        """Get recent signals for a pair."""
        results = self.signals_coll.query(
            query_texts=[f"{pair} signal direction"], n_results=n,
            where={"pair": pair.upper()},
        )
        return results.get("documents", [[]])[0]

    def retrieve_latest(self, n: int = 10) -> List[str]:
        """Get most recent signals across all pairs."""
        results = self.signals_coll.query(
            query_texts=["latest signals"], n_results=n,
        )
        return results.get("documents", [[]])[0]

    # ── Chat ──────────────────────────────────────────────────────────────────

    CHAT_PROMPT = """You are AlphaBot, the senior FX analyst for FX AlphaLab — an institutional-grade trading signal system.

    You have 20 years of experience trading EUR/USD, GBP/USD, and USD/JPY. You combine macroeconomics, technical analysis, and sentiment analysis to explain trading signals.

    YOUR VOICE:
    - Confident, direct, and insightful — like a seasoned hedge fund strategist
    - Use specific numbers and values from the context
    - Explain the WHY behind every signal, not just what it is
    - Connect macro events to their FX impact with clear causal chains
    - When agents disagree, explain the tension and who is likely right
    - Use phrases like "The key insight here is...", "What makes this interesting...", "The risk to watch is..."

    WHEN EXPLAINING A DIRECTION:
    1. State the direction and confidence clearly
    2. Explain which agents agree/disagree and why
    3. Connect to current macro regime (yield_z, VIX, carry)
    4. Mention specific technical levels or patterns
    5. Note the sentiment backdrop (news flow, article count)
    6. Identify the key driver
    7. State the main risk
    8. Give trade levels if available (entry zone, stop, target)

    WHEN EXPLAINING A NEWS EVENT'S IMPACT:
    - Explain the asset's typical reaction to this type of data
    - Connect to current positioning and regime
    - Give both the baseline scenario and the surprise scenario
    - Mention which currency pairs are most affected
    - Reference similar historical patterns if relevant

    WHEN EXPLAINING WHY A SIGNAL CHANGED:
    - Compare the current and previous signal
    - Identify which agent(s) flipped and why
    - Connect to the specific data change (yield move, RSI cross, news spike)
    - Explain the confidence implications

    GENERAL RULES:
    - Base answers ONLY on the provided context
    - If context lacks specific data, say so clearly and offer what you CAN infer
    - Structure longer answers with clear sections
    - Never invent numbers
    - If the signal is HOLD, explain the conflict or uncertainty honestly
    - Mention if this is an LLM-generated or rule-based signal

    CONTEXT FROM RECENT SIGNALS AND MARKET DATA:
    {context}"""

    def chat(self, user_query: str) -> str:
        """Full RAG chat pipeline."""
        context_docs = self._smart_retrieve(user_query)
        context = "\n\n".join(f"[{i+1}] {d}" for i, d in enumerate(context_docs)) if context_docs else "No data available."

        llm = get_llm_client()
        response = llm.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": self.CHAT_PROMPT.format(context=context)},
                {"role": "user", "content": user_query},
            ],
            max_tokens=500,
            temperature=0.3,
        )
        return response.choices[0].message.content

    def _smart_retrieve(self, query: str) -> List[str]:
        """Detect intent and weight retrieval sources accordingly."""
        q = query.lower()

        # Strategy/how-to questions
        if any(w in q for w in ["how", "work", "architecture", "strategy", "system", "model", "agent"]):
            sig = self.retrieve(query, n=3)
            doc = self.docs_coll.query(query_texts=[query], n_results=3).get("documents", [[]])[0]
            return doc + sig

        # News/event impact questions
        if any(w in q for w in ["news", "article", "headline", "impact", "event", "data", "pmi", "nfp", "cpi", "gdp", "fed", "ecb", "boe", "boj", "jolts", "ism", "jobs", "inflation"]):
            sig = self.retrieve(query, n=5)
            mac = self.macro_coll.query(query_texts=[query], n_results=3).get("documents", [[]])[0]
            doc = self.docs_coll.query(query_texts=[query], n_results=2).get("documents", [[]])[0]
            return sig + mac + doc

        # Macro/regime questions
        if any(w in q for w in ["macro", "regime", "yield", "vix", "economy", "central bank"]):
            sig = self.retrieve(query, n=3)
            mac = self.macro_coll.query(query_texts=[query], n_results=5).get("documents", [[]])[0]
            return mac + sig

        # History/evolution questions
        if any(w in q for w in ["history", "past", "previous", "evolution", "trend", "before", "changed", "flip"]):
            return self.retrieve(query, n=TOP_K * 2)[:TOP_K]

        # Trade levels / execution questions
        if any(w in q for w in ["entry", "stop", "target", "level", "trade", "position", "size", "risk"]):
            return self.retrieve(query, n=TOP_K)

        # Default: balanced retrieval
        return self.retrieve(query, n=TOP_K)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _signal_to_doc(self, s: dict) -> str:
        return (
            f"SIGNAL: {s.get('pair', '???')} | Dir: {s.get('direction', 'HOLD')} | "
            f"Conf: {s.get('confidence', 0):.3f} | Size: {s.get('position_size', 0):.2f} | "
            f"Regime: {s.get('macro_regime', 'unknown')} | "
            f"Tech: {s.get('tech_signal', '?')} | Sent: {s.get('sent_signal', '?')} | "
            f"Agreement: {s.get('agent_agreement', '?')} | "
            f"Key: {s.get('key_driver', '?')} | Risk: {s.get('risk_note', '?')} | "
            f"Reason: {s.get('reasoning', '')} | Time: {s.get('timestamp', '?')}"
        )

    def _detect_pair(self, query: str) -> Optional[str]:
        q = query.lower()
        for pair in ["eurusd", "gbpusd", "usdjpy"]:
            if pair in q:
                return pair.upper()
        return None

    def _prune_pair(self, pair: str) -> None:
        results = self.signals_coll.get(where={"pair": pair})
        if results["ids"] and len(results["ids"]) > MAX_SIGNALS_PER_PAIR:
            sorted_ids = sorted(results["ids"])
            remove = sorted_ids[:len(sorted_ids) - MAX_SIGNALS_PER_PAIR]
            self.signals_coll.delete(ids=remove)

    def _prune_collection(self, coll, keep: int) -> None:
        results = coll.get()
        if results["ids"] and len(results["ids"]) > keep:
            sorted_ids = sorted(results["ids"], reverse=True)
            coll.delete(ids=sorted_ids[keep:])

    @property
    def count(self) -> int:
        return self.signals_coll.count()

    def get_stats(self) -> dict:
        """Collection statistics."""
        signals = self.signals_coll.get()
        pairs, directions = set(), {"BUY": 0, "SELL": 0, "HOLD": 0}
        for m in signals.get("metadatas", []):
            if m:
                pairs.add(m.get("pair", ""))
                directions[m.get("direction", "HOLD")] += 1
        return {
            "total_signals": self.signals_coll.count(),
            "macro_snapshots": self.macro_coll.count(),
            "docs_indexed": self.docs_coll.count(),
            "pairs": sorted(list(pairs)),
            "direction_distribution": directions,
        }


# ── Self-test ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("🧪 Testing AlphaBotRAG")
    print("=" * 60)

    rag = AlphaBotRAG()

    # Index test data
    rag.index_signal({
        "pair": "EURUSD", "direction": "BUY", "confidence": 0.72,
        "position_size": 0.56, "macro_regime": "bullish",
        "tech_signal": "BUY", "sent_signal": "BUY",
        "agent_agreement": "FULL", "key_driver": "TECHNICAL",
        "risk_note": "ECB speech risk",
        "reasoning": "Tech+sent agree, yield_z=+0.35 steepening.",
        "timestamp": "2024-05-04T10:00:00Z",
    })

    print(f"\n📊 Stats: {rag.get_stats()}")
    print(f"✅ RAG ready. Persistent storage: {DEFAULT_PERSIST_DIR}")
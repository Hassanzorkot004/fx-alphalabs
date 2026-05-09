"""
data_feed/news_rag.py
────────────────────────────────────────────────────────────────────────────
Rolling News RAG (Retrieval-Augmented Generation)

Maintains an in-memory vector store of recent news articles.
At signal generation time, retrieves the most semantically relevant
articles for a given pair + market context query.

This replaces the naive "pass 5 RSS headlines to LLM" approach with
targeted retrieval — the LLM gets the articles most relevant to the
current signal context, not just the 5 most recent ones.

ARCHITECTURE:
  - Vector store: ChromaDB (in-memory, no persistence needed)
  - Embeddings: sentence-transformers (all-MiniLM-L6-v2, 22MB, fast)
  - Fallback: keyword scoring if sentence-transformers unavailable
  - Rolling window: keeps last 72h of articles, auto-expires older ones
  - Per-pair collections: EURUSD, GBPUSD, USDJPY + shared global

USAGE:
  rag = NewsRAG()
  rag.ingest(articles)                          # add new articles
  hits = rag.retrieve("EURUSD", query, top_k=5) # get relevant ones
"""
from __future__ import annotations

import hashlib
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from loguru import logger

# ── Optional dependencies ─────────────────────────────────────────────────────

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False
    logger.warning("chromadb not installed — RAG will use keyword fallback")

try:
    from sentence_transformers import SentenceTransformer
    ST_AVAILABLE = True
except ImportError:
    ST_AVAILABLE = False
    logger.warning("sentence-transformers not installed — RAG will use keyword fallback")


# ── Keyword fallback scorer ───────────────────────────────────────────────────

PAIR_KEYWORDS = {
    "EURUSD": ["euro", "eur", "ecb", "eurozone", "lagarde", "european"],
    "GBPUSD": ["pound", "sterling", "boe", "bank of england", "bailey", "britain"],
    "USDJPY": ["yen", "jpy", "boj", "bank of japan", "ueda", "japan"],
    "GLOBAL": ["dollar", "usd", "fed", "federal reserve", "powell", "fomc",
               "inflation", "cpi", "interest rate", "gdp", "yield", "treasury"],
}


def _keyword_score(text: str, pair: str, query: str) -> float:
    """Simple keyword relevance score as fallback when embeddings unavailable."""
    text_lower  = text.lower()
    query_lower = query.lower()
    pair_key    = pair.replace("=X", "")

    pair_hits   = sum(1 for k in PAIR_KEYWORDS.get(pair_key, []) if k in text_lower)
    global_hits = sum(1 for k in PAIR_KEYWORDS["GLOBAL"] if k in text_lower)
    query_words = [w for w in query_lower.split() if len(w) > 3]
    query_hits  = sum(1 for w in query_words if w in text_lower)

    return float(pair_hits * 2 + global_hits + query_hits)


# ── NewsRAG ───────────────────────────────────────────────────────────────────

class NewsRAG:
    """
    Rolling in-memory news vector store with semantic retrieval.

    Falls back gracefully to keyword scoring if ChromaDB or
    sentence-transformers are not installed.
    """

    COLLECTION_NAME = "fx_news"
    EMBED_MODEL     = "all-MiniLM-L6-v2"   # 22MB, ~14ms/sentence on CPU
    WINDOW_HOURS    = 72                    # keep articles from last 72h
    MAX_ARTICLES    = 500                   # cap to avoid memory growth

    def __init__(self):
        self._articles: List[Dict]          = []   # raw article store
        self._embedder: Optional[object]    = None
        self._collection: Optional[object] = None
        self._use_rag = CHROMA_AVAILABLE and ST_AVAILABLE
        self._initialized = False

        if self._use_rag:
            self._init_rag()
        else:
            logger.info(
                "NewsRAG: running in keyword-fallback mode "
                "(install chromadb + sentence-transformers for full RAG)"
            )

    def _init_rag(self) -> None:
        """Lazy-initialize embedder and ChromaDB collection."""
        try:
            logger.info("NewsRAG: loading sentence-transformer model …")
            self._embedder = SentenceTransformer(self.EMBED_MODEL)

            client = chromadb.Client(ChromaSettings(
                anonymized_telemetry=False,
                is_persistent=False,   # in-memory only
            ))
            self._collection = client.get_or_create_collection(
                name=self.COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
            self._initialized = True
            logger.success("NewsRAG: initialized (ChromaDB + sentence-transformers)")
        except Exception as e:
            logger.warning(f"NewsRAG: init failed ({e}) — keyword fallback")
            self._use_rag = False

    # ── Ingestion ─────────────────────────────────────────────────────────────

    def ingest(self, articles: List[Dict]) -> int:
        """
        Add articles to the store. Deduplicates by title hash.

        articles: list of dicts with keys: title, summary, published (datetime)
        Returns: number of new articles added
        """
        now    = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=self.WINDOW_HOURS)

        # Expire old articles
        self._articles = [
            a for a in self._articles
            if a.get("published", now) >= cutoff
        ]

        existing_ids = {a["id"] for a in self._articles}
        new_articles = []

        for art in articles:
            title   = art.get("title", "")
            summary = art.get("summary", "")
            pub     = art.get("published", now)

            if not title:
                continue

            # Skip articles outside window
            if isinstance(pub, datetime) and pub < cutoff:
                continue

            art_id = hashlib.md5(title.encode()).hexdigest()[:16]
            if art_id in existing_ids:
                continue

            art["id"]   = art_id
            art["text"] = f"{title}. {summary}".strip()
            new_articles.append(art)
            existing_ids.add(art_id)

        if not new_articles:
            return 0

        # Cap total size
        all_articles = self._articles + new_articles
        if len(all_articles) > self.MAX_ARTICLES:
            all_articles = sorted(
                all_articles,
                key=lambda a: a.get("published", now),
                reverse=True
            )[:self.MAX_ARTICLES]
        self._articles = all_articles

        # Add to ChromaDB if available
        if self._use_rag and self._collection is not None:
            try:
                texts = [a["text"] for a in new_articles]
                ids   = [a["id"]   for a in new_articles]
                metas = [
                    {
                        "published": a.get("published", now).isoformat()
                        if isinstance(a.get("published"), datetime)
                        else str(a.get("published", "")),
                        "title": a.get("title", "")[:200],
                    }
                    for a in new_articles
                ]
                embeddings = self._embedder.encode(
                    texts, batch_size=32, show_progress_bar=False
                ).tolist()
                self._collection.add(
                    ids=ids,
                    embeddings=embeddings,
                    documents=texts,
                    metadatas=metas,
                )
            except Exception as e:
                logger.warning(f"NewsRAG: ChromaDB add failed ({e})")

        logger.debug(f"NewsRAG: ingested {len(new_articles)} new articles "
                     f"(total={len(self._articles)})")
        return len(new_articles)

    # ── Retrieval ─────────────────────────────────────────────────────────────

    def retrieve(
        self,
        pair: str,
        query: str,
        top_k: int = 5,
    ) -> List[str]:
        """
        Retrieve the most relevant article headlines for a pair + query.

        pair:  e.g. "EURUSD=X" or "EURUSD"
        query: context string, e.g. "EURUSD SELL signal bearish macro yield curve"
        top_k: number of results to return

        Returns: list of formatted headline strings for LLM injection
        """
        if not self._articles:
            return []

        pair_key = pair.replace("=X", "")

        if self._use_rag and self._collection is not None:
            return self._semantic_retrieve(pair_key, query, top_k)
        else:
            return self._keyword_retrieve(pair_key, query, top_k)

    def _semantic_retrieve(self, pair: str, query: str, top_k: int) -> List[str]:
        """ChromaDB cosine similarity retrieval."""
        try:
            n_stored = self._collection.count()
            if n_stored == 0:
                return self._keyword_retrieve(pair, query, top_k)

            query_emb = self._embedder.encode(
                [query], show_progress_bar=False
            ).tolist()

            results = self._collection.query(
                query_embeddings=query_emb,
                n_results=min(top_k * 2, n_stored),   # over-fetch then filter
                include=["documents", "metadatas", "distances"],
            )

            docs  = results["documents"][0]
            metas = results["metadatas"][0]

            # Format as headlines with timestamps
            headlines = []
            for doc, meta in zip(docs, metas):
                title = meta.get("title", doc[:100])
                pub   = meta.get("published", "")
                try:
                    dt  = datetime.fromisoformat(pub)
                    ts  = dt.strftime("%H:%M")
                except Exception:
                    ts  = ""
                headlines.append(f"[{ts}] {title}" if ts else title)

            return headlines[:top_k]

        except Exception as e:
            logger.warning(f"NewsRAG: semantic retrieve failed ({e}) — keyword fallback")
            return self._keyword_retrieve(pair, query, top_k)

    def _keyword_retrieve(self, pair: str, query: str, top_k: int) -> List[str]:
        """Keyword-based fallback retrieval."""
        scored = []
        for art in self._articles:
            score = _keyword_score(art.get("text", ""), pair, query)
            if score > 0:
                scored.append((score, art))

        scored.sort(key=lambda x: x[0], reverse=True)
        headlines = []
        for _, art in scored[:top_k]:
            title = art.get("title", "")
            pub   = art.get("published")
            ts    = pub.strftime("%H:%M") if isinstance(pub, datetime) else ""
            headlines.append(f"[{ts}] {title}" if ts else title)

        return headlines

    # ── Stats ─────────────────────────────────────────────────────────────────

    @property
    def article_count(self) -> int:
        return len(self._articles)

    def stats(self) -> Dict:
        now    = datetime.now(timezone.utc)
        ages   = []
        for a in self._articles:
            pub = a.get("published")
            if isinstance(pub, datetime):
                ages.append((now - pub).total_seconds() / 3600)

        return {
            "total":       len(self._articles),
            "rag_enabled": self._use_rag,
            "avg_age_h":   round(sum(ages) / len(ages), 1) if ages else 0.0,
            "oldest_h":    round(max(ages), 1) if ages else 0.0,
            "newest_h":    round(min(ages), 1) if ages else 0.0,
        }

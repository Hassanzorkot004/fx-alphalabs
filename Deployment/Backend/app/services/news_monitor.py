"""News monitoring - detects sentiment spikes and triggers immediate Sentiment Agent rerun"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Callable
import numpy as np
from loguru import logger

from app.services.news_service import news_service


class NewsMonitor:
    """Monitors news feeds for sentiment spikes"""
    
    def __init__(self, spike_threshold: float = 0.25, cooldown_minutes: int = 15):
        self.spike_threshold = spike_threshold
        self.cooldown_seconds = cooldown_minutes * 60
        self.baseline_sentiment: Dict[str, float] = {}
        self.last_spike_fired: Dict[str, datetime] = {}
        self.running = False
        self._on_spike_callback: Callable = None
    
    def set_spike_callback(self, callback: Callable):
        """Set callback to trigger when spike detected"""
        self._on_spike_callback = callback
    
    async def run(self):
        """Background task - polls RSS every 2 minutes"""
        self.running = True
        logger.info("NewsMonitor started - polling every 2 minutes")
        
        while self.running:
            try:
                await self._check_for_spikes()
            except Exception as e:
                logger.error(f"NewsMonitor error: {e}")
            
            await asyncio.sleep(120)  # 2 minutes
    
    def stop(self):
        """Stop the monitor"""
        self.running = False
        logger.info("NewsMonitor stopped")
    
    async def _check_for_spikes(self):
        """Check all pairs for sentiment spikes"""
        articles = news_service.get_articles(max_age_hours=2, limit=50)
        
        if not articles:
            return
        
        # Group articles by currency
        currency_articles = {
            "EUR": [],
            "GBP": [],
            "JPY": [],
            "USD": [],
        }
        
        for article in articles:
            for tag in article.get("tags", []):
                if tag in currency_articles:
                    currency_articles[tag].append(article)
        
        # Check each pair
        pairs = ["EURUSD", "GBPUSD", "USDJPY"]
        for pair in pairs:
            await self._check_pair_spike(pair, currency_articles)
    
    async def _check_pair_spike(self, pair: str, currency_articles: Dict):
        """Check if a specific pair has a sentiment spike"""
        # Get currencies for this pair
        if pair == "EURUSD":
            currencies = ["EUR", "USD"]
        elif pair == "GBPUSD":
            currencies = ["GBP", "USD"]
        elif pair == "USDJPY":
            currencies = ["JPY", "USD"]
        else:
            return
        
        # Collect relevant articles
        relevant_articles = []
        for curr in currencies:
            relevant_articles.extend(currency_articles.get(curr, []))
        
        if len(relevant_articles) < 2:
            return
        
        # Simple sentiment scoring (positive tags = bullish, negative = bearish)
        # This is a placeholder - in production you'd use the actual sentiment model
        scores = []
        for article in relevant_articles:
            title_lower = article.get("title", "").lower()
            score = 0.0
            
            # Bullish keywords
            if any(word in title_lower for word in ["rise", "gain", "up", "surge", "rally", "boost"]):
                score += 0.3
            
            # Bearish keywords
            if any(word in title_lower for word in ["fall", "drop", "down", "plunge", "decline", "slump"]):
                score -= 0.3
            
            scores.append(score)
        
        current_avg = float(np.mean(scores)) if scores else 0.0
        baseline = self.baseline_sentiment.get(pair, 0.0)
        delta = abs(current_avg - baseline)
        
        # Check for spike
        if delta >= self.spike_threshold:
            # Check cooldown
            last_spike = self.last_spike_fired.get(pair)
            if last_spike:
                seconds_since = (datetime.now() - last_spike).total_seconds()
                if seconds_since < self.cooldown_seconds:
                    logger.debug(f"[{pair}] Spike detected but in cooldown ({seconds_since:.0f}s < {self.cooldown_seconds}s)")
                    return
            
            # Fire spike event
            logger.warning(
                f"[{pair}] SENTIMENT SPIKE DETECTED: "
                f"delta={delta:.3f} (threshold={self.spike_threshold}), "
                f"current={current_avg:+.3f}, baseline={baseline:+.3f}, "
                f"articles={len(relevant_articles)}"
            )
            
            self.last_spike_fired[pair] = datetime.now()
            
            # Trigger callback
            if self._on_spike_callback:
                await self._on_spike_callback(pair, {
                    "delta": delta,
                    "current_avg": current_avg,
                    "baseline": baseline,
                    "article_count": len(relevant_articles),
                })
        
        # Update rolling baseline (slow exponential average)
        self.baseline_sentiment[pair] = 0.95 * baseline + 0.05 * current_avg


# Global instance
news_monitor = NewsMonitor()

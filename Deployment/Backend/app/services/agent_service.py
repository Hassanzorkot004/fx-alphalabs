"""Service layer wrapping fx_alphalab.AgentRunner"""

import asyncio
from typing import Dict, List, Optional

from loguru import logger

try:
    from fx_alphalab import AgentRunner
    FX_ALPHALAB_AVAILABLE = True
except ImportError:
    FX_ALPHALAB_AVAILABLE = False
    logger.warning(
        "fx_alphalab not installed. "
        "Install with: pip install -e ../../fx_alphalab"
    )


class AgentService:
    """Manages agent execution for the backend"""
    
    def __init__(self):
        self.runner: Optional[AgentRunner] = None
        self.running = False
        self.cycle_number = 0
        
    def initialize(self):
        """Lazy initialization of agent runner"""
        if not FX_ALPHALAB_AVAILABLE:
            raise RuntimeError(
                "fx_alphalab package not installed. "
                "Run: pip install -e ../../fx_alphalab"
            )
            
        if self.runner is None:
            logger.info("Initializing AgentRunner...")
            try:
                self.runner = AgentRunner()
                logger.success("✓ AgentRunner initialized")
            except Exception as e:
                logger.error(f"Failed to initialize AgentRunner: {e}")
                raise
    
    async def run_cycle(self, pairs: Optional[List[str]] = None) -> List[Dict]:
        """
        Run agent cycle asynchronously.
        
        Args:
            pairs: Optional list of currency pairs to analyze
            
        Returns:
            List of signal dictionaries
            
        Raises:
            RuntimeError: If agent is already running
        """
        if self.running:
            raise RuntimeError("Agent already running")
        
        self.initialize()
        self.running = True
        self.cycle_number += 1
        
        try:
            logger.info(f"Starting agent cycle #{self.cycle_number}")
            
            # Run in thread pool to avoid blocking the event loop
            signals = await asyncio.to_thread(
                self.runner.run_cycle,
                pairs
            )
            
            logger.success(
                f"✓ Cycle #{self.cycle_number} completed - "
                f"{len(signals)} signals generated"
            )
            return signals
            
        except Exception as e:
            logger.error(f"✗ Cycle #{self.cycle_number} failed: {e}")
            raise
        finally:
            self.running = False
    
    @property
    def is_running(self) -> bool:
        """Check if agent is currently running"""
        return self.running
    
    @property
    def is_initialized(self) -> bool:
        """Check if agent runner is initialized"""
        return self.runner is not None
    
    async def run_technical_only(self, pairs: Optional[List[str]] = None) -> Dict[str, Dict]:
        """
        Run only Technical Agent for specified pairs.
        
        Returns:
            Dict mapping pair -> technical output
            {
                "EURUSD": {
                    "signal": "BUY",
                    "confidence": 0.73,
                    "p_buy": 0.68,
                    "p_sell": 0.12,
                    "p_hold": 0.20,
                    "rsi14": 0.58,
                    ...
                }
            }
        """
        self.initialize()
        
        if pairs is None:
            from app.config import settings
            pairs = settings.PAIRS
        
        try:
            logger.info(f"Running Technical Agent only for {pairs}")
            
            outputs = {}
            for pair in pairs:
                # Fetch price data
                price_df = self.runner.price_feed.fetch(pair)
                if price_df is None or len(price_df) < 50:
                    logger.warning(f"Insufficient price data for {pair}, skipping")
                    continue
                
                # Run Technical Agent
                tech_out = await asyncio.to_thread(
                    self.runner.tech_agent.predict_live,
                    price_df
                )
                outputs[pair] = tech_out
            
            logger.success(f"✓ Technical Agent completed for {len(outputs)} pairs")
            return outputs
            
        except Exception as e:
            logger.error(f"Technical-only run failed: {e}")
            raise
    
    async def run_sentiment_only(self, pair: str) -> Dict:
        """
        Run only Sentiment Agent for a specific pair.
        
        Returns:
            Sentiment output dict
            {
                "signal": "bullish",
                "p_buy": 0.65,
                "n_articles": 12,
                ...
            }
        """
        self.initialize()
        
        try:
            logger.info(f"Running Sentiment Agent only for {pair}")
            
            # Fetch news data
            news_result = self.runner.news_feed.fetch(pair)
            nws_feats = news_result["nws_features"]
            
            # Run Sentiment Agent
            sent_out = await asyncio.to_thread(
                self.runner.sent_agent.predict_live,
                nws_feats
            )
            
            logger.success(f"✓ Sentiment Agent completed for {pair}")
            return sent_out
            
        except Exception as e:
            logger.error(f"Sentiment-only run failed for {pair}: {e}")
            raise


# Global service instance
agent_service = AgentService()

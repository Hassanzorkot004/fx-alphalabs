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


# Global service instance
agent_service = AgentService()

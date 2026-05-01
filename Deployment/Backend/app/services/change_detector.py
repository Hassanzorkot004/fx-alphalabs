"""Change detection for agent outputs - decides when to trigger LLM"""

from typing import Dict, Optional
from loguru import logger


class ChangeDetector:
    """Detects meaningful changes in agent outputs"""
    
    def __init__(self):
        self._last_technical: Dict[str, Dict] = {}
        self._last_sentiment: Dict[str, Dict] = {}
    
    def technical_changed(self, pair: str, current: Dict) -> bool:
        """
        Check if Technical Agent output changed significantly.
        
        Triggers on:
        - Signal flip (BUY → SELL, etc)
        - Confidence change >= 15 percentage points
        - Leading probability change >= 12 percentage points
        """
        prev = self._last_technical.get(pair)
        self._last_technical[pair] = current
        
        if prev is None:
            logger.info(f"[{pair}] Technical: First run, triggering LLM")
            return True
        
        # Check signal flip
        prev_sig = prev.get("signal", "HOLD")
        curr_sig = current.get("signal", "HOLD")
        if prev_sig != curr_sig:
            logger.info(f"[{pair}] Technical: Signal changed {prev_sig} → {curr_sig}, triggering LLM")
            return True
        
        # Check confidence change
        prev_conf = float(prev.get("confidence", 0))
        curr_conf = float(current.get("confidence", 0))
        conf_delta = abs(curr_conf - prev_conf)
        if conf_delta >= 0.15:
            logger.info(f"[{pair}] Technical: Confidence changed by {conf_delta:.2f}, triggering LLM")
            return True
        
        # Check leading probability change
        prev_probs = [
            float(prev.get("p_buy", 0)),
            float(prev.get("p_hold", 0)),
            float(prev.get("p_sell", 0))
        ]
        curr_probs = [
            float(current.get("p_buy", 0)),
            float(current.get("p_hold", 0)),
            float(current.get("p_sell", 0))
        ]
        
        prev_max = max(prev_probs)
        curr_max = max(curr_probs)
        prob_delta = abs(curr_max - prev_max)
        
        if prob_delta >= 0.12:
            logger.info(f"[{pair}] Technical: Leading probability changed by {prob_delta:.2f}, triggering LLM")
            return True
        
        logger.debug(f"[{pair}] Technical: No significant change (conf_delta={conf_delta:.3f}, prob_delta={prob_delta:.3f})")
        return False
    
    def sentiment_changed(self, pair: str, current: Dict) -> bool:
        """
        Check if Sentiment Agent output changed significantly.
        
        Triggers on:
        - Signal flip
        - P(bullish) change >= 10 percentage points
        """
        prev = self._last_sentiment.get(pair)
        self._last_sentiment[pair] = current
        
        if prev is None:
            logger.info(f"[{pair}] Sentiment: First run, triggering LLM")
            return True
        
        # Check signal flip
        prev_sig = prev.get("signal", "HOLD")
        curr_sig = current.get("signal", "HOLD")
        # Ignore [LOW-NEWS] suffix for comparison
        prev_sig_clean = prev_sig.replace(" [LOW-NEWS]", "")
        curr_sig_clean = curr_sig.replace(" [LOW-NEWS]", "")
        
        if prev_sig_clean != curr_sig_clean and curr_sig_clean != "HOLD":
            logger.info(f"[{pair}] Sentiment: Signal changed {prev_sig} → {curr_sig}, triggering LLM")
            return True
        
        # Check P(bullish) change
        prev_bull = float(prev.get("p_buy", 0.33))
        curr_bull = float(current.get("p_buy", 0.33))
        bull_delta = abs(curr_bull - prev_bull)
        
        if bull_delta >= 0.10:
            logger.info(f"[{pair}] Sentiment: P(bullish) changed by {bull_delta:.2f}, triggering LLM")
            return True
        
        logger.debug(f"[{pair}] Sentiment: No significant change (bull_delta={bull_delta:.3f})")
        return False


# Global instance
change_detector = ChangeDetector()

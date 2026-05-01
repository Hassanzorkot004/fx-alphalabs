"""Live context service - provides real-time signal context without ML models"""

import time
from datetime import datetime, timezone
from typing import Dict, List, Optional

import yfinance as yf
from loguru import logger

from app.services.signal_validator import signal_validator


class LiveContextService:
    """Manages live context updates for active signals"""
    
    def __init__(self):
        pass
    
    def get_live_context(self, signal: Dict, current_price: float) -> Dict:
        """
        Get complete live context for a signal.
        
        Returns:
            {
                "pair": str,
                "current_price": float,
                "signal_age_minutes": float,
                "signal_age_display": str,
                "time_remaining": str,
                "tech_indicators": {...},
                "price_context": {...},
                "validity": {...},
                "freshness": {...}
            }
        """
        pair = signal.get("pair", "")
        
        # Get last Technical Agent output from signal (real model results)
        tech_indicators = {
            "rsi_14": signal.get("rsi14") * 100 if signal.get("rsi14") is not None else None,  # Signal stores 0-1, display as 0-100
            "p_buy": signal.get("p_buy", 0),
            "p_sell": signal.get("p_sell", 0),
            "p_hold": signal.get("p_hold", 0),
        }
        
        # Compute price context (vs entry/stop/target)
        price_context = signal_validator.compute_price_context(signal, current_price)
        
        # Check validity
        validity = signal_validator.check_signal_validity(signal, current_price)
        
        # Compute age and freshness
        try:
            ts_str = signal.get("timestamp", "")
            if ts_str:
                # Handle different timestamp formats
                if isinstance(ts_str, str):
                    # Remove timezone suffix variations
                    ts_str_clean = ts_str.replace("Z", "+00:00")
                    # Try parsing with timezone
                    try:
                        ts = datetime.fromisoformat(ts_str_clean)
                    except ValueError:
                        # Try without microseconds
                        ts = datetime.strptime(ts_str.split('.')[0], "%Y-%m-%d %H:%M:%S")
                        ts = ts.replace(tzinfo=timezone.utc)
                else:
                    ts = ts_str
                
                age_seconds = (datetime.now(timezone.utc) - ts).total_seconds()
                age_minutes = age_seconds / 60
                age_hours = age_seconds / 3600
                
                # Format age display
                if age_minutes < 60:
                    age_display = f"{int(age_minutes)} min ago"
                else:
                    age_display = f"{age_hours:.1f}h ago"
                
                # Compute time remaining
                agreement = signal.get("agent_agreement", "PARTIAL")
                horizon_hours = 8.0 if agreement == "FULL" else 12.0
                remaining_hours = horizon_hours - age_hours
                
                if remaining_hours > 1:
                    time_remaining = f"{remaining_hours:.1f}h remaining"
                elif remaining_hours > 0:
                    time_remaining = f"{int(remaining_hours * 60)} min remaining"
                else:
                    time_remaining = "Expired"
            else:
                age_minutes = 0
                age_display = "Unknown"
                time_remaining = "Unknown"
        except Exception as e:
            logger.warning(f"Failed to parse timestamp '{signal.get('timestamp')}': {e}")
            age_minutes = 0
            age_display = "Unknown"
            time_remaining = "Unknown"
        
        # Freshness metadata (when each component last ran)
        freshness = {
            "signal_generated_at": signal.get("timestamp"),
            "price_checked_at": datetime.now(timezone.utc).isoformat(),
            "macro_computed_at": signal.get("timestamp"),  # Same as signal for now
            "technical_computed_at": signal.get("timestamp"),
            "sentiment_computed_at": signal.get("timestamp"),
        }
        
        return {
            "pair": pair,
            "current_price": current_price,
            "signal_age_minutes": round(age_minutes, 1),
            "signal_age_display": age_display,
            "time_remaining": time_remaining,
            "tech_indicators": tech_indicators,
            "price_context": price_context,
            "validity": validity,
            "freshness": freshness,
        }
    
    def get_all_contexts(self, signals: List[Dict], 
                        prices: Dict[str, Dict]) -> Dict[str, Dict]:
        """Get live context for all active signals"""
        contexts = {}
        
        for signal in signals:
            pair = signal.get("pair", "")
            price_data = prices.get(pair, {})
            current_price = price_data.get("price", signal.get("price_at_signal", 0))
            
            if current_price:
                contexts[pair] = self.get_live_context(signal, current_price)
        
        return contexts


# Global service instance
live_context_service = LiveContextService()

"""Signal validation and live context computation"""

from datetime import datetime, timezone
from typing import Dict, Optional

import numpy as np
from loguru import logger


class SignalValidator:
    """Validates signals and computes live context"""
    
    @staticmethod
    def check_signal_validity(signal: Dict, current_price: float) -> Dict:
        """
        Check if signal is still valid and compute status.
        
        Returns:
            {
                "status": "VALID" | "STOPPED_OUT" | "TARGET_HIT" | "EXPIRED" | "WARNING",
                "reason": str,
                "action_recommended": str
            }
        """
        direction = signal.get("direction", "HOLD")
        
        # Parse timestamp
        try:
            ts_str = signal.get("timestamp", "")
            if ts_str:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                age_hours = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
            else:
                age_hours = 0
        except Exception:
            age_hours = 0
        
        # Check expiry based on horizon
        agreement = signal.get("agent_agreement", "PARTIAL")
        horizon_hours = 8.0 if agreement == "FULL" else 12.0
        
        if age_hours >= horizon_hours:
            return {
                "status": "EXPIRED",
                "reason": f"Signal is {age_hours:.1f}h old (horizon: {horizon_hours}h)",
                "action_recommended": "Do not trade. Wait for next signal update."
            }
        
        # Check stop/target levels
        stop = signal.get("stop_estimate")
        target = signal.get("target_estimate")
        
        if direction == "BUY":
            if stop and current_price <= stop:
                return {
                    "status": "STOPPED_OUT",
                    "reason": f"Price {current_price} hit stop level {stop}",
                    "action_recommended": "Exit position if held. Signal invalidated."
                }
            if target and current_price >= target:
                return {
                    "status": "TARGET_HIT",
                    "reason": f"Price {current_price} reached target {target}",
                    "action_recommended": "Take profit. Signal completed successfully."
                }
        
        # Check near expiry
        if age_hours >= horizon_hours * 0.8:
            return {
                "status": "NEAR_EXPIRY",
                "reason": f"Signal is {age_hours:.1f}h old, approaching {horizon_hours}h horizon",
                "action_recommended": "Do not open new positions. Monitor for next update."
            }
        
        # All checks passed
        return {
            "status": "VALID",
            "reason": f"Signal active ({age_hours:.1f}h old, {horizon_hours - age_hours:.1f}h remaining)",
            "action_recommended": "Signal is actionable within risk parameters."
        }
    
    @staticmethod
    def compute_price_context(signal: Dict, current_price: float) -> Dict:
        """Compute price position relative to signal levels"""
        direction = signal.get("direction", "HOLD")
        entry_low = signal.get("entry_low")
        entry_high = signal.get("entry_high")
        stop = signal.get("stop_estimate")
        target = signal.get("target_estimate")
        
        context = {
            "current_price": current_price,
            "vs_entry": None,
            "vs_stop": None,
            "vs_target": None,
            "entry_status": "unknown",
        }
        
        if not entry_low or not entry_high:
            return context
        
        # Entry zone status
        if entry_low <= current_price <= entry_high:
            context["entry_status"] = "in_zone"
            context["vs_entry"] = "Inside entry zone"
        elif current_price < entry_low:
            pips_below = (entry_low - current_price) * 10000
            context["entry_status"] = "below"
            context["vs_entry"] = f"{pips_below:.1f} pips below entry"
        else:
            pips_above = (current_price - entry_high) * 10000
            context["entry_status"] = "above"
            context["vs_entry"] = f"{pips_above:.1f} pips above entry"
        
        # Stop distance
        if stop:
            if direction == "BUY":
                pips_to_stop = (current_price - stop) * 10000
                context["vs_stop"] = f"{abs(pips_to_stop):.1f} pips {'above' if pips_to_stop > 0 else 'BELOW'} stop"
            else:
                pips_to_stop = (stop - current_price) * 10000
                context["vs_stop"] = f"{abs(pips_to_stop):.1f} pips {'below' if pips_to_stop > 0 else 'ABOVE'} stop"
        
        # Target distance
        if target:
            if direction == "BUY":
                pips_to_target = (target - current_price) * 10000
                context["vs_target"] = f"{abs(pips_to_target):.1f} pips to target"
            else:
                pips_to_target = (current_price - target) * 10000
                context["vs_target"] = f"{abs(pips_to_target):.1f} pips to target"
        
        return context


# Global validator instance
signal_validator = SignalValidator()

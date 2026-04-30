"""FX AlphaLab - Multi-agent forex trading system"""

__version__ = "2.0.0"

from fx_alphalab.agents import MacroAgent, TechnicalAgent, SentimentAgent
from fx_alphalab.orchestrator import Orchestrator
from fx_alphalab.core.runner import AgentRunner
from fx_alphalab.config.settings import Settings, settings

__all__ = [
    "MacroAgent",
    "TechnicalAgent",
    "SentimentAgent",
    "Orchestrator",
    "AgentRunner",
    "Settings",
    "settings",
    "__version__",
]

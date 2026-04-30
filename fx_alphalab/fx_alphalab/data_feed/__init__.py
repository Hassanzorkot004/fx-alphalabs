"""Data feed modules for FX AlphaLab"""

from fx_alphalab.data_feed.price_feed import PriceFeed
from fx_alphalab.data_feed.macro_feed import MacroFeed
from fx_alphalab.data_feed.news_feed import NewsFeed

__all__ = ["PriceFeed", "MacroFeed", "NewsFeed"]

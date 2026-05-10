import pandas as pd
import json
from datetime import datetime, timezone, timedelta

# Use today's date so signals appear fresh (no "X hours old" warning)
_TODAY = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)

def _ts(hours_ago: float) -> str:
    """Return an ISO timestamp N hours ago from now."""
    return (_TODAY - timedelta(hours=hours_ago)).isoformat()

COLS = [
    'timestamp','pair','direction','confidence','position_size',
    'macro_regime','tech_signal','sent_signal','agent_agreement',
    'reasoning','key_driver','risk_note','source',
    'macro_conf','tech_conf','sent_conf',
    'macro_analyst','macro_key_feat','macro_override',
    'tech_analyst','tech_key_feat','tech_override',
    'sent_analyst','sent_key_feat','sent_override',
    'price_at_signal','atr','entry_low','entry_high','stop_estimate','target_estimate',
    'yield_z','carry_signal','vix_z',
    'regime_prob_bull','regime_prob_neut','regime_prob_bear',
    'p_buy','p_sell','p_hold','model_conf',
    'rsi14','macd_hist','bb_pos',
    'p_bullish','n_articles','sent_raw','headlines'
]

def trade_levels(price, atr, direction):
    """Compute entry zone, stop, target. Returns None*4 for HOLD."""
    if direction == 'HOLD':
        return None, None, None, None
    h = 0.5 * atr
    if direction == 'BUY':
        return (round(price - h, 5), round(price + h, 5),
                round(price - 3 * atr, 5), round(price + 6 * atr, 5))
    else:  # SELL
        return (round(price - h, 5), round(price + h, 5),
                round(price + 3 * atr, 5), round(price - 6 * atr, 5))

def make_row(
    ts, pair, direction, confidence, position_size,
    macro_regime, tech_signal, sent_signal, agent_agreement,
    reasoning, key_driver, risk_note,
    macro_conf, tech_conf, sent_conf,
    macro_analyst, macro_key_feat, macro_override,
    tech_analyst, tech_key_feat, tech_override,
    sent_analyst, sent_key_feat, sent_override,
    price, atr,
    yield_z, carry_signal, vix_z,
    rpbull, rpneut, rpbear,
    p_buy, p_sell, p_hold, model_conf,
    rsi14, macd_hist, bb_pos,
    p_bullish, n_articles, sent_raw, headlines_list
):
    el, eh, se, te = trade_levels(price, atr, direction)
    return {
        'timestamp': ts, 'pair': pair, 'direction': direction,
        'confidence': confidence, 'position_size': position_size,
        'macro_regime': macro_regime, 'tech_signal': tech_signal,
        'sent_signal': sent_signal, 'agent_agreement': agent_agreement,
        'reasoning': reasoning, 'key_driver': key_driver,
        'risk_note': risk_note, 'source': 'groq',
        'macro_conf': macro_conf, 'tech_conf': tech_conf, 'sent_conf': sent_conf,
        'macro_analyst': macro_analyst, 'macro_key_feat': macro_key_feat,
        'macro_override': macro_override,
        'tech_analyst': tech_analyst, 'tech_key_feat': tech_key_feat,
        'tech_override': tech_override,
        'sent_analyst': sent_analyst, 'sent_key_feat': sent_key_feat,
        'sent_override': sent_override,
        'price_at_signal': price, 'atr': atr,
        'entry_low': el, 'entry_high': eh,
        'stop_estimate': se, 'target_estimate': te,
        'yield_z': yield_z, 'carry_signal': carry_signal, 'vix_z': vix_z,
        'regime_prob_bull': rpbull, 'regime_prob_neut': rpneut,
        'regime_prob_bear': rpbear,
        'p_buy': p_buy, 'p_sell': p_sell, 'p_hold': p_hold,
        'model_conf': model_conf,
        'rsi14': rsi14, 'macd_hist': macd_hist, 'bb_pos': bb_pos,
        'p_bullish': p_bullish, 'n_articles': n_articles,
        'sent_raw': sent_raw, 'headlines': json.dumps(headlines_list)
    }

# ─────────────────────────────────────────────
# VIDEO 1 — COMMERCIAL  (1 cycle, 3 signals)
# ─────────────────────────────────────────────
# Macro block shared across all 3 pairs
M1 = dict(
    macro_regime='bearish', yield_z=-0.821, vix_z=0.412,
    rpbull=0.2184, rpneut=0.3127, rpbear=0.4689,
    macro_conf=0.4689          # max(regime_probs)
)
HL1 = [
    "[08:47] FOMC minutes signal Fed in no rush to cut rates — Reuters",
    "[08:31] Dollar index climbs to 3-week high as hawkish Fed tone sinks in — ForexLive",
    "[08:18] EUR/USD slides toward 1.0820 as USD demand picks up — FXStreet",
    "[07:54] USD/JPY breaks resistance at 152.00 on strong US macro data — MarketWatch",
    "[07:41] ECB rate path diverging from Fed, euro on the back foot — CNBC"
]

rows_v1 = []

# ── EURUSD  SELL  FULL ──
rows_v1.append(make_row(
    ts=_ts(0.5), pair='EURUSD=X',
    direction='SELL', confidence=0.78, position_size=0.8,
    macro_regime=M1['macro_regime'],
    tech_signal='SELL', sent_signal='SELL', agent_agreement='FULL',
    reasoning=(
        "The EURUSD sell signal is supported by a rare FULL agreement across all three agents: "
        "a bearish macro regime driven by a yield curve z-score of -0.821, a technical model sell "
        "at RSI 38.2 with probability 0.78, and negative news sentiment of -0.42 following hawkish "
        "FOMC minutes. With confidence at 0.78 and position size 0.8, the signal carries strong "
        "conviction with entry zone at 1.08199–1.08283, stop at 1.08492, and target at 1.07739."
    ),
    key_driver='MACRO',
    risk_note=(
        "An unexpected dovish shift from the Fed or better-than-expected Eurozone inflation data "
        "could reverse the USD rally and invalidate this sell signal."
    ),
    macro_conf=M1['macro_conf'], tech_conf=0.78, sent_conf=0.42,
    macro_analyst=(
        "The macro regime is firmly bearish for EURUSD, driven by a yield curve z-score of -0.821 "
        "signalling that US yields remain elevated relative to historical norms and creating a "
        "structural headwind for the euro. With the VIX z-score at 0.412 indicating mild risk-off "
        "sentiment and the bearish regime probability at 0.469, the macro backdrop strongly favours "
        "USD strength against the euro."
    ),
    macro_key_feat='mac_yield_z', macro_override=False,
    tech_analyst=(
        "EURUSD is in a clear downtrend with the RSI at 38.2, approaching oversold territory but "
        "with further room to fall, and the price trading near the lower Bollinger Band at a position "
        "of 0.22, confirming bearish momentum. The MACD histogram of -0.000318 remains negative "
        "and the model assigns a sell probability of 0.78 with high confidence, supporting a "
        "directional sell signal."
    ),
    tech_key_feat='RSI(14)=38.2', tech_override=False,
    sent_analyst=(
        "News sentiment for EURUSD is bearish, with 6 relevant articles driving a bullish probability "
        "of 0.18 and a raw sentiment score of -0.42, reflecting the market reaction to hawkish FOMC "
        "minutes and the widening ECB-Fed policy divergence. The sentiment agent aligns with both "
        "technical and macro signals, contributing to FULL agreement on the sell recommendation."
    ),
    sent_key_feat='FOMC hawkish', sent_override=False,
    price=1.08241, atr=0.000836,
    yield_z=M1['yield_z'], carry_signal=-0.0478, vix_z=M1['vix_z'],
    rpbull=M1['rpbull'], rpneut=M1['rpneut'], rpbear=M1['rpbear'],
    p_buy=0.11, p_sell=0.78, p_hold=0.11, model_conf=0.78,
    rsi14=38.2, macd_hist=-0.000318, bb_pos=0.22,
    p_bullish=0.18, n_articles=6, sent_raw=-0.42, headlines_list=HL1
))

# ── GBPUSD  HOLD  CONFLICT ──
rows_v1.append(make_row(
    ts=_ts(0.5), pair='GBPUSD=X',
    direction='HOLD', confidence=0.50, position_size=0.0,
    macro_regime=M1['macro_regime'],
    tech_signal='HOLD', sent_signal='SELL', agent_agreement='CONFLICT',
    reasoning=(
        "The GBPUSD hold reflects a CONFLICT state where bearish macro and mildly bearish sentiment "
        "are undermined by a neutral technical model with near-zero confidence of 0.038. Without "
        "technical confirmation, the conviction gate cannot fire a directional signal, keeping "
        "position size at zero while the system leans bearish with a sell probability of 0.38."
    ),
    key_driver='TECHNICAL',
    risk_note=(
        "A break below 1.2850 with rising technical confidence could trigger a sell in the next "
        "cycle; a bounce above 1.2920 would invalidate the bearish lean."
    ),
    macro_conf=M1['macro_conf'], tech_conf=0.038, sent_conf=0.21,
    macro_analyst=(
        "The macro environment remains bearish for GBPUSD, with a yield curve z-score of -0.821 "
        "and bearish regime probability of 0.469 sustaining USD demand. The negative carry signal "
        "of -0.436 for the pair adds structural downward pressure, but macro confidence alone is "
        "insufficient to override the neutral technical model and fire a directional signal."
    ),
    macro_key_feat='mac_yield_z', macro_override=False,
    tech_analyst=(
        "The technical model for GBPUSD is neutral, with the RSI at 51.4 sitting in the mid-range "
        "and a Bollinger Band position of 0.48 indicating price is near the centre of its recent "
        "range with no directional bias. The MACD histogram of -0.000189 is marginally negative but "
        "insufficient to confirm a downtrend, and model confidence of 0.038 is well below the "
        "threshold of 0.15 required to fire a directional signal."
    ),
    tech_key_feat='RSI(14)=51.4', tech_override=True,
    sent_analyst=(
        "Sentiment for GBPUSD is mildly bearish, with 5 relevant articles producing a raw score "
        "of -0.21 and a bullish probability of 0.30, reflecting the spillover from USD strength "
        "driven by FOMC minutes. With sentiment conviction insufficient to override the neutral "
        "technical reading, the overall signal remains a hold pending a clearer technical setup."
    ),
    sent_key_feat='USD spillover', sent_override=False,
    price=1.28743, atr=0.001124,
    yield_z=M1['yield_z'], carry_signal=-0.4362, vix_z=M1['vix_z'],
    rpbull=M1['rpbull'], rpneut=M1['rpneut'], rpbear=M1['rpbear'],
    p_buy=0.26, p_sell=0.38, p_hold=0.36, model_conf=0.038,
    rsi14=51.4, macd_hist=-0.000189, bb_pos=0.48,
    p_bullish=0.30, n_articles=5, sent_raw=-0.21, headlines_list=HL1
))

# ── USDJPY  BUY  PARTIAL ──
rows_v1.append(make_row(
    ts=_ts(0.5), pair='USDJPY=X',
    direction='BUY', confidence=0.64, position_size=0.5,
    macro_regime=M1['macro_regime'],
    tech_signal='BUY', sent_signal='BUY', agent_agreement='PARTIAL',
    reasoning=(
        "The USDJPY buy signal reflects PARTIAL agreement between the technical and sentiment agents, "
        "both responding to the FOMC-driven USD rally and the BoJ divergence trade, despite the macro "
        "agent's bearish regime classification. Technical confidence of 0.64 exceeds the required "
        "threshold of 0.15, allowing the conviction gate to fire with position size 0.5 and target "
        "at 153.282."
    ),
    key_driver='TECHNICAL',
    risk_note=(
        "A sudden risk-off event or BoJ verbal intervention near the 153.00 level could rapidly "
        "reverse the USD/JPY rally and invalidate this buy signal."
    ),
    macro_conf=M1['macro_conf'], tech_conf=0.64, sent_conf=0.38,
    macro_analyst=(
        "The macro regime is bearish for USDJPY, driven by a yield curve z-score of -0.821 and "
        "subdued macro strength, suggesting structural headwinds for USD from a regime perspective. "
        "However, the pair-specific carry signal of -0.716 reflects the significant interest rate "
        "differential between USD and JPY that continues to attract buyers, partially offsetting "
        "the bearish macro classification."
    ),
    macro_key_feat='carry_signal', macro_override=False,
    tech_analyst=(
        "The technical model is generating a buy signal for USDJPY, supported by a rising RSI of "
        "61.3 with room before overbought territory, a positive MACD histogram of 0.0823, and a "
        "Bollinger Band position of 0.67 indicating price is in the upper half of its recent range. "
        "Model confidence stands at 0.64, comfortably above the 0.15 firing threshold in a bearish "
        "macro regime, validating the directional signal."
    ),
    tech_key_feat='RSI(14)=61.3', tech_override=False,
    sent_analyst=(
        "News sentiment for USDJPY is bullish, with 7 relevant articles and a raw sentiment score "
        "of 0.38 driven by the market reaction to the FOMC minutes and expectations of continued "
        "JPY weakness as the Bank of Japan maintains its accommodative stance. The bullish sentiment "
        "probability of 0.62 aligns with the technical buy signal, creating PARTIAL agreement "
        "despite the conflicting macro regime classification."
    ),
    sent_key_feat='BoJ divergence', sent_override=False,
    price=152.384, atr=0.149714,
    yield_z=M1['yield_z'], carry_signal=-0.7157, vix_z=M1['vix_z'],
    rpbull=M1['rpbull'], rpneut=M1['rpneut'], rpbear=M1['rpbear'],
    p_buy=0.64, p_sell=0.18, p_hold=0.18, model_conf=0.64,
    rsi14=61.3, macd_hist=0.082341, bb_pos=0.67,
    p_bullish=0.62, n_articles=7, sent_raw=0.38, headlines_list=HL1
))

df_v1 = pd.DataFrame(rows_v1, columns=COLS)
df_v1.to_csv('outputs/demo_video1_commercial.csv', index=False)
print(f"Video 1: {len(df_v1)} rows written")

# ─────────────────────────────────────────────
# VIDEO 2 — SHOWCASE  (5 cycles × 3 pairs = 15 rows)
# ─────────────────────────────────────────────

# Macro blocks per cycle (macro is a global cached read — identical across pairs in each cycle)
MACRO = {
    1: dict(macro_regime='bearish', yield_z=-0.721, vix_z=0.318,
            rpbull=0.2312, rpneut=0.3241, rpbear=0.4447, macro_conf=0.4447),
    2: dict(macro_regime='bearish', yield_z=-0.689, vix_z=0.287,
            rpbull=0.2198, rpneut=0.3312, rpbear=0.4490, macro_conf=0.4490),
    3: dict(macro_regime='bearish', yield_z=-0.643, vix_z=0.412,
            rpbull=0.2087, rpneut=0.3189, rpbear=0.4724, macro_conf=0.4724),
    4: dict(macro_regime='bearish', yield_z=-0.598, vix_z=0.487,
            rpbull=0.1943, rpneut=0.3124, rpbear=0.4933, macro_conf=0.4933),
    5: dict(macro_regime='bearish', yield_z=-0.612, vix_z=0.321,
            rpbull=0.2241, rpneut=0.3418, rpbear=0.4341, macro_conf=0.4341),
}

# Headlines per cycle
HL = {
    1: [
        "[06:42] FOMC minutes signal Fed in no rush to cut rates — Reuters",
        "[06:31] Dollar strengthens as FOMC minutes reveal hawkish undertone — ForexLive",
        "[05:58] US Treasury yields climb on Fed hold expectations — MarketWatch",
        "[05:44] EUR/USD slides as dollar demand returns post-FOMC — FXStreet",
        "[05:21] USD/JPY eyes 153.00 as risk appetite improves — ForexLive",
    ],
    2: [
        "[07:48] Dollar rally extends into European open, DXY above 104.20 — Reuters",
        "[07:34] EUR/USD breaks below 1.0860 on continued USD demand — ForexLive",
        "[07:21] Sterling struggles as UK data disappoints, GBP/USD near 1.2910 — FXStreet",
        "[07:08] USD/JPY pushes toward 152.30 as Treasuries remain elevated — MarketWatch",
        "[06:52] Fed hold expectations keeping dollar bid into London session — CNBC",
    ],
    3: [
        "[08:47] ECB's Lane signals further rate cuts possible if disinflation continues — Reuters",
        "[08:34] Euro weakens after ECB policymaker downplays Eurozone growth outlook — ForexLive",
        "[08:21] USD/JPY breaks above 152.40 on combined Fed-BoJ divergence — FXStreet",
        "[08:09] GBP/USD falls through 1.2910 as dollar dominance continues — MarketWatch",
        "[07:58] Risk appetite improving as equities rise alongside USD — CNBC",
    ],
    4: [
        "[09:52] US Non-Farm Payrolls beat forecasts: 227K vs 185K expected — Reuters",
        "[09:48] Dollar surges to session highs on blockbuster US jobs data — ForexLive",
        "[09:41] EUR/USD hits session low at 1.0812 on NFP surprise — FXStreet",
        "[09:33] USD/JPY eyes 153.00 after breaking through 152.70 — MarketWatch",
        "[09:21] GBP/USD falls toward 1.2880 as dollar demand spikes across the board — ForexLive",
    ],
    5: [
        "[10:48] EUR/USD showing tentative technical bounce from oversold territory — FXStreet",
        "[10:41] Dollar bulls take profit as EUR/USD nears key support at 1.0800 — ForexLive",
        "[10:28] USD/JPY momentum slows as RSI approaches overbought zone near 153.00 — MarketWatch",
        "[10:14] GBP/USD stabilises near 1.2870 ahead of UK retail sales data — BBC Business",
        "[09:58] Risk sentiment turns mixed as NFP euphoria fades in NY session — CNBC",
    ],
}

rows_v2 = []

# ═══════════════════════════════════════════════
# CYCLE 1 — 07:00 UTC — FOMC minutes dropped overnight
# ═══════════════════════════════════════════════
M = MACRO[1]

# ── EURUSD  SELL  FULL ──
rows_v2.append(make_row(
    ts=_ts(4.0), pair='EURUSD=X',
    direction='SELL', confidence=0.74, position_size=0.7,
    macro_regime=M['macro_regime'],
    tech_signal='SELL', sent_signal='SELL', agent_agreement='FULL',
    reasoning=(
        "The EURUSD sell signal reflects FULL agreement across all three agents: a bearish macro "
        "regime underpinned by the yield curve z-score of -0.721 following overnight FOMC minutes, "
        "a technical model sell with RSI at 41.2 and confidence 0.74, and negative news sentiment "
        "of -0.31 driven by the hawkish Fed tone. All three agents are aligned on USD strength, "
        "resulting in a conviction signal with position size 0.7 and target at 1.08218."
    ),
    key_driver='MACRO',
    risk_note=(
        "A surprise dovish comment from a Fed official or better-than-expected Eurozone PMI data "
        "could trigger a short squeeze and reverse the signal rapidly."
    ),
    macro_conf=M['macro_conf'], tech_conf=0.74, sent_conf=0.31,
    macro_analyst=(
        "The macro regime is bearish for EURUSD, driven by a yield curve z-score of -0.721 and a "
        "bearish regime probability of 0.445, reflecting the impact of overnight FOMC minutes "
        "which reinforced expectations of an extended Fed hold. The macro strength index remains "
        "subdued and the VIX z-score of 0.318 adds mild risk-off pressure, firmly favouring USD "
        "appreciation against the euro."
    ),
    macro_key_feat='mac_yield_z', macro_override=False,
    tech_analyst=(
        "EURUSD is trending lower with the RSI at 41.2, in bearish territory with room before "
        "reaching oversold levels, and the Bollinger Band position of 0.28 confirming price is in "
        "the lower quarter of its recent range. The negative MACD histogram of -0.000318 confirms "
        "downward momentum, and the technical model assigns a sell probability of 0.74 with high "
        "confidence, generating a clear directional signal."
    ),
    tech_key_feat='RSI(14)=41.2', tech_override=False,
    sent_analyst=(
        "News sentiment is bearish for EURUSD with 5 relevant articles producing a raw score of "
        "-0.31, predominantly driven by the FOMC minutes and their hawkish tone signalling no "
        "imminent Fed rate cuts. The sentiment agent aligns with both macro and technical signals, "
        "producing FULL agreement with a bullish probability of just 0.21."
    ),
    sent_key_feat='FOMC hawkish', sent_override=False,
    price=1.08720, atr=0.000836,
    yield_z=M['yield_z'], carry_signal=-0.0478, vix_z=M['vix_z'],
    rpbull=M['rpbull'], rpneut=M['rpneut'], rpbear=M['rpbear'],
    p_buy=0.12, p_sell=0.74, p_hold=0.14, model_conf=0.74,
    rsi14=41.2, macd_hist=-0.000318, bb_pos=0.28,
    p_bullish=0.21, n_articles=5, sent_raw=-0.31, headlines_list=HL[1]
))

# ── GBPUSD  SELL  PARTIAL ──
rows_v2.append(make_row(
    ts=_ts(4.0), pair='GBPUSD=X',
    direction='SELL', confidence=0.61, position_size=0.4,
    macro_regime=M['macro_regime'],
    tech_signal='SELL', sent_signal='HOLD [LOW-NEWS]', agent_agreement='PARTIAL',
    reasoning=(
        "The GBPUSD sell reflects PARTIAL agreement between the macro and technical agents, with "
        "sentiment unable to confirm due to low news coverage. Technical confidence of 0.61 is "
        "sufficient to fire in the bearish macro environment, and the negative carry signal of "
        "-0.436 adds structural support for the sell. Position size of 0.4 reflects the reduced "
        "conviction of a two-agent agreement with target at 1.28665."
    ),
    key_driver='TECHNICAL',
    risk_note=(
        "With sentiment coverage limited to 3 articles, a sudden GBP-specific news catalyst "
        "could shift the signal rapidly in either direction."
    ),
    macro_conf=M['macro_conf'], tech_conf=0.61, sent_conf=0.14,
    macro_analyst=(
        "The macro backdrop is bearish for GBPUSD, with the yield curve z-score of -0.721 and "
        "bearish regime probability of 0.445 reflecting persistent USD demand following the FOMC "
        "minutes. The negative pair carry signal of -0.436 adds further structural downward "
        "pressure on sterling, aligning with the broader USD-positive macro environment."
    ),
    macro_key_feat='mac_yield_z', macro_override=False,
    tech_analyst=(
        "The technical model for GBPUSD is generating a sell signal with the RSI at 47.8, with "
        "room to fall further before reaching oversold levels, and the Bollinger Band position of "
        "0.41 showing price drifting into the lower half of its range. The MACD histogram of "
        "-0.000241 is negative and model confidence of 0.61 clears the 0.15 firing threshold "
        "in this bearish macro regime."
    ),
    tech_key_feat='RSI(14)=47.8', tech_override=False,
    sent_analyst=(
        "Sentiment coverage for GBPUSD is limited with only 3 relevant articles producing a raw "
        "score of -0.14, insufficient to generate a high-confidence signal. The low news volume "
        "triggers a LOW-NEWS flag and the sentiment agent defaults to a hold recommendation, so "
        "only macro and technical agents contribute to this PARTIAL agreement sell."
    ),
    sent_key_feat='LOW-NEWS', sent_override=True,
    price=1.29340, atr=0.001124,
    yield_z=M['yield_z'], carry_signal=-0.4362, vix_z=M['vix_z'],
    rpbull=M['rpbull'], rpneut=M['rpneut'], rpbear=M['rpbear'],
    p_buy=0.19, p_sell=0.61, p_hold=0.20, model_conf=0.61,
    rsi14=47.8, macd_hist=-0.000241, bb_pos=0.41,
    p_bullish=0.28, n_articles=3, sent_raw=-0.14, headlines_list=HL[1]
))

# ── USDJPY  BUY  PARTIAL ──
rows_v2.append(make_row(
    ts=_ts(4.0), pair='USDJPY=X',
    direction='BUY', confidence=0.63, position_size=0.5,
    macro_regime=M['macro_regime'],
    tech_signal='BUY', sent_signal='BUY', agent_agreement='PARTIAL',
    reasoning=(
        "USDJPY buy is driven by PARTIAL agreement between the technical and sentiment agents, both "
        "responding to the FOMC-driven USD rally and the BoJ divergence trade, despite the macro "
        "agent's bearish regime classification. Technical confidence of 0.63 clears the required "
        "threshold, generating a position size of 0.5 with entry at 151.765–151.915, stop at "
        "151.391, and target at 152.738."
    ),
    key_driver='TECHNICAL',
    risk_note=(
        "BoJ intervention risk increases above the 153.00 level; watch for MOF commentary "
        "that could rapidly reverse JPY weakness."
    ),
    macro_conf=M['macro_conf'], tech_conf=0.63, sent_conf=0.29,
    macro_analyst=(
        "The macro regime remains bearish for USDJPY as the yield curve z-score of -0.721 still "
        "reflects an inverted curve dynamic that historically creates headwinds for the pair. "
        "However, the pair-specific carry signal of -0.716 highlights the significant interest "
        "rate differential between USD and JPY, providing a structural pull toward USD strength "
        "that the regime label alone does not fully capture."
    ),
    macro_key_feat='carry_signal', macro_override=False,
    tech_analyst=(
        "The technical model is generating a buy signal for USDJPY with the RSI at 58.4, showing "
        "bullish momentum with room before overbought territory, and the Bollinger Band position "
        "of 0.62 trending through the upper half of the recent range. The positive MACD histogram "
        "of 0.0614 confirms upward momentum, and model confidence of 0.63 is sufficient to fire "
        "despite the bearish macro classification."
    ),
    tech_key_feat='RSI(14)=58.4', tech_override=False,
    sent_analyst=(
        "News sentiment for USDJPY is bullish with 5 articles and a raw score of 0.29, reflecting "
        "the market reaction to hawkish FOMC minutes and ongoing BoJ policy divergence keeping the "
        "yen under pressure. The bullish probability of 0.58 aligns with the technical signal, "
        "creating PARTIAL agreement with macro despite the bearish regime label."
    ),
    sent_key_feat='BoJ divergence', sent_override=False,
    price=151.840, atr=0.149714,
    yield_z=M['yield_z'], carry_signal=-0.7157, vix_z=M['vix_z'],
    rpbull=M['rpbull'], rpneut=M['rpneut'], rpbear=M['rpbear'],
    p_buy=0.63, p_sell=0.19, p_hold=0.18, model_conf=0.63,
    rsi14=58.4, macd_hist=0.061413, bb_pos=0.62,
    p_bullish=0.58, n_articles=5, sent_raw=0.29, headlines_list=HL[1]
))

# ═══════════════════════════════════════════════
# CYCLE 2 — 08:00 UTC — Tech update; EURUSD sell firms up, GBPUSD stalls
# ═══════════════════════════════════════════════
M = MACRO[2]

# ── EURUSD  SELL  FULL ──
rows_v2.append(make_row(
    ts=_ts(3.0), pair='EURUSD=X',
    direction='SELL', confidence=0.76, position_size=0.75,
    macro_regime=M['macro_regime'],
    tech_signal='SELL', sent_signal='SELL', agent_agreement='FULL',
    reasoning=(
        "The EURUSD sell signal strengthens in the second cycle, with FULL agreement maintained "
        "and confidence rising to 0.76 as the downtrend consolidates. RSI at 38.7 confirms continued "
        "bearish pressure without yet triggering an oversold bounce, and the deepening MACD histogram "
        "signals accelerating momentum; position size increases to 0.75 with target at 1.08008."
    ),
    key_driver='MACRO',
    risk_note=(
        "The RSI approaching 35 raises the risk of a short-term technical bounce; a break back "
        "above 1.0870 would signal weakening momentum and potential signal invalidation."
    ),
    macro_conf=M['macro_conf'], tech_conf=0.76, sent_conf=0.36,
    macro_analyst=(
        "The bearish macro regime for EURUSD deepens as the yield curve z-score of -0.689 remains "
        "negative and the bearish regime probability climbs to 0.449, with overnight FOMC minutes "
        "continuing to drive USD demand into the European session. The VIX z-score of 0.287 signals "
        "modest risk-off conditions, adding further support for USD strength against the euro."
    ),
    macro_key_feat='mac_yield_z', macro_override=False,
    tech_analyst=(
        "EURUSD continues its downtrend with the RSI falling to 38.7, approaching oversold territory "
        "but still generating a valid sell signal, and the price pushing further toward the lower "
        "Bollinger Band with a position of 0.24. The MACD histogram of -0.000421 deepens the "
        "negative reading from the prior cycle, and the model sell probability of 0.76 represents "
        "a strengthening of conviction."
    ),
    tech_key_feat='RSI(14)=38.7', tech_override=False,
    sent_analyst=(
        "Sentiment for EURUSD is increasingly bearish with 5 articles producing a raw score of "
        "-0.36, as European traders react to continued dollar strength from the Asian session. "
        "The bullish probability has dropped to 0.19, reinforcing the FULL agreement sell signal "
        "alongside both macro and technical agents."
    ),
    sent_key_feat='USD dominance', sent_override=False,
    price=1.08510, atr=0.000836,
    yield_z=M['yield_z'], carry_signal=-0.0478, vix_z=M['vix_z'],
    rpbull=M['rpbull'], rpneut=M['rpneut'], rpbear=M['rpbear'],
    p_buy=0.10, p_sell=0.76, p_hold=0.14, model_conf=0.76,
    rsi14=38.7, macd_hist=-0.000421, bb_pos=0.24,
    p_bullish=0.19, n_articles=5, sent_raw=-0.36, headlines_list=HL[2]
))

# ── GBPUSD  HOLD  CONFLICT ──
rows_v2.append(make_row(
    ts=_ts(3.0), pair='GBPUSD=X',
    direction='HOLD', confidence=0.50, position_size=0.0,
    macro_regime=M['macro_regime'],
    tech_signal='HOLD', sent_signal='SELL', agent_agreement='CONFLICT',
    reasoning=(
        "GBPUSD remains on HOLD as the CONFLICT between bearish macro and sentiment versus a "
        "neutral technical model persists for a second consecutive cycle. Technical confidence "
        "of 0.041 is well below the threshold of 0.15 required in a bearish macro regime, keeping "
        "position size at zero. The system is leaning bearish but requires technical confirmation "
        "to fire a directional signal."
    ),
    key_driver='TECHNICAL',
    risk_note=(
        "Two consecutive holds with a growing bearish lean suggest GBPUSD could trigger a sell in "
        "the next cycle if technical confidence rises; a close below 1.2900 would be the catalyst."
    ),
    macro_conf=M['macro_conf'], tech_conf=0.041, sent_conf=0.18,
    macro_analyst=(
        "The macro environment remains bearish for GBPUSD with the yield curve z-score at -0.689 "
        "and bearish regime probability of 0.449 sustaining USD demand. The negative carry signal "
        "of -0.436 continues to add structural downward pressure, but macro confidence alone "
        "cannot override the neutral technical model."
    ),
    macro_key_feat='mac_yield_z', macro_override=False,
    tech_analyst=(
        "The technical model for GBPUSD remains neutral with the RSI at 52.1 in the middle of its "
        "range and no clear directional bias, with the Bollinger Band position of 0.44 confirming "
        "price is oscillating near its central tendency. Model confidence is near zero at 0.041, "
        "preventing the conviction gate from firing despite the bearish macro and sentiment backdrop."
    ),
    tech_key_feat='RSI(14)=52.1', tech_override=True,
    sent_analyst=(
        "Sentiment for GBPUSD remains mildly bearish with 3 articles and a raw score of -0.18, "
        "reflecting the spillover from the broader USD strengthening narrative but without a "
        "GBP-specific catalyst to drive conviction. The low article count is insufficient to "
        "override the neutral technical model, maintaining the HOLD recommendation."
    ),
    sent_key_feat='USD spillover', sent_override=False,
    price=1.29180, atr=0.001124,
    yield_z=M['yield_z'], carry_signal=-0.4362, vix_z=M['vix_z'],
    rpbull=M['rpbull'], rpneut=M['rpneut'], rpbear=M['rpbear'],
    p_buy=0.22, p_sell=0.41, p_hold=0.37, model_conf=0.041,
    rsi14=52.1, macd_hist=-0.000108, bb_pos=0.44,
    p_bullish=0.26, n_articles=3, sent_raw=-0.18, headlines_list=HL[2]
))

# ── USDJPY  BUY  PARTIAL ──
rows_v2.append(make_row(
    ts=_ts(3.0), pair='USDJPY=X',
    direction='BUY', confidence=0.65, position_size=0.55,
    macro_regime=M['macro_regime'],
    tech_signal='BUY', sent_signal='BUY', agent_agreement='PARTIAL',
    reasoning=(
        "USDJPY maintains its buy signal in the second cycle with PARTIAL agreement between tech "
        "and sentiment, confidence edges higher to 0.65 and position size increases to 0.55. "
        "The technical model confirms the uptrend is intact with a strengthening MACD histogram, "
        "and the target at 153.028 remains the near-term objective."
    ),
    key_driver='TECHNICAL',
    risk_note=(
        "RSI approaching 65 suggests the rally is maturing; watch for BoJ intervention rhetoric "
        "if USD/JPY tests 153.00 ahead of schedule."
    ),
    macro_conf=M['macro_conf'], tech_conf=0.65, sent_conf=0.33,
    macro_analyst=(
        "The macro regime remains bearish for USDJPY with the yield curve z-score at -0.689, though "
        "the carry signal of -0.716 reflects the ongoing yield differential between USD and JPY "
        "that continues to attract buyers. The VIX z-score of 0.287 is modestly elevated, adding "
        "a mild risk-off tilt that is being outweighed by the technical and sentiment signals."
    ),
    macro_key_feat='carry_signal', macro_override=False,
    tech_analyst=(
        "The technical model sustains its buy signal for USDJPY with the RSI rising to 61.2, still "
        "in bullish territory with room before reaching overbought levels above 70, and the Bollinger "
        "Band position of 0.68 confirming the pair is trending in the upper half of its range. "
        "The MACD histogram of 0.0847 strengthens from the prior cycle and model confidence of "
        "0.65 maintains a comfortable margin above the firing threshold."
    ),
    tech_key_feat='RSI(14)=61.2', tech_override=False,
    sent_analyst=(
        "Sentiment for USDJPY strengthens with 5 articles and a raw score of 0.33, as the European "
        "session opens with continued USD buying and no new BoJ communication to support the yen. "
        "The bullish probability of 0.61 confirms sustained market conviction in the USD/JPY "
        "uptrend, maintaining PARTIAL agreement with the technical agent."
    ),
    sent_key_feat='USD demand', sent_override=False,
    price=152.130, atr=0.149714,
    yield_z=M['yield_z'], carry_signal=-0.7157, vix_z=M['vix_z'],
    rpbull=M['rpbull'], rpneut=M['rpneut'], rpbear=M['rpbear'],
    p_buy=0.65, p_sell=0.17, p_hold=0.18, model_conf=0.65,
    rsi14=61.2, macd_hist=0.084718, bb_pos=0.68,
    p_bullish=0.61, n_articles=5, sent_raw=0.33, headlines_list=HL[2]
))

# ═══════════════════════════════════════════════
# CYCLE 3 — 09:00 UTC — ECB Lane dovish; sentiment joins
# ═══════════════════════════════════════════════
M = MACRO[3]

# ── EURUSD  SELL  FULL (peak conviction this cycle) ──
rows_v2.append(make_row(
    ts=_ts(2.0), pair='EURUSD=X',
    direction='SELL', confidence=0.81, position_size=0.9,
    macro_regime=M['macro_regime'],
    tech_signal='SELL', sent_signal='SELL', agent_agreement='FULL',
    reasoning=(
        "The EURUSD sell reaches peak conviction with FULL agreement, confidence 0.81, and position "
        "size at 0.9, driven by the triple catalyst of hawkish Fed expectations, ECB Lane's dovish "
        "comments, and accelerating technical momentum at RSI 33.8. All three agents are at their "
        "highest confidence levels of the session, with target at 1.07788 as the key objective."
    ),
    key_driver='SENTIMENT',
    risk_note=(
        "RSI approaching oversold territory at 33.8 creates a short-squeeze risk; a bounce above "
        "1.0850 would signal potential exhaustion of the sell signal."
    ),
    macro_conf=M['macro_conf'], tech_conf=0.81, sent_conf=0.52,
    macro_analyst=(
        "The bearish macro regime for EURUSD intensifies as the yield curve z-score of -0.643 "
        "remains significantly negative and the bearish regime probability rises to 0.472, "
        "reflecting the growing divergence between Fed and ECB policy trajectories. ECB Lane's "
        "dovish signal this morning further undermines the euro's fundamental support, adding "
        "macro conviction to the sell recommendation."
    ),
    macro_key_feat='mac_yield_z', macro_override=False,
    tech_analyst=(
        "EURUSD is accelerating lower with the RSI dropping to 33.8, nearing oversold levels but "
        "with the downtrend intact, and the price touching the lower Bollinger Band at a position "
        "of 0.18, indicating strong bearish momentum. The MACD histogram of -0.000587 deepens "
        "significantly versus prior cycles, and the sell probability of 0.81 represents the "
        "highest technical conviction of the session."
    ),
    tech_key_feat='RSI(14)=33.8', tech_override=False,
    sent_analyst=(
        "Sentiment for EURUSD surges to its most bearish reading of the session with 8 articles "
        "and a raw score of -0.52, driven by ECB Lane's dovish comments and the continued "
        "FOMC-driven USD rally. The bullish probability collapses to 0.16 and the higher article "
        "count raises sentiment confidence to 0.52, strengthening the FULL agreement signal."
    ),
    sent_key_feat='ECB dovish', sent_override=False,
    price=1.08290, atr=0.000836,
    yield_z=M['yield_z'], carry_signal=-0.0478, vix_z=M['vix_z'],
    rpbull=M['rpbull'], rpneut=M['rpneut'], rpbear=M['rpbear'],
    p_buy=0.08, p_sell=0.81, p_hold=0.11, model_conf=0.81,
    rsi14=33.8, macd_hist=-0.000587, bb_pos=0.18,
    p_bullish=0.16, n_articles=8, sent_raw=-0.52, headlines_list=HL[3]
))

# ── GBPUSD  SELL  FULL (sentiment finally joins) ──
rows_v2.append(make_row(
    ts=_ts(2.0), pair='GBPUSD=X',
    direction='SELL', confidence=0.65, position_size=0.55,
    macro_regime=M['macro_regime'],
    tech_signal='SELL', sent_signal='SELL', agent_agreement='FULL',
    reasoning=(
        "GBPUSD achieves FULL agreement in the third cycle as ECB Lane's dovish comments boost "
        "sentiment conviction and the technical model confirms the RSI breaking below 50. With all "
        "three agents aligned on sterling weakness, confidence rises to 0.65 and position size "
        "to 0.55, with entry at 1.28954–1.29066 and target at 1.28335."
    ),
    key_driver='SENTIMENT',
    risk_note=(
        "UK-specific risk events such as a surprise BoE comment could temporarily reverse the "
        "bearish sterling signal despite the broad USD-dominant environment."
    ),
    macro_conf=M['macro_conf'], tech_conf=0.65, sent_conf=0.28,
    macro_analyst=(
        "The bearish macro regime intensifies for GBPUSD as the yield curve z-score of -0.643 and "
        "rising bearish regime probability of 0.472 reflect the impact of the ECB's dovish signal "
        "and ongoing FOMC-driven USD strength. The carry differential of -0.436 remains unchanged "
        "but the broader macro backdrop is now fully aligned with the technical and sentiment signals."
    ),
    macro_key_feat='mac_yield_z', macro_override=False,
    tech_analyst=(
        "The technical model confirms a sell for GBPUSD with the RSI falling to 44.3, breaking "
        "below the 50 midline to signal a shift from neutral to bearish momentum, and the Bollinger "
        "Band position of 0.32 showing the price moving into the lower third of its recent range. "
        "The MACD histogram of -0.000312 deepens the negative reading and model confidence of "
        "0.65 clears the firing threshold."
    ),
    tech_key_feat='RSI(14)=44.3', tech_override=False,
    sent_analyst=(
        "Sentiment for GBPUSD turns decisively bearish with 6 articles and a raw score of -0.28, "
        "driven by the combination of ECB Lane's dovish tone and continued FOMC-driven dollar "
        "demand spilling over into sterling. The bullish probability of 0.24 and improved coverage "
        "allow the sentiment agent to join the sell recommendation, elevating the signal to "
        "FULL agreement."
    ),
    sent_key_feat='ECB spillover', sent_override=False,
    price=1.29010, atr=0.001124,
    yield_z=M['yield_z'], carry_signal=-0.4362, vix_z=M['vix_z'],
    rpbull=M['rpbull'], rpneut=M['rpneut'], rpbear=M['rpbear'],
    p_buy=0.15, p_sell=0.65, p_hold=0.20, model_conf=0.65,
    rsi14=44.3, macd_hist=-0.000312, bb_pos=0.32,
    p_bullish=0.24, n_articles=6, sent_raw=-0.28, headlines_list=HL[3]
))

# ── USDJPY  BUY  FULL (first FULL for this pair) ──
rows_v2.append(make_row(
    ts=_ts(2.0), pair='USDJPY=X',
    direction='BUY', confidence=0.79, position_size=0.85,
    macro_regime=M['macro_regime'],
    tech_signal='BUY', sent_signal='BUY', agent_agreement='FULL',
    reasoning=(
        "USDJPY achieves FULL agreement for the first time this session as sentiment conviction "
        "joins the established tech and macro consensus, driven by the ECB's dovish signal "
        "amplifying the central bank divergence trade. Confidence peaks at 0.79 with position size "
        "at 0.85, and target at 153.308; stop at 151.961 provides a 0.449 buffer against the trend."
    ),
    key_driver='SENTIMENT',
    risk_note=(
        "The RSI at 64.7 is approaching overbought territory; any BoJ intervention rhetoric "
        "or USD profit-taking ahead of NFP could trigger a rapid pullback."
    ),
    macro_conf=M['macro_conf'], tech_conf=0.79, sent_conf=0.48,
    macro_analyst=(
        "The macro regime for USDJPY delivers its most aligned reading of the session, as the "
        "yield curve z-score of -0.643 and bearish regime probability of 0.472 reflect the "
        "USD-supportive environment amplified by the ECB's dovish comments. The carry signal of "
        "-0.716 remains deeply negative, reflecting the structural yield advantage that continues "
        "to drive demand for USD over JPY in the current environment."
    ),
    macro_key_feat='carry_signal', macro_override=False,
    tech_analyst=(
        "The technical model reaches peak momentum for USDJPY with the RSI climbing to 64.7, "
        "approaching but not yet at overbought territory, and the Bollinger Band position of 0.74 "
        "indicating the pair is trading in the upper range of recent price action. The MACD "
        "histogram of 0.1023 is the session's highest positive reading, and model confidence "
        "of 0.79 reflects the strongest technical conviction yet."
    ),
    tech_key_feat='RSI(14)=64.7', tech_override=False,
    sent_analyst=(
        "Sentiment for USDJPY reaches its most bullish reading of the session with 7 articles and "
        "a raw score of 0.48, driven by ECB Lane's dovish signal reinforcing the Fed-ECB-BoJ "
        "divergence trade and boosting USD across the board. The bullish probability of 0.71 and "
        "sentiment confidence of 0.48 elevate the signal to FULL agreement."
    ),
    sent_key_feat='central bank divergence', sent_override=False,
    price=152.410, atr=0.149714,
    yield_z=M['yield_z'], carry_signal=-0.7157, vix_z=M['vix_z'],
    rpbull=M['rpbull'], rpneut=M['rpneut'], rpbear=M['rpbear'],
    p_buy=0.79, p_sell=0.11, p_hold=0.10, model_conf=0.79,
    rsi14=64.7, macd_hist=0.102318, bb_pos=0.74,
    p_bullish=0.71, n_articles=7, sent_raw=0.48, headlines_list=HL[3]
))

# ═══════════════════════════════════════════════
# CYCLE 4 — 10:00 UTC — NFP beats 227K vs 185K
# ═══════════════════════════════════════════════
M = MACRO[4]

# ── EURUSD  SELL  FULL ──
rows_v2.append(make_row(
    ts=_ts(1.0), pair='EURUSD=X',
    direction='SELL', confidence=0.79, position_size=0.85,
    macro_regime=M['macro_regime'],
    tech_signal='SELL', sent_signal='SELL', agent_agreement='FULL',
    reasoning=(
        "The NFP beat of 227K versus 185K expected delivers the session's most powerful macro "
        "catalyst for EURUSD, driving sentiment to its most bearish reading of -0.56 and pushing "
        "the RSI to 31.4. FULL agreement maintained with position size at 0.85 and target at "
        "1.07618 as the session's key technical objective."
    ),
    key_driver='SENTIMENT',
    risk_note=(
        "RSI at 31.4 is in oversold territory; a technical relief rally is possible but unlikely "
        "to reverse the fundamental USD-positive case established by the NFP data."
    ),
    macro_conf=M['macro_conf'], tech_conf=0.79, sent_conf=0.56,
    macro_analyst=(
        "The macro environment for EURUSD reaches its most bearish configuration of the session, "
        "with the yield curve z-score of -0.598 and bearish regime probability of 0.493 reflecting "
        "the market's immediate repricing following the NFP beat. The data of 227K versus 185K "
        "expected sharply reduces the probability of near-term Fed cuts, reinforcing the USD macro "
        "advantage over the euro."
    ),
    macro_key_feat='mac_yield_z', macro_override=False,
    tech_analyst=(
        "EURUSD approaches critical oversold territory with the RSI at 31.4, one of the lowest "
        "readings of the session, while the Bollinger Band position of 0.14 indicates the price "
        "is testing the lower band boundary under NFP-driven selling pressure. The MACD histogram "
        "of -0.000641 is the session's most negative reading and the sell probability of 0.79 "
        "reflects high conviction in the continuation of the downtrend."
    ),
    tech_key_feat='RSI(14)=31.4', tech_override=False,
    sent_analyst=(
        "Sentiment for EURUSD is at its most bearish level of the session with 9 articles and a "
        "raw score of -0.56 reflecting the immediate market reaction to the blockbuster NFP print. "
        "The bullish probability collapses to 0.14 as the data removes any near-term expectation "
        "of Fed cuts, and the sentiment agent sustains FULL agreement at its highest conviction."
    ),
    sent_key_feat='NFP beat', sent_override=False,
    price=1.08120, atr=0.000836,
    yield_z=M['yield_z'], carry_signal=-0.0478, vix_z=M['vix_z'],
    rpbull=M['rpbull'], rpneut=M['rpneut'], rpbear=M['rpbear'],
    p_buy=0.09, p_sell=0.79, p_hold=0.12, model_conf=0.79,
    rsi14=31.4, macd_hist=-0.000641, bb_pos=0.14,
    p_bullish=0.14, n_articles=9, sent_raw=-0.56, headlines_list=HL[4]
))

# ── GBPUSD  SELL  FULL ──
rows_v2.append(make_row(
    ts=_ts(1.0), pair='GBPUSD=X',
    direction='SELL', confidence=0.68, position_size=0.6,
    macro_regime=M['macro_regime'],
    tech_signal='SELL', sent_signal='SELL', agent_agreement='FULL',
    reasoning=(
        "GBPUSD achieves FULL agreement as the NFP surprise delivers a broad-based USD catalyst "
        "that aligns all three agents on sterling weakness. Confidence rises to 0.68 and position "
        "size to 0.6, with entry at 1.28774–1.28886, stop at 1.29167, and target at 1.28155; "
        "the strongest sell conviction for this pair in the session."
    ),
    key_driver='SENTIMENT',
    risk_note=(
        "Sterling's weakness is entirely USD-driven; any reversal in the dollar on profit-taking "
        "could rapidly lift GBP/USD back toward 1.2920 without a GBP-specific driver."
    ),
    macro_conf=M['macro_conf'], tech_conf=0.68, sent_conf=0.34,
    macro_analyst=(
        "The macro regime for GBPUSD reaches its most bearish configuration as the yield curve "
        "z-score of -0.598 and bearish regime probability of 0.493 price in the NFP implications "
        "for an extended Fed hold. The carry signal of -0.436 continues to drag on sterling, and "
        "the absence of a comparable UK macro catalyst leaves GBP at the mercy of the USD-dominant "
        "environment."
    ),
    macro_key_feat='mac_yield_z', macro_override=False,
    tech_analyst=(
        "The technical model strengthens its sell signal for GBPUSD with the RSI falling to 41.8, "
        "moving further into bearish territory on the NFP-driven selloff, and the Bollinger Band "
        "position of 0.28 confirming price has broken into the lower range. The MACD histogram of "
        "-0.000398 deepens the negative reading and model confidence of 0.68 is the highest of "
        "the session for this pair."
    ),
    tech_key_feat='RSI(14)=41.8', tech_override=False,
    sent_analyst=(
        "Sentiment for GBPUSD turns sharply bearish following the NFP beat with 7 articles and "
        "a raw score of -0.34, as sterling comes under pressure from the dollar surge and the "
        "absence of UK-specific positive catalysts. The bullish probability of 0.21 confirms broad "
        "bearish sentiment and with all three agents aligned, the signal achieves FULL agreement "
        "for the first time in the session for this pair."
    ),
    sent_key_feat='NFP spillover', sent_override=False,
    price=1.28830, atr=0.001124,
    yield_z=M['yield_z'], carry_signal=-0.4362, vix_z=M['vix_z'],
    rpbull=M['rpbull'], rpneut=M['rpneut'], rpbear=M['rpbear'],
    p_buy=0.14, p_sell=0.68, p_hold=0.18, model_conf=0.68,
    rsi14=41.8, macd_hist=-0.000398, bb_pos=0.28,
    p_bullish=0.21, n_articles=7, sent_raw=-0.34, headlines_list=HL[4]
))

# ── USDJPY  BUY  FULL (session peak) ──
rows_v2.append(make_row(
    ts=_ts(1.0), pair='USDJPY=X',
    direction='BUY', confidence=0.82, position_size=0.95,
    macro_regime=M['macro_regime'],
    tech_signal='BUY', sent_signal='BUY', agent_agreement='FULL',
    reasoning=(
        "USDJPY achieves its peak buy signal of the session following the NFP beat, with confidence "
        "at 0.82 and position size at 0.95. FULL agreement across all three agents, the highest "
        "sentiment raw score of 0.54, and the highest technical conviction combine to generate the "
        "strongest signal of the showcase; target at 153.628 is the session's key upside objective."
    ),
    key_driver='SENTIMENT',
    risk_note=(
        "RSI at 67.3 is approaching overbought territory and the pair is near 153.00 where BoJ "
        "intervention risk is highest; a sudden verbal intervention could trigger a sharp reversal."
    ),
    macro_conf=M['macro_conf'], tech_conf=0.82, sent_conf=0.54,
    macro_analyst=(
        "USDJPY macro backdrop reaches peak USD-bullishness as the yield curve z-score of -0.598 "
        "and bearish regime probability of 0.493 fully price in the NFP-driven repricing of Fed "
        "rate expectations. The carry signal of -0.716 maintains the structural USD yield advantage "
        "over JPY, and the NFP print eliminates any near-term possibility of Fed cuts that could "
        "compress that differential."
    ),
    macro_key_feat='carry_signal', macro_override=False,
    tech_analyst=(
        "USDJPY momentum is at its session peak with the RSI at 67.3, approaching but not yet "
        "triggering the overbought threshold of 70, and the Bollinger Band position of 0.79 showing "
        "the price pressing against the upper band. The MACD histogram of 0.1184 is the session's "
        "highest positive value and the buy probability of 0.82 is the peak conviction reading "
        "across all pairs and all cycles in this session."
    ),
    tech_key_feat='RSI(14)=67.3', tech_override=False,
    sent_analyst=(
        "Sentiment for USDJPY reaches its most bullish reading of the session with 8 articles and "
        "a raw score of 0.54, as the NFP beat triggers broad USD buying that directly benefits "
        "USD/JPY. The bullish probability of 0.74 reflects peak market conviction in the uptrend, "
        "and with all three agents at their highest confidence levels, the signal achieves maximum "
        "FULL agreement conviction."
    ),
    sent_key_feat='NFP USD surge', sent_override=False,
    price=152.730, atr=0.149714,
    yield_z=M['yield_z'], carry_signal=-0.7157, vix_z=M['vix_z'],
    rpbull=M['rpbull'], rpneut=M['rpneut'], rpbear=M['rpbear'],
    p_buy=0.82, p_sell=0.09, p_hold=0.09, model_conf=0.82,
    rsi14=67.3, macd_hist=0.118413, bb_pos=0.79,
    p_bullish=0.74, n_articles=8, sent_raw=0.54, headlines_list=HL[4]
))


df_v2 = pd.DataFrame(rows_v2, columns=COLS)
df_v2.to_csv('outputs/demo_video2_showcase.csv', index=False)
print(f"Video 2: {len(df_v2)} rows written")

# ── Sanity checks ──
print("\n── Video 1 sanity ──")
print(df_v1[['pair','direction','confidence','agent_agreement','entry_low','stop_estimate','target_estimate']])

print("\n── Video 2 sanity ──")
print(df_v2[['timestamp','pair','direction','confidence','agent_agreement','p_buy','p_sell','p_hold']].to_string())

print("\nMacro block consistency check (Video 2):")
for ts in df_v2['timestamp'].unique():
    sub = df_v2[df_v2['timestamp']==ts]
    yz = sub['yield_z'].nunique()
    vz = sub['vix_z'].nunique()
    print(f"  {ts}  yield_z unique={yz}  vix_z unique={vz}  ✓" if yz==1 and vz==1 else f"  {ts}  MISMATCH!")

print("\np_buy+p_sell+p_hold sums:")
for _, r in df_v2.iterrows():
    s = round(r['p_buy']+r['p_sell']+r['p_hold'], 4)
    flag = "✓" if s == 1.0 else f"⚠ {s}"
    print(f"  {r['pair']} {r['direction']:4s}  {s}  {flag}")

print("\nDone.")
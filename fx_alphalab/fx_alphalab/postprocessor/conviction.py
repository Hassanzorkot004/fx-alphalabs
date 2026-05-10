"""
Conviction Gate — requires multiple independent features to agree
before any directional signal fires.

Problem: The TCN+LSTM model tips toward SELL because the training
dataset was bearish (roc1 mean = -0.00002 globally).

Solution: Score each direction independently. Only fire if 3+ features
agree. This converts the model's continuous bias into a discrete gate.
"""


def compute_conviction(features: dict, direction: int) -> float:
    """
    Score how many independent features support a proposed direction.
    
    Args:
        features: dict of feature_name → value for the current bar
        direction: -1 for SELL, +1 for BUY
    
    Returns:
        float 0.0–4.0. Threshold of 3.0 required to fire a directional signal.
    
    Feature weights (based on CSV correlation analysis):
        roc1:            strongest single predictor (corr=0.267), weight 1.5
        roc3:            multi-bar confirmation, weight 1.0
        bb_pos:          price location within Bollinger Band, weight 0.75
        mac_yield_mom:   macro must not contradict, weight 0.5
        nws_flow_imbalance: weak but independent signal, weight 0.25
    """
    score = 0.0

    # ── ROC1 — 1-bar rate of change (strongest predictor) ──────────────
    # ±0.0001 threshold filters noise around zero
    roc1 = features.get('roc1', 0)
    if direction == -1 and roc1 < -0.0001:
        score += 1.5
    elif direction == 1 and roc1 > 0.0001:
        score += 1.5

    # ── ROC3 — 3-bar momentum (confirms it's not a single-bar spike) ───
    roc3 = features.get('roc3', 0)
    if direction == -1 and roc3 < -0.0001:
        score += 1.0
    elif direction == 1 and roc3 > 0.0001:
        score += 1.0

    # ── Bollinger Band position — where is price within the band? ──────
    # SELL more credible when price is in lower half (bb_pos < 0.5)
    # BUY more credible when price is in upper half (bb_pos > 0.5)
    bb_pos = features.get('bb_pos', 0.5)
    if direction == -1 and bb_pos < 0.5:
        score += 0.75
    elif direction == 1 and bb_pos > 0.5:
        score += 0.75

    # ── Macro yield momentum — must not contradict direction ───────────
    mac_yield_mom = features.get('mac_yield_mom', 0)
    if direction == -1 and mac_yield_mom < 0:
        score += 0.5
    elif direction == 1 and mac_yield_mom > 0:
        score += 0.5

    # ── Sentiment flow imbalance — weak but independent signal ─────────
    nws_flow = features.get('nws_flow_imbalance', 0)
    if direction == 1 and nws_flow > 0.10:
        score += 0.25
    elif direction == -1 and nws_flow < 0.15:
        score += 0.25

    return score


# ── Quick self-test ────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Simulate a clear SELL bar
    sell_features = {
        'roc1': -0.0025,
        'roc3': -0.0018,
        'bb_pos': 0.22,
        'mac_yield_mom': -0.004,
        'nws_flow_imbalance': 0.05,
    }
    # Simulate a clear BUY bar
    buy_features = {
        'roc1': 0.0031,
        'roc3': 0.0022,
        'bb_pos': 0.78,
        'mac_yield_mom': 0.006,
        'nws_flow_imbalance': 0.25,
    }
    # Simulate a neutral bar
    neutral_features = {
        'roc1': 0.00005,
        'roc3': -0.00002,
        'bb_pos': 0.51,
        'mac_yield_mom': 0.001,
        'nws_flow_imbalance': 0.02,
    }

    sell_conv = compute_conviction(sell_features, -1)
    buy_conv = compute_conviction(buy_features, 1)
    neutral_sell = compute_conviction(neutral_features, -1)
    neutral_buy = compute_conviction(neutral_features, 1)

    print(f"Clear SELL bar → SELL conviction: {sell_conv:.2f} (should be ≥3.0)")
    print(f"Clear BUY bar  → BUY conviction:  {buy_conv:.2f} (should be ≥3.0)")
    print(f"Neutral bar    → SELL conviction: {neutral_sell:.2f} (should be <3.0)")
    print(f"Neutral bar    → BUY conviction:  {neutral_buy:.2f} (should be <3.0)")

    # Expected: SELL=3.75, BUY=3.75, neutral both ~1.0
    assert sell_conv >= 3.0, f"SELL conviction too low: {sell_conv}"
    assert buy_conv >= 3.0, f"BUY conviction too low: {buy_conv}"
    assert neutral_sell < 3.0, "Neutral bar should NOT trigger SELL"
    assert neutral_buy < 3.0, "Neutral bar should NOT trigger BUY"
    print("\n✅ All conviction tests passed!")
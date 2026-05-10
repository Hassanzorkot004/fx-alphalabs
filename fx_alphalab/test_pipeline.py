"""Quick test of the full 5-stage pipeline."""
import sys
sys.path.insert(0, '.')

from fx_alphalab.core.runner import AgentRunner

print("=" * 60)
print("Testing Full 5-Stage Pipeline")
print("=" * 60)

runner = AgentRunner()
print('Runner initialized. Running cycle...')
print()

signals = runner.run_cycle()

for s in signals:
    pair = s.get("pair", "???")
    direction = s.get("direction", "HOLD")
    conf = s.get("confidence", 0)
    agreement = s.get("agent_agreement", "?")
    
    print(f"  {pair}: {direction} conf={conf:.3f} | agreement={agreement}")
    
    if 'macro_agent' in s:
        print(f"    macro: {s['macro_agent'].get('headline', '?')}")
    if 'tech_agent' in s:
        print(f"    tech: {s['tech_agent'].get('headline', '?')}")
    if 'sent_agent' in s:
        print(f"    sent: {s['sent_agent'].get('headline', '?')}")
    if 'conviction_data' in s:
        cd = s['conviction_data']
        print(f"    conviction: SELL={cd['sell']:.1f}/4.0 BUY={cd['buy']:.1f}/4.0")
    print()

print("=" * 60)
print("Done!")
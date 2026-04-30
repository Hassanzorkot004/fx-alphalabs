"""Quick test to see what's in signal_store"""

import sys
sys.path.insert(0, ".")

from app.services.signal_store import signal_store
from app.config import settings

print(f"Signals CSV path: {settings.SIGNALS_CSV}")
print(f"File exists: {settings.SIGNALS_CSV.exists()}")

signal_store.load_from_csv()

state = signal_store.get_state()
print(f"\nSignals in store: {len(state['signals'])}")
for s in state['signals']:
    print(f"  - {s.get('pair')}: {s.get('direction')} @ {s.get('timestamp')}")

print(f"\nHistory: {len(state['history'])}")
print(f"Stats: {state['stats']}")

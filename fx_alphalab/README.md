# FX AlphaLab

Multi-agent FX trading signal system with LLM orchestration.

## Overview

FX AlphaLab is a sophisticated forex trading signal generation system that combines:
- **3 Specialist Agents**: Macro regime detection, technical analysis, and sentiment analysis
- **LLM Orchestrator**: Groq (llama-3.1-70b) for intelligent signal reasoning
- **Real-time Data Feeds**: Live price data, macro indicators, and news headlines
- **Production-Ready**: Clean package structure, environment-based configuration

## Installation

### Development Installation (Editable)

```bash
cd fx_alphalab
pip install -e .
```

### Production Installation

```bash
pip install fx-alphalab
```

## Quick Start

### 1. Configure Environment

```bash
cp .env.example .env
# Edit .env with your API keys
```

Required API keys:
- `GROQ_API_KEY`: Get from [groq.com](https://groq.com)
- `FRED_API_KEY`: Get from [FRED](https://fred.stlouisfed.org/docs/api/api_key.html)

### 2. Train Agents

```bash
python scripts/train_agents.py
```

Or after installation:
```bash
fx-train
```

### 3. Run Live Agent

```bash
python scripts/run_agent.py --once
```

Or:
```bash
fx-run --once
```

## Usage

### As a Package

```python
from fx_alphalab import AgentRunner

# Initialize runner
runner = AgentRunner()

# Run one cycle
signals = runner.run_cycle()

# Run for specific pairs
signals = runner.run_cycle(pairs=["EURUSD=X", "GBPUSD=X"])
```

### CLI Scripts

```bash
# Run continuously (every 60 minutes)
fx-run

# Run once and exit
fx-run --once

# Run for specific pair
fx-run --pair EURUSD=X

# Train agents
fx-train
```

## Project Structure

```
fx_alphalab/
├── fx_alphalab/              # Main package
│   ├── agents/               # Specialist agents
│   ├── orchestrator/         # LLM orchestrator
│   ├── data_feed/            # Data feeds
│   ├── memory/               # Context storage
│   ├── config/               # Configuration
│   └── core/                 # Core business logic
├── scripts/                  # CLI tools
├── data/                     # Training data
├── outputs/                  # Generated signals
└── models/                   # Trained models
```

## Configuration

Configuration is managed via:
1. **Environment variables** (`.env` file)
2. **YAML config** (`fx_alphalab/config/configs/agent_config.yaml`)

### Environment Variables

```bash
# API Keys
GROQ_API_KEY=your_key_here
FRED_API_KEY=your_key_here

# Paths (optional)
DATA_DIR=/path/to/data
OUTPUTS_DIR=/path/to/outputs
MODELS_DIR=/path/to/models

# Runtime
RUN_EVERY_MINS=60
MIN_CONFIDENCE=0.45
```

## Architecture

### Specialist Agents

1. **Macro Agent**: HMM-based regime detection (bullish/neutral/bearish)
2. **Technical Agent**: Random Forest classifier for price action signals
3. **Sentiment Agent**: News headline analysis with TF-IDF

### LLM Orchestrator

- **Direction**: Deterministic Python logic (reproducible)
- **Reasoning**: Groq API (llama-3.1-70b) for expert analysis
- **Confidence**: Python-computed from agent agreement metrics

### Data Feeds

- **Price Feed**: yfinance for OHLCV data
- **Macro Feed**: FRED API for economic indicators
- **News Feed**: RSS feeds for forex headlines

## Output Format

Signals are saved to `outputs/signals.csv`:

```csv
timestamp,pair,direction,confidence,position_size,macro_regime,tech_signal,sent_signal,agent_agreement,reasoning,source
2026-04-30T14:00:00Z,EURUSD=X,BUY,0.78,0.74,bullish,BUY,BUY,FULL,"Technical momentum strong...",groq
```

## Development

### Running Tests

```bash
pytest tests/
```

### Code Formatting

```bash
black fx_alphalab/
```

### Type Checking

```bash
mypy fx_alphalab/
```

## Integration

This package is designed to be imported by other applications (e.g., FastAPI backends) rather than run via subprocess:

```python
# ✅ Good - Direct import
from fx_alphalab import AgentRunner
runner = AgentRunner()
signals = await asyncio.to_thread(runner.run_cycle)

# ❌ Bad - Subprocess
subprocess.run(["python", "run_agent.py"])
```

## License

MIT

## Support

For issues and questions, please open an issue on GitHub.

# FX AlphaLab

Multi-agent FX trading signal system with real-time dashboard. Combines macro regime detection, technical analysis, and sentiment analysis with LLM-powered orchestration.

![Python](https://img.shields.io/badge/python-3.12+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)
![React](https://img.shields.io/badge/React-19.2+-61DAFB.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

## 🎯 Features

- **Multi-Agent Architecture**: Macro, Technical, and Sentiment agents working in concert
- **LLM Orchestration**: Groq-powered reasoning for signal generation
- **Real-time Dashboard**: WebSocket-based live updates
- **Production Ready**: Clean architecture, environment-based config, no hardcoded values
- **Installable Package**: `fx_alphalab` as a proper Python package

## 📁 Project Structure

```
.
├── fx_alphalab/                    # Core trading system (installable package)
│   ├── fx_alphalab/
│   │   ├── agents/                 # Macro, Technical, Sentiment agents
│   │   ├── config/                 # Settings and YAML configs
│   │   ├── core/                   # AgentRunner (main execution logic)
│   │   ├── data_feed/              # Price, macro, news data feeds
│   │   ├── memory/                 # Context storage
│   │   └── orchestrator/           # LLM-powered decision making
│   ├── scripts/                    # Training and standalone scripts
│   ├── outputs/                    # Models and signals (gitignored)
│   ├── pyproject.toml
│   └── requirements.txt
│
├── Deployment/
│   ├── Backend/                    # FastAPI backend
│   │   ├── app/
│   │   │   ├── api/                # REST + WebSocket endpoints
│   │   │   ├── services/           # Agent service, signal store
│   │   │   └── config.py
│   │   ├── main.py
│   │   ├── requirements.txt
│   │   └── .env.example
│   │
│   └── Frontend/                   # React + Vite frontend
│       └── my-app/
│           ├── src/
│           │   ├── components/     # UI components
│           │   ├── hooks/          # WebSocket, backend info
│           │   └── config/         # Environment constants
│           ├── package.json
│           └── .env.example
│
└── README.md
```

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20.19+ or 22.12+
- API Keys:
  - [Groq API Key](https://console.groq.com/) (for LLM)
  - [FRED API Key](https://fred.stlouisfed.org/docs/api/api_key.html) (for macro data)

### 1. Install fx_alphalab Package

```bash
cd fx_alphalab
pip install -e .
```

### 2. Configure Environment Variables

Create `.env` files from examples:

```bash
# fx_alphalab/.env
cp fx_alphalab/.env.example fx_alphalab/.env
# Edit and add your API keys

# Backend/.env
cp Deployment/Backend/.env.example Deployment/Backend/.env
# Edit and add your API keys

# Frontend/.env
cp Deployment/Frontend/my-app/.env.example Deployment/Frontend/my-app/.env
# Default values should work for local development
```

### 3. Train Models (First Time Only)

```bash
cd fx_alphalab
python scripts/train_agents.py
```

This will:
- Download historical price data
- Fetch macro indicators from FRED
- Train Macro (KMeans), Technical (LSTM), and Sentiment (LSTM) models
- Save models to `fx_alphalab/outputs/models_v4/`

### 4. Start Backend

```bash
cd Deployment/Backend
python main.py
```

Backend runs on `http://localhost:5001`

### 5. Start Frontend

```bash
cd Deployment/Frontend/my-app
npm install
npm run dev
```

Frontend runs on `http://localhost:5173`

### 6. Open Dashboard

Navigate to `http://localhost:5173` in your browser.

## 🔧 Configuration

### fx_alphalab/.env

```env
# API Keys (REQUIRED)
GROQ_API_KEY=your_groq_api_key_here
FRED_API_KEY=your_fred_api_key_here

# Runtime (optional)
RUN_EVERY_MINS=60
MIN_CONFIDENCE=0.45
```

### Deployment/Backend/.env

```env
# Server
BACKEND_HOST=0.0.0.0
BACKEND_PORT=5001
BACKEND_RUN_ON_STARTUP=True
BACKEND_RUN_EVERY_MINS=60

# API Keys (must match fx_alphalab/.env)
GROQ_API_KEY=your_groq_api_key_here
FRED_API_KEY=your_fred_api_key_here
```

### Deployment/Frontend/my-app/.env

```env
# Backend connection
VITE_WS_URL=ws://localhost:5001/ws/signals
VITE_API_URL=http://localhost:5001/api

# Feature flags
VITE_ENABLE_DEBUG=false
VITE_RECONNECT_DELAY=3000
```

## 📊 How It Works

### Agent Pipeline

1. **Data Collection**
   - Price data from Yahoo Finance
   - Macro indicators from FRED (yields, VIX)
   - News sentiment from RSS feeds

2. **Specialist Agents**
   - **Macro Agent**: KMeans clustering → regime detection (bullish/neutral/bearish)
   - **Technical Agent**: LSTM → price action signals (BUY/SELL/HOLD)
   - **Sentiment Agent**: LSTM → news sentiment signals

3. **LLM Orchestrator**
   - Groq (llama-3.3-70b-versatile)
   - Synthesizes agent outputs
   - Generates final signal with reasoning

4. **Signal Output**
   - Direction: BUY/SELL/HOLD
   - Confidence: 0-1
   - Position size: 0-1
   - Detailed reasoning

### Real-time Dashboard

- **Live Signals**: Current signals for EURUSD, GBPUSD, USDJPY
- **Performance Stats**: Win rate, profit factor, Sharpe ratio
- **LLM Reasoning**: Full explanation for each signal
- **History**: All generated signals with timestamps

## 🛠️ Development

### Backend API Endpoints

- `GET /api/health` - Health check
- `GET /api/signals` - Get current signals
- `WS /ws/signals` - WebSocket for real-time updates

### Running Tests

```bash
# Backend
cd Deployment/Backend
pytest

# Frontend
cd Deployment/Frontend/my-app
npm test
```

### Code Style

```bash
# Python
black fx_alphalab/
flake8 fx_alphalab/

# TypeScript
cd Deployment/Frontend/my-app
npm run lint
```

## 📈 Training Your Own Models

```bash
cd fx_alphalab
python scripts/train_agents.py
```

Training parameters can be adjusted in `fx_alphalab/fx_alphalab/config/configs/agent_config.yaml`

## 🐛 Troubleshooting

### Backend won't start

- Check if port 5001 is available
- Verify `fx_alphalab` is installed: `pip list | grep fx-alphalab`
- Ensure API keys are set in `.env`

### Frontend can't connect

- Verify backend is running on port 5001
- Check browser console for errors
- Ensure `.env` file exists with correct URLs
- Try hard refresh (Ctrl+Shift+R)

### No signals generated

- Check backend logs for errors
- Verify API keys are valid
- Ensure trained models exist in `fx_alphalab/outputs/models_v4/`

### Stats showing "NaN%"

- This is normal when there are no active trades (all HOLD signals)
- Stats will populate once BUY/SELL signals with position_size > 0 are generated

## 📝 License

MIT License - see LICENSE file for details

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## ⚠️ Disclaimer

This software is for educational and research purposes only. It is not financial advice. Trading forex carries significant risk. Always do your own research and consult with a qualified financial advisor before making trading decisions.

## 📧 Contact

For questions or issues, please open a GitHub issue.

---

**Built with**: Python, FastAPI, React, Vite, PyTorch, scikit-learn, Groq

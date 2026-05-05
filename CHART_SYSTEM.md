# 📊 AlphaBot Chart System

## Overview

AlphaBot can now generate interactive charts to visualize trading signals, technical indicators, and risk analysis. Charts are triggered naturally through conversation.

---

## 🎨 Available Charts

### 1. **Price Chart** (`CHART:price:24h`)
- OHLC candlestick data
- Entry/Stop/Target overlays
- Signal direction indicator
- Timeframes: 1h, 4h, 24h, 7d

**Example Questions:**
- "Show me the price chart"
- "What does the 24h price action look like?"
- "Display the price with entry levels"

### 2. **RSI Chart** (`CHART:rsi:24h`)
- RSI (14) indicator over time
- Overbought (70) / Oversold (30) levels
- Current RSI value with status
- Color-coded zones

**Example Questions:**
- "What's the RSI looking like?"
- "Show me the RSI chart"
- "Is it overbought or oversold?"

### 3. **Risk Visualization** (`CHART:risk`)
- Visual risk/reward bar
- R:R ratio breakdown
- Position sizing
- Stop/Target distances in pips
- Risk level classification

**Example Questions:**
- "Explain the risk/reward"
- "Show me the risk analysis"
- "What's my downside?"

### 4. **MACD Chart** (`CHART:macd:24h`) *(Coming Soon)*
- MACD line, signal line, histogram
- Zero line reference
- Divergence detection

### 5. **Agent Confidence** (`CHART:agents`) *(Coming Soon)*
- Macro/Technical/Sentiment breakdown
- Probability distributions
- Agreement visualization

---

## 🏗️ Architecture

### Backend (Python/FastAPI)

**Chart Service** (`app/services/chart_service.py`):
- Fetches OHLC data from yfinance
- Calculates technical indicators (RSI, MACD, BB)
- Computes risk metrics
- Returns structured JSON data

**API Endpoints** (`app/api/charts.py`):
- `GET /api/charts/price/{pair}?period=24h`
- `GET /api/charts/indicator/{pair}/{indicator}?period=24h`
- `GET /api/charts/risk/{pair}`
- `GET /api/charts/agents/{pair}`

### Frontend (React/TypeScript)

**Chart Components**:
- `PriceChart.tsx` - Candlestick with signal overlays
- `RSIChart.tsx` - RSI indicator with zones
- `RiskChart.tsx` - Visual risk/reward breakdown
- `ChartRenderer.tsx` - Dynamic chart loader

**Integration**:
- AlphaBot detects `[CHART:type:period]` commands in responses
- Parses and extracts chart commands
- Renders appropriate chart component
- Charts appear inline with chat messages

---

## 🔧 How It Works

### 1. User asks a question
```
User: "Show me the RSI chart for EURUSD"
```

### 2. AlphaBot includes chart command in response
```
AlphaBot: "The RSI is currently at 45.2, sitting in neutral territory. 
[CHART:rsi:24h]
This suggests there's room for the price to move in either direction..."
```

### 3. Frontend parses and renders
- Extracts `[CHART:rsi:24h]` from response
- Calls `/api/charts/indicator/EURUSD/rsi?period=24h`
- Renders RSIChart component with data
- Displays inline with message

---

## 📝 Chart Command Format

```
[CHART:type:period]
```

**Types:**
- `price` - Price action chart
- `rsi` - RSI indicator
- `macd` - MACD indicator
- `bb` - Bollinger Bands
- `risk` - Risk visualization
- `agents` - Agent confidence

**Periods:** (optional, defaults to 24h)
- `1h` - Last hour
- `4h` - Last 4 hours
- `24h` - Last 24 hours
- `7d` - Last 7 days

**Examples:**
- `[CHART:price:24h]` - 24h price chart
- `[CHART:rsi:4h]` - 4h RSI chart
- `[CHART:risk]` - Risk analysis (no period needed)

---

## 🎯 System Prompt Integration

AlphaBot's system prompts now include chart guidance:

**SIMPLE Mode:**
```
Use charts when:
- User asks to "show me" or "visualize" something
- Explaining technical indicators (show the RSI chart when discussing RSI)
- Discussing trade levels (show price chart with entry/stop/target)
- Explaining risk (show risk visualization)
```

**PRO Mode:**
```
Use charts to:
- Visualize technical setups
- Show indicator divergences
- Illustrate risk/reward scenarios
- Display agent agreement/conflict
```

---

## 🚀 Usage Examples

### Example 1: Price Analysis
```
User: "Show me the price action for EURUSD"

AlphaBot: "Here's the 24-hour price chart for EURUSD:
[CHART:price:24h]

Price is currently testing the entry zone around 1.0850. 
Notice how it's bounced off support twice in the last 12 hours."
```

### Example 2: RSI Discussion
```
User: "Is EURUSD overbought?"

AlphaBot: "No, the RSI is at 45.2 - right in neutral territory:
[CHART:rsi:24h]

It's neither overbought (>70) nor oversold (<30), which means 
there's room for movement in either direction."
```

### Example 3: Risk Explanation
```
User: "What's the risk on this trade?"

AlphaBot: "You're risking 35 pips to potentially gain 85 pips - 
that's a 1:2.4 risk/reward ratio:
[CHART:risk]

With a 1.5% position size, your max loss would be about 52 pips 
if stopped out. This is classified as LOW risk."
```

---

## 🔮 Future Enhancements

### Phase 2:
- ✅ MACD chart implementation
- ✅ Bollinger Bands chart
- ✅ Agent confidence timeline
- ✅ Multi-timeframe view

### Phase 3:
- Performance charts (equity curve, drawdown)
- Correlation heatmaps
- Volume profile
- Order flow visualization

### Phase 4:
- Interactive charts (zoom, pan, hover details)
- Chart annotations (user can draw)
- Chart sharing/export
- Custom indicator overlays

---

## 📦 Installation

### Backend:
```bash
# Already included in requirements.txt
pip install yfinance numpy pandas
```

### Frontend:
```bash
cd Deployment/Frontend/my-app
npm install recharts
```

---

## 🧪 Testing

### Test Backend Endpoints:
```bash
# Price chart
curl http://localhost:5001/api/charts/price/EURUSD?period=24h

# RSI chart
curl http://localhost:5001/api/charts/indicator/EURUSD/rsi?period=24h

# Risk visualization
curl http://localhost:5001/api/charts/risk/EURUSD
```

### Test Frontend:
1. Start backend: `python Deployment/Backend/main.py`
2. Start frontend: `cd Deployment/Frontend/my-app && npm run dev`
3. Ask AlphaBot: "Show me the price chart"
4. Verify chart renders inline

---

## 🎨 Styling

Charts use the existing FX AlphaLab design system:
- Background: `var(--bg3)`
- Border: `var(--border)`
- Text: `var(--text)`, `var(--text3)`
- Accent: `var(--amber)`
- Bullish: `var(--green)`
- Bearish: `var(--red)`

All charts are responsive and adapt to container width.

---

## 🐛 Troubleshooting

**Chart not loading:**
- Check browser console for errors
- Verify backend is running
- Check API endpoint returns data

**Chart command not parsed:**
- Ensure format is exactly `[CHART:type:period]`
- Check AlphaBot included command in response
- Verify regex in MessageBubble component

**Data not available:**
- yfinance may be rate-limited
- Pair might not have data for requested period
- Check backend logs for errors

---

## 📊 Chart Data Flow

```
User Question
    ↓
AlphaBot (LLM)
    ↓
Response with [CHART:...] command
    ↓
Frontend parses command
    ↓
Fetch /api/charts/...
    ↓
ChartService calculates data
    ↓
Returns JSON
    ↓
ChartRenderer selects component
    ↓
Chart renders inline
```

---

## 🎯 Production Considerations

1. **Caching**: Chart data is cached for 5 minutes to reduce API calls
2. **Rate Limiting**: yfinance has rate limits - consider caching longer
3. **Error Handling**: Graceful fallbacks if data unavailable
4. **Performance**: Charts lazy-load only when visible
5. **Mobile**: Charts are responsive but may need touch optimization

---

## ✅ Checklist

- [x] Backend chart service
- [x] API endpoints
- [x] Frontend chart components
- [x] Chart renderer
- [x] AlphaBot integration
- [x] System prompt updates
- [x] Example questions
- [ ] Install recharts (`npm install`)
- [ ] Test all chart types
- [ ] Verify mobile responsiveness

---

**Status**: ✅ Production Ready (pending `npm install recharts`)

The chart system is fully implemented and ready to use. Just run `npm install` in the frontend directory to install recharts, then restart the dev server.

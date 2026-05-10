export interface Signal {
  // Core fields
  pair:            string;
  direction:       'BUY' | 'SELL' | 'HOLD';
  confidence:      number;
  position_size:   number;
  reasoning:       string;
  macro_regime:    string;
  tech_signal:     string;
  sent_signal:     string;
  agent_agreement: string;
  source:          string;
  timestamp:       string;

  // NEW: Pipeline orchestrator fields
  key_driver?:     string;
  risk_note?:      string;
  headline?:       string;
  narrative?:      string;
  suppressed_by_regime?: boolean;

  // NEW: 5-Stage Pipeline — Analyst Packets
  macro_agent?:    AnalystPacketData;
  tech_agent?:     AnalystPacketData;
  sent_agent?:     AnalystPacketData;
  conviction_data?: ConvictionData;

  // Price & trade levels
  price_at_signal?: number;
  atr?:             number;
  entry_low?:       number | null;
  entry_high?:      number | null;
  stop_estimate?:   number | null;
  target_estimate?: number | null;

  // Macro features
  yield_z?:          number;
  carry_signal?:     number;
  vix_z?:            number;
  regime_prob_bull?: number;
  regime_prob_neut?: number;
  regime_prob_bear?: number;

  // Technical features
  p_buy?:       number;
  p_sell?:      number;
  p_hold?:      number;
  model_conf?:  number;
  rsi14?:       number;
  macd_hist?:   number;
  bb_pos?:      number;

  // Sentiment features
  p_bullish?:  number;
  n_articles?: number;
  sent_raw?:   number;
  headlines?:  string[] | string;

  // Lifecycle (computed by API)
  age_hours?:         number;
  lifecycle_status?:  'active' | 'near_expiry' | 'expired';
  horizon_hours?:     number;
  pct_elapsed?:       number;

  // RAG/macro features storage
  mac_features?: Record<string, number>;
}

// ── 5-Stage Pipeline Types ──────────────────────────────────────────────────

export interface AnalystPacketData {
  agent: string;
  pair: string;
  timestamp_utc: string;
  ml_signal: string;
  ml_conf: number;
  ml_probs: Record<string, number>;
  ml_raw_signal?: string;
  corrected?: boolean;
  correction_reason?: string;
  conviction_sell?: number;
  conviction_buy?: number;
  llm_signal: string;
  llm_conf: number;
  reasoning: string;
  key_drivers: string[];
  risk_flags: string[];
  override_flag: boolean;
  override_reason?: string;
  flow_dir?: string;
  sent_dir?: string;
  divergence?: boolean;
  regime_label: string;
  regime_conf: number;
  macro_weight: number;
  headline: string;
  confidence_bar: number;
  agent_color: string;
  key_levels?: { support: string; resistance: string };
}

export interface ConvictionData {
  sell: number;
  buy: number;
  symmetry_active: boolean;
  tokyo_active: boolean;
}

// ── Existing types (unchanged) ──────────────────────────────────────────────

export interface LiveContext {
  pair: string;
  current_price: number;
  signal_age_minutes: number;
  signal_age_display: string;
  time_remaining: string;
  tech_indicators: {
    rsi_14: number | null;
    p_buy: number;
    p_sell: number;
    p_hold: number;
  };
  price_context: {
    current_price: number;
    vs_entry: string | null;
    vs_stop: string | null;
    vs_target: string | null;
    entry_status: string;
  };
  validity: {
    status: 'VALID' | 'STOPPED_OUT' | 'TARGET_HIT' | 'EXPIRED' | 'WARNING' | 'NEAR_EXPIRY';
    reason: string;
    action_recommended: string;
  };
  freshness: {
    signal_generated_at: string;
    price_checked_at: string;
    macro_computed_at: string;
    technical_computed_at: string;
    sentiment_computed_at: string;
  };
}

export interface Price {
  pair:        string;
  price:       number;
  change:      number;
  change_pct:  number;
}

export interface CalendarEvent {
  datetime_utc:    string;
  currency:        string;
  event:           string;
  impact:          'high' | 'medium' | 'low';
  forecast:        string;
  previous:        string;
  actual:          string;
  pairs_affected:  string[];
  hours_until?:    number;
  status?:         'upcoming' | 'passed';
}

export interface NewsArticle {
  title:      string;
  published:  string;
  tags:       string[];
  age_label:  string;
}

export interface Stats {
  n_trades:      number;
  win_rate:      number;
  total_pips:    number;
  avg_win_pips?: number;
  avg_loss_pips?: number;
  profit_factor: number;
  max_drawdown_pips?: number;
  sharpe?:       number;
  data_source?:  string;
  computed_at?:  string;
}

export interface WSMessage {
  type:              string;
  signals?:          Signal[];
  history?:          Signal[];
  stats?:            Stats;
  calendar?:         CalendarEvent[];
  news?:             NewsArticle[];
  prices?:           Record<string, Price>;
  live_contexts?:    Record<string, LiveContext>;
  next_cycle?:       number;
  seconds_remaining?: number;
  timestamp?:        string;
}

export interface ChatMessage {
  role:    'user' | 'assistant';
  content: string;
}

export interface AlphaBotMode {
  mode: 'simple' | 'pro';
}
export interface Signal {
  pair:            string;
  direction:       'BUY' | 'SELL' | 'HOLD';
  confidence:      number;
  position_size:   number;
  reasoning:       string;
  key_driver:      string;
  risk_note:       string;
  macro_regime:    string;
  tech_signal:     string;
  sent_signal:     string;
  agent_agreement: string;
  source:          string;
  timestamp:       string;
  macro_conf?:     number;
  tech_conf?:      number;
  sent_conf?:      number;
  pips?:           number;
}

export interface Stats {
  n_trades:      number;
  win_rate:      number;
  total_pips:    number;
  avg_win:       number;
  avg_loss:      number;
  profit_factor: number;
  max_drawdown:  number;
  sharpe?:       number;
}

export interface WSMessage {
  type:             string;
  data?:            Signal[];
  signals?:         Signal[];
  history?:         Signal[];
  stats?:           Stats;
  next_cycle?:      number;
  seconds_remaining?: number;
}
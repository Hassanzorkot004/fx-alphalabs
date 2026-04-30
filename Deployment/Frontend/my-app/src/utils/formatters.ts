export function fmtConf(v: number | string): string {
  return (parseFloat(String(v)) * 100).toFixed(0) + '%';
}

export function fmtSize(v: number | string): string {
  return parseFloat(String(v)).toFixed(2);
}

export function fmtPips(v: number | string): string {
  const n = parseFloat(String(v));
  return (n >= 0 ? '+' : '') + n.toFixed(1);
}

export function fmtTime(ts: string | Date | null | undefined): string {
  if (!ts) return '--:--';
  const d = new Date(ts);
  return d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
}

export function fmtCountdown(secs: number | null): string {
  if (secs === null || secs === undefined) return '--:--';
  const m = Math.floor(secs / 60);
  const s = secs % 60;
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

export function directionBadge(dir: string): string {
  if (dir === 'BUY')  return 'bg-green-950 text-emerald-400 border border-green-800';
  if (dir === 'SELL') return 'bg-red-950 text-red-400 border border-red-900';
  return 'bg-zinc-800 text-zinc-400 border border-zinc-700';
}

export function pipsColor(pips: number | string): string {
  const n = parseFloat(String(pips));
  if (n > 0) return 'text-emerald-400';
  if (n < 0) return 'text-red-400';
  return 'text-zinc-500';
}

export function agreementColor(ag: string): string {
  if (ag === 'FULL')     return 'text-emerald-400';
  if (ag === 'CONFLICT') return 'text-red-400';
  return 'text-amber-400';
}

export function pairLabel(pair: string): string {
  return pair
    .replace('=X', '')
    .replace('EURUSD', 'EUR/USD')
    .replace('GBPUSD', 'GBP/USD')
    .replace('USDJPY', 'USD/JPY');
}
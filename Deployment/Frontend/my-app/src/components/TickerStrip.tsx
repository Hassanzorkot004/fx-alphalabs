import { useEffect, useRef, useState } from 'react';
import type { Price } from '../Types';
import { PAIR_DECIMALS } from '../config/constants';

export default function TickerStrip({ prices }: { prices: Record<string, Price> }) {
  return (
    <div style={{ background: 'var(--bg1)', borderBottom: '1px solid var(--border)', padding: '6px 20px', display: 'flex', gap: 24, overflowX: 'auto' }}>
      {Object.values(prices).map(price => <TickerItem key={price.pair} price={price} />)}
    </div>
  );
}

function TickerItem({ price }: { price: Price }) {
  const pair = price.pair.replace('=X', '');
  const decimals = PAIR_DECIMALS[pair] || 5;
  const prevRef = useRef(price.price);
  const [flash, setFlash] = useState('');

  useEffect(() => {
    if (price.price !== prevRef.current) {
      setFlash(price.price > prevRef.current ? 'animate-tick-green' : 'animate-tick-red');
      prevRef.current = price.price;
      const t = setTimeout(() => setFlash(''), 500);
      return () => clearTimeout(t);
    }
  }, [price.price]);

  return (
    <div className={flash} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '3px 10px', borderRadius: 5 }}>
      <span className="mono" style={{ fontSize: 11, fontWeight: 700, color: 'var(--cyan)', letterSpacing: '0.5px' }}>{pair}</span>
      <span className="mono" style={{ fontSize: 14, fontWeight: 600, color: 'var(--text)' }}>{price.price.toFixed(decimals)}</span>
      <span className="mono" style={{ fontSize: 10, color: price.change >= 0 ? 'var(--buy)' : 'var(--sell)', fontWeight: 500 }}>
        {price.change >= 0 ? '+' : ''}{price.change.toFixed(decimals)} ({price.change_pct >= 0 ? '+' : ''}{price.change_pct.toFixed(2)}%)
      </span>
    </div>
  );
}
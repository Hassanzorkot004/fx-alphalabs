import { useEffect, useRef, useState } from 'react';
import type { Price } from '../Types';
import { PAIR_DECIMALS } from '../config/constants';

interface TickerStripProps {
  prices: Record<string, Price>;
}

export default function TickerStrip({ prices }: TickerStripProps) {
  return (
    <div style={{
      background: 'var(--bg1)',
      borderBottom: '1px solid var(--border)',
      padding: '8px 20px',
      display: 'flex',
      gap: 32,
      overflowX: 'auto',
    }}>
      {Object.values(prices).map(price => (
        <TickerItem key={price.pair} price={price} />
      ))}
    </div>
  );
}

function TickerItem({ price }: { price: Price }) {
  const pair = price.pair.replace('=X', '');
  const decimals = PAIR_DECIMALS[pair] || 5;
  const prevPriceRef = useRef(price.price);
  const [flashClass, setFlashClass] = useState('');

  useEffect(() => {
    if (price.price !== prevPriceRef.current) {
      const direction = price.price > prevPriceRef.current ? 'green' : 'red';
      setFlashClass(`animate-flash-${direction}`);
      prevPriceRef.current = price.price;

      const timer = setTimeout(() => setFlashClass(''), 600);
      return () => clearTimeout(timer);
    }
  }, [price.price]);

  const changeColor = price.change >= 0 ? 'var(--green)' : 'var(--red)';

  return (
    <div 
      className={flashClass}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        padding: '4px 12px',
        borderRadius: 6,
        transition: 'background-color 0.6s ease',
      }}
    >
      <span className="mono" style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>
        {pair}
      </span>
      <span className="mono" style={{ fontSize: 15, fontWeight: 600, color: 'var(--text)' }}>
        {price.price.toFixed(decimals)}
      </span>
      <span className="mono" style={{ fontSize: 11, color: changeColor, fontWeight: 500 }}>
        {price.change >= 0 ? '+' : ''}{price.change.toFixed(decimals)}
      </span>
      <span className="mono" style={{ fontSize: 11, color: changeColor }}>
        ({price.change_pct >= 0 ? '+' : ''}{price.change_pct.toFixed(2)}%)
      </span>
    </div>
  );
}

import { useState } from 'react';
import { useTrading } from '../hooks/useTrading';
import { useSignals } from '../hooks/useSignals';
import type { VirtualTrade } from '../Types';

export default function TradesPage() {
  const {
    portfolio,
    openTrades,
    closedTrades,
    loading,
    error,
    closeTrade,
    refreshTrading,
  } = useTrading();

  const { prices, connected, lastUpdate } = useSignals();

  const [exitPrices, setExitPrices] = useState<Record<number, string>>({});
  const [pageMessage, setPageMessage] = useState<string | null>(null);
  const [pageMessageType, setPageMessageType] = useState<'success' | 'error'>('error');

  const unrealizedPnl = openTrades.reduce((sum, trade) => {
    const currentPrice = getCurrentPrice(trade.symbol, prices);
    if (!currentPrice) return sum;

    return sum + calculatePnl(trade, currentPrice);
  }, 0);

  const equity = (portfolio?.balance ?? 0) + unrealizedPnl;

  async function handleClose(trade: VirtualTrade) {
    const rawExitPrice = exitPrices[trade.id];

    if (!rawExitPrice) {
      setPageMessageType('error');
      setPageMessage('Enter an exit price first');
      return;
    }

    const exitPrice = Number(rawExitPrice);

    if (!Number.isFinite(exitPrice) || exitPrice <= 0) {
      setPageMessageType('error');
      setPageMessage('Invalid exit price');
      return;
    }

    if (!isReasonableFxExitPrice(trade.symbol, exitPrice)) {
      setPageMessageType('error');
      setPageMessage('Exit price looks unrealistic for this FX pair');
      return;
    }

    try {
      await closeTrade(trade.id, { exit_price: exitPrice });

      setExitPrices((prev) => {
        const next = { ...prev };
        delete next[trade.id];
        return next;
      });

      setPageMessageType('success');
      setPageMessage(`${trade.symbol} trade closed successfully`);

      setTimeout(() => setPageMessage(null), 2500);
    } catch (err) {
      console.error(err);
      setPageMessageType('error');
      setPageMessage('Failed to close trade');
    }
  }

  function closeAtLivePrice(trade: VirtualTrade) {
    const currentPrice = getCurrentPrice(trade.symbol, prices);

    if (!currentPrice) {
      setPageMessageType('error');
      setPageMessage('Live price unavailable for this pair');
      return;
    }

    setExitPrices((prev) => ({
      ...prev,
      [trade.id]: String(currentPrice),
    }));
  }

  return (
    <main style={{ padding: 20 }}>
      <header style={{ marginBottom: 20 }}>
        <h1 style={{ color: 'var(--amber)', margin: 0 }}>Paper Trading</h1>

        <p style={{ color: 'var(--text3)', marginTop: 6 }}>
          Live virtual portfolio, open trades, closed trades and unrealized PnL.
        </p>

        <div
          style={{
            marginTop: 8,
            fontSize: 12,
            color: connected ? 'var(--green)' : 'var(--red)',
          }}
        >
          {connected ? 'Live prices connected' : 'Live prices disconnected'}

          {lastUpdate && (
            <span style={{ color: 'var(--text3)', marginLeft: 8 }}>
              Updated {new Date(lastUpdate).toLocaleTimeString()}
            </span>
          )}
        </div>
      </header>

      {(error || pageMessage) && (
        <div
          style={{
            ...styles.messageBox,
            color:
              pageMessageType === 'success' && !error
                ? 'var(--green)'
                : 'var(--red)',
            background:
              pageMessageType === 'success' && !error
                ? 'rgba(0, 150, 100, 0.08)'
                : 'rgba(220, 38, 38, 0.08)',
            border:
              pageMessageType === 'success' && !error
                ? '1px solid rgba(0, 150, 100, 0.25)'
                : '1px solid rgba(220, 38, 38, 0.25)',
          }}
        >
          {error || pageMessage}
        </div>
      )}

      <section style={styles.grid}>
        <Card title="Balance">
          <BigValue value={portfolio ? `$${portfolio.balance.toFixed(2)}` : '—'} />
        </Card>

        <Card title="Unrealized PnL">
          <BigValue
            value={`$${unrealizedPnl.toFixed(2)}`}
            positive={unrealizedPnl >= 0}
          />
        </Card>

        <Card title="Equity">
          <BigValue
            value={portfolio ? `$${equity.toFixed(2)}` : '—'}
            positive={equity >= (portfolio?.initial_balance ?? 0)}
          />
        </Card>

        <Card title="Open Trades">
          <BigValue value={String(openTrades.length)} />
        </Card>
      </section>

      <div style={{ marginTop: 20, marginBottom: 20 }}>
        <button onClick={refreshTrading} style={styles.button}>
          {loading ? 'Loading...' : 'Refresh'}
        </button>
      </div>

      <section style={styles.panel}>
        <h2 style={styles.sectionTitle}>Open Trades</h2>

        {openTrades.length === 0 ? (
          <EmptyText text="No open trades yet." />
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={styles.table}>
              <thead>
                <tr>
                  <Th>Symbol</Th>
                  <Th>Side</Th>
                  <Th>Entry</Th>
                  <Th>Stop Loss</Th>
                  <Th>Take Profit</Th>
                  <Th>Current</Th>
                  <Th>Quantity</Th>
                  <Th>Unrealized PnL</Th>
                  <Th>Exit Price</Th>
                  <Th>Action</Th>
                </tr>
              </thead>

              <tbody>
                {openTrades.map((trade) => {
                  const currentPrice = getCurrentPrice(trade.symbol, prices);
                  const pnl = currentPrice ? calculatePnl(trade, currentPrice) : 0;

                  return (
                    <tr key={trade.id}>
                      <Td>{trade.symbol}</Td>

                      <Td>
                        <span
                          style={{
                            color: trade.side === 'BUY' ? 'var(--green)' : 'var(--red)',
                            fontWeight: 700,
                          }}
                        >
                          {trade.side}
                        </span>
                      </Td>

                      <Td>{formatPrice(trade.symbol, trade.entry_price)}</Td>

                      <Td>
                        {trade.stop_loss !== null && trade.stop_loss !== undefined
                          ? formatPrice(trade.symbol, trade.stop_loss)
                          : '—'}
                      </Td>

                      <Td>
                        {trade.take_profit !== null && trade.take_profit !== undefined
                          ? formatPrice(trade.symbol, trade.take_profit)
                          : '—'}
                      </Td>

                      <Td>{currentPrice ? formatPrice(trade.symbol, currentPrice) : '—'}</Td>
                      <Td>{trade.quantity}</Td>

                      <Td>
                        <span
                          style={{
                            color: pnl >= 0 ? 'var(--green)' : 'var(--red)',
                            fontWeight: 700,
                          }}
                        >
                          ${pnl.toFixed(2)}
                        </span>
                      </Td>

                      <Td>
                        <div style={{ display: 'flex', gap: 8 }}>
                          <input
                            value={exitPrices[trade.id] ?? ''}
                            onChange={(e) => {
                              setPageMessage(null);
                              setExitPrices((prev) => ({
                                ...prev,
                                [trade.id]: e.target.value,
                              }));
                            }}
                            placeholder={getExitPlaceholder(trade.symbol)}
                            style={styles.input}
                          />

                          <button
                            onClick={() => closeAtLivePrice(trade)}
                            style={styles.secondaryButton}
                          >
                            Live
                          </button>
                        </div>
                      </Td>

                      <Td>
                        <button
                          onClick={() => handleClose(trade)}
                          style={styles.closeButton}
                        >
                          Close
                        </button>
                      </Td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section style={styles.panel}>
        <h2 style={styles.sectionTitle}>Closed Trades</h2>

        {closedTrades.length === 0 ? (
          <EmptyText text="No closed trades yet." />
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={styles.table}>
              <thead>
                <tr>
                  <Th>Symbol</Th>
                  <Th>Side</Th>
                  <Th>Entry</Th>
                  <Th>Stop Loss</Th>
                  <Th>Take Profit</Th>
                  <Th>Exit</Th>
                  <Th>Quantity</Th>
                  <Th>PnL</Th>
                  <Th>Closed</Th>
                </tr>
              </thead>

              <tbody>
                {closedTrades.map((trade) => (
                  <tr key={trade.id}>
                    <Td>{trade.symbol}</Td>
                    <Td>{trade.side}</Td>
                    <Td>{formatPrice(trade.symbol, trade.entry_price)}</Td>

                    <Td>
                      {trade.stop_loss !== null && trade.stop_loss !== undefined
                        ? formatPrice(trade.symbol, trade.stop_loss)
                        : '—'}
                    </Td>

                    <Td>
                      {trade.take_profit !== null && trade.take_profit !== undefined
                        ? formatPrice(trade.symbol, trade.take_profit)
                        : '—'}
                    </Td>

                    <Td>
                      {trade.exit_price !== null && trade.exit_price !== undefined
                        ? formatPrice(trade.symbol, trade.exit_price)
                        : '—'}
                    </Td>

                    <Td>{trade.quantity}</Td>

                    <Td>
                      <span
                        style={{
                          color: trade.pnl >= 0 ? 'var(--green)' : 'var(--red)',
                          fontWeight: 700,
                        }}
                      >
                        ${trade.pnl.toFixed(2)}
                      </span>
                    </Td>

                    <Td>{trade.closed_at ? formatDate(trade.closed_at) : '—'}</Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}

function getCurrentPrice(
  symbol: string,
  prices: Record<string, { price: number }>
) {
  return prices[`${symbol}=X`]?.price ?? prices[symbol]?.price ?? null;
}

function calculatePnl(trade: VirtualTrade, currentPrice: number) {
  if (trade.side === 'BUY') {
    return (currentPrice - trade.entry_price) * trade.quantity;
  }

  return (trade.entry_price - currentPrice) * trade.quantity;
}

function isReasonableFxExitPrice(symbol: string, price: number) {
  if (symbol === 'USDJPY') return price >= 50 && price <= 250;

  return price >= 0.5 && price <= 2.5;
}

function getExitPlaceholder(symbol: string) {
  return symbol === 'USDJPY' ? 'ex: 157.200' : 'ex: 1.0875';
}

function formatPrice(symbol: string, price: number) {
  const decimals = symbol === 'USDJPY' ? 3 : 5;

  return price.toFixed(decimals);
}

function formatDate(value: string) {
  return new Date(value).toLocaleString();
}

function Card({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div style={styles.card}>
      <div style={styles.cardTitle}>{title}</div>
      {children}
    </div>
  );
}

function BigValue({
  value,
  positive,
}: {
  value: string;
  positive?: boolean;
}) {
  return (
    <div
      style={{
        fontSize: 24,
        fontWeight: 800,
        color:
          positive === undefined
            ? 'var(--text)'
            : positive
              ? 'var(--green)'
              : 'var(--red)',
      }}
    >
      {value}
    </div>
  );
}

function Th({ children }: { children: React.ReactNode }) {
  return <th style={styles.th}>{children}</th>;
}

function Td({ children }: { children: React.ReactNode }) {
  return <td style={styles.td}>{children}</td>;
}

function EmptyText({ text }: { text: string }) {
  return <p style={{ color: 'var(--text3)', margin: 0 }}>{text}</p>;
}

const styles: Record<string, React.CSSProperties> = {
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, minmax(160px, 1fr))',
    gap: 14,
  },
  card: {
    background: 'var(--bg1)',
    border: '1px solid var(--border)',
    borderRadius: 8,
    padding: 16,
  },
  cardTitle: {
    color: 'var(--text3)',
    fontSize: 12,
    textTransform: 'uppercase',
    letterSpacing: 1,
    marginBottom: 8,
  },
  panel: {
    background: 'var(--bg1)',
    border: '1px solid var(--border)',
    borderRadius: 8,
    padding: 16,
    marginTop: 20,
  },
  sectionTitle: {
    color: 'var(--amber)',
    fontSize: 16,
    marginTop: 0,
    marginBottom: 14,
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: 13,
  },
  th: {
    textAlign: 'left',
    color: 'var(--text3)',
    borderBottom: '1px solid var(--border)',
    padding: '10px 8px',
    fontWeight: 700,
    whiteSpace: 'nowrap',
  },
  td: {
    color: 'var(--text)',
    borderBottom: '1px solid var(--border)',
    padding: '10px 8px',
    whiteSpace: 'nowrap',
  },
  input: {
    background: 'var(--bg)',
    border: '1px solid var(--border)',
    color: 'var(--text)',
    padding: '7px 8px',
    borderRadius: 6,
    width: 120,
  },
  button: {
    background: 'var(--amber)',
    color: '#fff',
    border: 'none',
    borderRadius: 6,
    padding: '9px 14px',
    fontWeight: 700,
    cursor: 'pointer',
  },
  secondaryButton: {
    background: 'transparent',
    color: 'var(--amber)',
    border: '1px solid var(--amber)',
    borderRadius: 6,
    padding: '7px 10px',
    fontWeight: 700,
    cursor: 'pointer',
  },
  closeButton: {
    background: 'var(--red)',
    color: '#fff',
    border: 'none',
    borderRadius: 6,
    padding: '7px 12px',
    fontWeight: 700,
    cursor: 'pointer',
  },
  messageBox: {
    padding: '10px 12px',
    borderRadius: 6,
    fontSize: 12,
    fontWeight: 600,
    marginBottom: 16,
  },
};
import { useSignals } from '../hooks/useSignals';
import type { Signal } from '../Types';

export default function HistoryPage() {
  const { history, signals, connected, lastUpdate } = useSignals();

  const allRows = [...signals, ...history];

  function exportCsv() {
    if (allRows.length === 0) return;

    const headers = [
      'pair',
      'direction',
      'confidence',
      'agent_agreement',
      'macro_regime',
      'tech_signal',
      'sent_signal',
      'timestamp',
    ];

    const rows = allRows.map((signal) => [
      signal.pair.replace('=X', ''),
      signal.direction,
      Math.round(signal.confidence * 100) + '%',
      signal.agent_agreement,
      signal.macro_regime,
      signal.tech_signal,
      signal.sent_signal,
      signal.timestamp,
    ]);

    const csvContent = [
      headers.join(','),
      ...rows.map((row) =>
        row
          .map((cell) => `"${String(cell ?? '').replace(/"/g, '""')}"`)
          .join(',')
      ),
    ].join('\n');

    const blob = new Blob([csvContent], {
      type: 'text/csv;charset=utf-8;',
    });

    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');

    link.href = url;
    link.download = `fx-alphalab-history-${new Date()
      .toISOString()
      .slice(0, 10)}.csv`;

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    URL.revokeObjectURL(url);
  }

  return (
    <main style={{ padding: 24 }}>
      <header
        style={{
          marginBottom: 24,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          gap: 20,
        }}
      >
        <div>
          <h1
            className="mono"
            style={{
              color: 'var(--amber)',
              fontSize: 22,
              marginBottom: 6,
            }}
          >
            Signal History
          </h1>

          <p style={{ color: 'var(--text3)', fontSize: 13 }}>
            Historical FX AlphaLab signals loaded from the live WebSocket stream.
          </p>

          <div
            style={{
              marginTop: 8,
              fontSize: 12,
              color: connected ? 'var(--green)' : 'var(--red)',
            }}
          >
            {connected ? 'Live data connected' : 'Live data disconnected'}

            {lastUpdate && (
              <span style={{ color: 'var(--text3)', marginLeft: 8 }}>
                Updated {new Date(lastUpdate).toLocaleTimeString()}
              </span>
            )}
          </div>
        </div>

        <button
          onClick={exportCsv}
          disabled={allRows.length === 0}
          style={{
            background: allRows.length === 0 ? 'var(--bg3)' : 'var(--amber)',
            color: allRows.length === 0 ? 'var(--text3)' : '#000',
            border: 'none',
            borderRadius: 8,
            padding: '10px 14px',
            fontSize: 13,
            fontWeight: 700,
            cursor: allRows.length === 0 ? 'not-allowed' : 'pointer',
          }}
        >
          Export CSV
        </button>
      </header>

      {allRows.length === 0 ? (
        <div
          style={{
            background: 'var(--bg1)',
            border: '1px solid var(--border)',
            borderRadius: 10,
            padding: 20,
            color: 'var(--text3)',
          }}
        >
          Waiting for history data...
        </div>
      ) : (
        <section
          style={{
            background: 'var(--bg1)',
            border: '1px solid var(--border)',
            borderRadius: 10,
            overflow: 'hidden',
          }}
        >
          <table
            style={{
              width: '100%',
              borderCollapse: 'collapse',
              fontSize: 13,
            }}
          >
            <thead>
              <tr style={{ background: 'var(--bg2)' }}>
                <Th>Pair</Th>
                <Th>Direction</Th>
                <Th>Confidence</Th>
                <Th>Agreement</Th>
                <Th>Macro</Th>
                <Th>Tech</Th>
                <Th>Sentiment</Th>
                <Th>Timestamp</Th>
              </tr>
            </thead>

            <tbody>
              {allRows.map((signal: Signal, index: number) => (
                <tr key={`${signal.pair}-${signal.timestamp}-${index}`}>
                  <Td>{signal.pair.replace('=X', '')}</Td>

                  <Td>
                    <span
                      style={{
                        color:
                          signal.direction === 'BUY'
                            ? 'var(--green)'
                            : signal.direction === 'SELL'
                              ? 'var(--red)'
                              : 'var(--amber)',
                        fontWeight: 700,
                      }}
                    >
                      {signal.direction}
                    </span>
                  </Td>

                  <Td>{Math.round(signal.confidence * 100)}%</Td>
                  <Td>{signal.agent_agreement}</Td>
                  <Td>{signal.macro_regime}</Td>
                  <Td>{signal.tech_signal}</Td>
                  <Td>{signal.sent_signal}</Td>
                  <Td>{formatDate(signal.timestamp)}</Td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </main>
  );
}

function Th({ children }: { children: React.ReactNode }) {
  return (
    <th
      style={{
        textAlign: 'left',
        padding: '12px 14px',
        color: 'var(--text3)',
        borderBottom: '1px solid var(--border)',
        fontSize: 11,
        textTransform: 'uppercase',
        letterSpacing: '0.6px',
      }}
    >
      {children}
    </th>
  );
}

function Td({ children }: { children: React.ReactNode }) {
  return (
    <td
      style={{
        padding: '12px 14px',
        color: 'var(--text)',
        borderBottom: '1px solid var(--border)',
        whiteSpace: 'nowrap',
      }}
    >
      {children}
    </td>
  );
}

function formatDate(value: string) {
  if (!value) return '—';

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString();
}
import { useState, useEffect } from 'react';
import { ErrorBoundary } from './components/ErrorBoundary';
import App from './App';
import HistoryPage from './pages/HistoryPage';
import PerformancePage from './pages/PerformancePage';
import SettingsPage from './pages/SettingsPage';

type Page = 'dashboard' | 'history' | 'performance' | 'settings';

export default function AppWithRouter() {
  const [currentPage, setCurrentPage] = useState<Page>('dashboard');

  // Apply saved theme on boot
  useEffect(() => {
    try {
      const stored = localStorage.getItem('fx-alphalab-settings');
      if (stored) {
        const parsed = JSON.parse(stored);
        if (parsed.theme) {
          document.documentElement.setAttribute('data-theme', parsed.theme);
        }
      }
    } catch { /* ignore */ }
  }, []);

  return (
    <ErrorBoundary>
      <div style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)' }}>
        {/* Navigation Bar */}
        <nav style={{
          background: 'var(--bg1)',
          borderBottom: '1px solid var(--border)',
          padding: '0 20px',
          display: 'flex',
          alignItems: 'center',
          gap: 0,
        }}>
          {/* Logo */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginRight: 24 }}>
            <div style={{
              width: 32,
              height: 32,
              background: 'var(--cyan)',
              borderRadius: 6,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}>
              <span className="mono" style={{ fontSize: 11, fontWeight: 700, color: '#0d1117' }}>FX</span>
            </div>
            <div>
              <div className="mono" style={{ fontSize: 13, fontWeight: 700, color: 'var(--text)', lineHeight: 1.2 }}>
                AlphaLab
              </div>
              <div className="mono" style={{ fontSize: 9, color: 'var(--text3)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
                Signal Engine
              </div>
            </div>
          </div>

          <NavButton label="Dashboard"   isActive={currentPage === 'dashboard'}   onClick={() => setCurrentPage('dashboard')} />
          <NavButton label="History"     isActive={currentPage === 'history'}     onClick={() => setCurrentPage('history')} />
          <NavButton label="Performance" isActive={currentPage === 'performance'} onClick={() => setCurrentPage('performance')} />
          <NavButton label="Settings"    isActive={currentPage === 'settings'}    onClick={() => setCurrentPage('settings')} />
        </nav>

        {/* Page Content */}
        {currentPage === 'dashboard'   && <App />}
        {currentPage === 'history'     && <HistoryPage />}
        {currentPage === 'performance' && <PerformancePage />}
        {currentPage === 'settings'    && <SettingsPage />}
      </div>
    </ErrorBoundary>
  );
}

function NavButton({ label, isActive, onClick }: {
  label: string;
  isActive: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      style={{
        background: 'transparent',
        border: 'none',
        borderBottom: `2px solid ${isActive ? 'var(--cyan)' : 'transparent'}`,
        color: isActive ? 'var(--cyan)' : 'var(--text3)',
        padding: '14px 18px',
        fontSize: 13,
        fontWeight: 500,
        cursor: 'pointer',
        transition: 'color 0.15s ease, border-color 0.15s ease',
        letterSpacing: '0.01em',
      }}
      onMouseEnter={e => { if (!isActive) (e.target as HTMLElement).style.color = 'var(--text2)'; }}
      onMouseLeave={e => { if (!isActive) (e.target as HTMLElement).style.color = 'var(--text3)'; }}
    >
      {label}
    </button>
  );
}

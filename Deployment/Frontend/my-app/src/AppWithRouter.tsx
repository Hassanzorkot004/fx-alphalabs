import { useState } from 'react';
import { ErrorBoundary } from './components/ErrorBoundary';
import App from './App';
import HistoryPage from './pages/HistoryPage';
import SettingsPage from './pages/SettingsPage';

type Page = 'dashboard' | 'history' | 'settings';

export default function AppWithRouter() {
  const [currentPage, setCurrentPage] = useState<Page>('dashboard');

  return (
    <ErrorBoundary>
      <div style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)' }}>
        {/* Navigation Bar */}
        <nav style={{
          background: 'var(--bg1)',
          borderBottom: '1px solid var(--border)',
          padding: '0 20px',
          display: 'flex',
          gap: 4,
        }}>
          <NavButton
            label="Dashboard"
            isActive={currentPage === 'dashboard'}
            onClick={() => setCurrentPage('dashboard')}
          />
          <NavButton
            label="History"
            isActive={currentPage === 'history'}
            onClick={() => setCurrentPage('history')}
          />
          <NavButton
            label="Settings"
            isActive={currentPage === 'settings'}
            onClick={() => setCurrentPage('settings')}
          />
        </nav>

        {/* Page Content */}
        {currentPage === 'dashboard' && <App />}
        {currentPage === 'history' && <HistoryPage />}
        {currentPage === 'settings' && <SettingsPage />}
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
        borderBottom: `2px solid ${isActive ? 'var(--amber)' : 'transparent'}`,
        color: isActive ? 'var(--amber)' : 'var(--text3)',
        padding: '12px 20px',
        fontSize: 13,
        fontWeight: 600,
        cursor: 'pointer',
        transition: 'all 0.2s ease',
      }}
      className={!isActive ? 'hover:color-text2' : ''}
    >
      {label}
    </button>
  );
}

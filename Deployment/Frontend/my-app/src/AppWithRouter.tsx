import { useState } from 'react';
import { ErrorBoundary } from './components/ErrorBoundary';
import App from './App';
import HistoryPage from './pages/HistoryPage';
import SettingsPage from './pages/SettingsPage';
import AuthPage from './pages/AuthPage';

type Page = 'dashboard' | 'history' | 'settings';

type User = {
  email: string;
  username: string;
};

export default function AppWithRouter() {
  const savedUser = localStorage.getItem('fx_user');

  const [currentPage, setCurrentPage] = useState<Page>('dashboard');
  const [user, setUser] = useState<User | null>(
    savedUser ? JSON.parse(savedUser) : null
  );

  const isAuthenticated = !!localStorage.getItem('fx_token') && !!user;

  if (!isAuthenticated) {
    return (
      <ErrorBoundary>
        <AuthPage onLogin={(loggedUser) => setUser(loggedUser)} />
      </ErrorBoundary>
    );
  }

  return (
    <ErrorBoundary>
      <div style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)' }}>
        <nav style={{
          background: 'var(--bg1)',
          borderBottom: '1px solid var(--border)',
          padding: '0 20px',
          display: 'flex',
          gap: 4,
          alignItems: 'center',
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

          <div
            style={{
              marginLeft: 'auto',
              color: 'var(--text3)',
              fontSize: 13,
              padding: '12px 20px',
            }}
          >
            Logged in as <span style={{ color: 'var(--amber)' }}>{user.username}</span>
          </div>

          <button
            onClick={() => {
              localStorage.removeItem('fx_token');
              localStorage.removeItem('fx_user');
              setUser(null);
              setCurrentPage('dashboard');
            }}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--red)',
              padding: '12px 20px',
              fontSize: 13,
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            Logout
          </button>
        </nav>

        {currentPage === 'dashboard' && <App />}
        {currentPage === 'history' && <HistoryPage />}
        {currentPage === 'settings' && <SettingsPage />}
      </div>
    </ErrorBoundary>
  );
}

function NavButton({
  label,
  isActive,
  onClick,
}: {
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
    >
      {label}
    </button>
  );
}
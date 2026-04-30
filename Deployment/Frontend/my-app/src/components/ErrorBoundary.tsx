import { Component, ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };
  
  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }
  
  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('ErrorBoundary caught:', error, errorInfo);
  }
  
  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'var(--bg)',
          color: 'var(--text-primary)',
          padding: 40,
          textAlign: 'center',
          flexDirection: 'column'
        }}>
          <div>
            <h2 style={{ fontSize: 24, marginBottom: 16, color: 'var(--sell)' }}>
              Something went wrong
            </h2>
            <p style={{ 
              color: 'var(--text-muted)', 
              marginBottom: 24, 
              fontFamily: 'var(--font-mono)', 
              fontSize: 12,
              maxWidth: 600
            }}>
              {this.state.error?.message || 'Unknown error'}
            </p>
            <button
              onClick={() => window.location.reload()}
              style={{
                background: 'var(--info)',
                color: '#fff',
                border: 'none',
                padding: '10px 20px',
                borderRadius: 8,
                cursor: 'pointer',
                fontFamily: 'var(--font-mono)',
                fontSize: 13,
                fontWeight: 500
              }}
            >
              Reload Application
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

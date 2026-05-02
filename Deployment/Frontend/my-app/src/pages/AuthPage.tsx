import { useState } from 'react';

const API_BASE = 'http://127.0.0.1:8001';

type AuthPageProps = {
  onLogin: (user: { email: string; username: string }) => void;
};

type AuthStep = 'login' | 'register' | 'verify';

export default function AuthPage({ onLogin }: AuthPageProps) {
  const [step, setStep] = useState<AuthStep>('login');

  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const [otpCode, setOtpCode] = useState('');

  const [message, setMessage] = useState<string | null>(null);
  const [messageType, setMessageType] = useState<'success' | 'error'>('success');
  const [loading, setLoading] = useState(false);

  async function register() {
    try {
      setLoading(true);
      setMessage(null);

      const res = await fetch(`${API_BASE}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, email, password }),
      });

      const data = await res.json().catch(() => null);

      if (!res.ok) {
        throw new Error(data?.detail || 'Registration failed');
      }

      setMessageType('success');
      setMessage('Account created. Please enter the verification code sent by email.');
      setStep('verify');
    } catch (err) {
      setMessageType('error');
      setMessage(err instanceof Error ? err.message : 'Registration failed');
    } finally {
      setLoading(false);
    }
  }

  async function verifyEmail() {
    try {
      setLoading(true);
      setMessage(null);

      const res = await fetch(`${API_BASE}/auth/verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, code: otpCode }),
      });

      const data = await res.json().catch(() => null);

      if (!res.ok) {
        throw new Error(data?.detail || 'Invalid verification code');
      }

      setMessageType('success');
      setMessage('Email verified successfully. You can now log in.');
      setStep('login');
      setOtpCode('');
      setPassword('');
    } catch (err) {
      setMessageType('error');
      setMessage(err instanceof Error ? err.message : 'Verification failed');
    } finally {
      setLoading(false);
    }
  }

  async function login() {
    try {
      setLoading(true);
      setMessage(null);

      const res = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      const data = await res.json().catch(() => null);

      if (!res.ok) {
        throw new Error(data?.detail || 'Login failed');
      }

      localStorage.setItem('fx_token', data.access_token);

      const meRes = await fetch(`${API_BASE}/auth/me`, {
        headers: {
          Authorization: `Bearer ${data.access_token}`,
        },
      });

      const user = await meRes.json().catch(() => null);

      if (!meRes.ok) {
        throw new Error(user?.detail || 'Unable to load profile');
      }

      localStorage.setItem('fx_user', JSON.stringify(user));
      onLogin(user);
    } catch (err) {
      setMessageType('error');
      setMessage(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setLoading(false);
    }
  }

  function submit() {
    if (step === 'register') return register();
    if (step === 'verify') return verifyEmail();
    return login();
  }

  return (
    <div style={pageStyle}>
      <div style={cardStyle}>
        <h1 style={{ color: 'var(--amber)', marginBottom: 8 }}>FX AlphaLab</h1>

        <p style={{ color: 'var(--text3)', marginBottom: 24 }}>
          {step === 'login' && 'Trader login'}
          {step === 'register' && 'Create your trader account'}
          {step === 'verify' && 'Verify your email address'}
        </p>

        {message && (
          <div
            style={{
              ...messageStyle,
              color: messageType === 'success' ? 'var(--green)' : 'var(--red)',
              border:
                messageType === 'success'
                  ? '1px solid rgba(0, 180, 120, 0.3)'
                  : '1px solid rgba(220, 80, 80, 0.3)',
              background:
                messageType === 'success'
                  ? 'rgba(0, 180, 120, 0.08)'
                  : 'rgba(220, 80, 80, 0.08)',
            }}
          >
            {message}
          </div>
        )}

        {step === 'register' && (
          <input
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            style={inputStyle}
          />
        )}

        {(step === 'login' || step === 'register' || step === 'verify') && (
          <input
            placeholder="Email"
            value={email}
            disabled={step === 'verify'}
            onChange={(e) => setEmail(e.target.value)}
            style={inputStyle}
          />
        )}

        {(step === 'login' || step === 'register') && (
          <input
            placeholder="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            style={inputStyle}
          />
        )}

        {step === 'verify' && (
          <input
            placeholder="Verification code"
            value={otpCode}
            onChange={(e) => setOtpCode(e.target.value)}
            style={inputStyle}
          />
        )}

        <button onClick={submit} disabled={loading} style={buttonStyle}>
          {loading
            ? 'Please wait...'
            : step === 'login'
              ? 'Login'
              : step === 'register'
                ? 'Register'
                : 'Verify Email'}
        </button>

        {step !== 'verify' && (
          <button
            onClick={() => {
              setMessage(null);
              setStep(step === 'login' ? 'register' : 'login');
            }}
            style={linkButtonStyle}
          >
            {step === 'login' ? 'Create an account' : 'I already have an account'}
          </button>
        )}

        {step === 'verify' && (
          <button
            onClick={() => {
              setMessage(null);
              setStep('login');
            }}
            style={linkButtonStyle}
          >
            Back to login
          </button>
        )}
      </div>
    </div>
  );
}

const pageStyle: React.CSSProperties = {
  minHeight: '100vh',
  background: 'var(--bg)',
  color: 'var(--text)',
  display: 'flex',
  justifyContent: 'center',
  alignItems: 'center',
};

const cardStyle: React.CSSProperties = {
  width: 420,
  background: 'var(--bg2)',
  border: '1px solid var(--border)',
  borderRadius: 12,
  padding: 28,
};

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '12px',
  marginBottom: 12,
  background: 'var(--bg3)',
  border: '1px solid var(--border)',
  borderRadius: 8,
  color: 'var(--text)',
};

const buttonStyle: React.CSSProperties = {
  width: '100%',
  padding: '12px',
  background: 'var(--amber)',
  color: '#000',
  border: 'none',
  borderRadius: 8,
  fontWeight: 700,
  cursor: 'pointer',
};

const linkButtonStyle: React.CSSProperties = {
  marginTop: 14,
  background: 'transparent',
  border: 'none',
  color: 'var(--amber)',
  cursor: 'pointer',
};

const messageStyle: React.CSSProperties = {
  padding: '10px 12px',
  borderRadius: 8,
  fontSize: 13,
  fontWeight: 600,
  marginBottom: 16,
};
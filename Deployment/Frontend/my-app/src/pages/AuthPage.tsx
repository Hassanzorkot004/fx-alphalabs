import { useState } from 'react';

const API_BASE = 'http://127.0.0.1:8001';

type AuthPageProps = {
  onLogin: (user: { email: string; username: string }) => void;
};

export default function AuthPage({ onLogin }: AuthPageProps) {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const submit = async () => {
    const endpoint = mode === 'login' ? '/auth/login' : '/auth/register';

    const body =
      mode === 'login'
        ? { email, password }
        : { username, email, password };

    const res = await fetch(`${API_BASE}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    if (!res.ok) {
      const error = await res.json().catch(() => null);
      alert(error?.detail || 'Erreur : vérifie tes informations');
      return;
    }

    if (mode === 'register') {
      alert('Compte créé. Connecte-toi maintenant.');
      setMode('login');
      return;
    }

    const data = await res.json();
    localStorage.setItem('fx_token', data.access_token);

    const meRes = await fetch(`${API_BASE}/auth/me`, {
      headers: {
        Authorization: `Bearer ${data.access_token}`,
      },
    });

    if (!meRes.ok) {
      alert('Connexion réussie, mais impossible de charger le profil.');
      return;
    }

    const user = await meRes.json();
    localStorage.setItem('fx_user', JSON.stringify(user));

    onLogin(user);
  };

  return (
    <div style={{
      minHeight: '100vh',
      background: 'var(--bg)',
      color: 'var(--text)',
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center'
    }}>
      <div style={{
        width: 420,
        background: 'var(--bg2)',
        border: '1px solid var(--border)',
        borderRadius: 12,
        padding: 28
      }}>
        <h1 style={{ color: 'var(--amber)', marginBottom: 8 }}>
          FX AlphaLab
        </h1>

        <p style={{ color: 'var(--text3)', marginBottom: 24 }}>
          {mode === 'login' ? 'Connexion trader' : 'Créer un compte trader'}
        </p>

        {mode === 'register' && (
          <input
            placeholder="Username"
            value={username}
            onChange={e => setUsername(e.target.value)}
            style={inputStyle}
          />
        )}

        <input
          placeholder="Email"
          value={email}
          onChange={e => setEmail(e.target.value)}
          style={inputStyle}
        />

        <input
          placeholder="Password"
          type="password"
          value={password}
          onChange={e => setPassword(e.target.value)}
          style={inputStyle}
        />

        <button onClick={submit} style={buttonStyle}>
          {mode === 'login' ? 'Login' : 'Register'}
        </button>

        <button
          onClick={() => setMode(mode === 'login' ? 'register' : 'login')}
          style={{
            marginTop: 14,
            background: 'transparent',
            border: 'none',
            color: 'var(--amber)',
            cursor: 'pointer'
          }}
        >
          {mode === 'login'
            ? 'Créer un compte'
            : 'J’ai déjà un compte'}
        </button>
      </div>
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '12px',
  marginBottom: 12,
  background: 'var(--bg3)',
  border: '1px solid var(--border)',
  borderRadius: 8,
  color: 'var(--text)'
};

const buttonStyle: React.CSSProperties = {
  width: '100%',
  padding: '12px',
  background: 'var(--amber)',
  color: '#000',
  border: 'none',
  borderRadius: 8,
  fontWeight: 700,
  cursor: 'pointer'
};
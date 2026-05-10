import { useState, useEffect } from 'react';

export default function SettingsPage() {
  const [defaultMode, setDefaultMode] = useState<'simple' | 'pro'>('simple');
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    try {
      const stored = localStorage.getItem('fx-alphalab-settings');
      if (stored) {
        const settings = JSON.parse(stored);
        setDefaultMode(settings.defaultMode || 'simple');
      }
    } catch {}
  }, []);

  const handleSave = () => {
    try {
      localStorage.setItem('fx-alphalab-settings', JSON.stringify({ defaultMode }));
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {}
  };

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)' }}>
      {/* Header */}
      <div style={{ background: 'var(--bg1)', borderBottom: '1px solid var(--border)', padding: '12px 24px', display: 'flex', alignItems: 'center', gap: 16, backdropFilter: 'blur(12px)', position: 'sticky', top: 0, zIndex: 50 }}>
        <div style={{ width: 28, height: 28, borderRadius: 8, background: 'linear-gradient(135deg, var(--cyan), var(--violet))', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 13, fontWeight: 800, color: '#000', boxShadow: '0 0 12px rgba(0,229,255,0.15)' }}>FX</div>
        <span className="mono" style={{ fontSize: 14, fontWeight: 700, color: 'var(--text)', letterSpacing: '-0.2px' }}>AlphaLab</span>
        <span style={{ color: 'var(--text3)', fontSize: 11, marginLeft: 'auto' }}>Settings</span>
      </div>

      <div style={{ maxWidth: 700, margin: '0 auto', padding: '32px 20px' }}>
        <div className="glass" style={{ padding: 24 }}>
          <h2 className="mono" style={{ fontSize: 16, fontWeight: 700, color: 'var(--cyan)', marginBottom: 8, letterSpacing: '-0.2px' }}>AlphaBot Preferences</h2>
          <p style={{ fontSize: 12, color: 'var(--text2)', marginBottom: 24, lineHeight: 1.6 }}>
            Choose how AlphaBot explains trading signals. Simple mode uses plain English with analogies. Pro mode uses proper terminology with exact values.
          </p>

          <div style={{ display: 'flex', gap: 12, marginBottom: 24 }}>
            {(['simple', 'pro'] as const).map(mode => (
              <button key={mode} onClick={() => setDefaultMode(mode)} style={{
                flex: 1, padding: '16px 20px', borderRadius: 10, cursor: 'pointer', textAlign: 'left', transition: 'all 0.2s ease',
                background: defaultMode === mode ? 'var(--cyan)10' : 'var(--bg2)',
                border: defaultMode === mode ? '1px solid var(--cyan)' : '1px solid var(--border)',
              }}>
                <div style={{ fontSize: 14, fontWeight: 700, color: defaultMode === mode ? 'var(--cyan)' : 'var(--text)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 4 }}>{mode}</div>
                <div style={{ fontSize: 11, color: 'var(--text3)', lineHeight: 1.5 }}>
                  {mode === 'simple' ? 'Plain English, analogies, no jargon. Best for new traders.' : 'Exact values, proper terminology, detailed reasoning chain.'}
                </div>
              </button>
            ))}
          </div>

          <button onClick={handleSave} style={{
            width: '100%', padding: '12px', borderRadius: 8, border: 'none', cursor: 'pointer', fontSize: 13, fontWeight: 600,
            background: saved ? 'var(--emerald)' : 'var(--cyan)', color: '#000', transition: 'all 0.2s ease',
          }}>
            {saved ? '✓ Saved' : 'Save Settings'}
          </button>
        </div>

        <div className="glass" style={{ padding: 24, marginTop: 20 }}>
          <h2 className="mono" style={{ fontSize: 16, fontWeight: 700, color: 'var(--cyan)', marginBottom: 8, letterSpacing: '-0.2px' }}>About</h2>
          <div style={{ fontSize: 11, color: 'var(--text3)', lineHeight: 1.8 }}>
            <div>FX AlphaLab v2.0</div>
            <div>5-Stage Hybrid Pipeline</div>
            <div>Llama 3.1 70B · Hosted Ollama</div>
            <div style={{ marginTop: 8, color: 'var(--text2)' }}>Macro (KMeans) · Technical (TCN+LSTM) · Sentiment (XGBoost) · Conviction Gate · LLM Analysts · Orchestrator</div>
          </div>
        </div>
      </div>
    </div>
  );
}
import { useState, useEffect } from 'react';

interface Settings {
  watchlist: string[];
  defaultMode: 'simple' | 'pro';
  theme: 'dark';
}

const DEFAULT_SETTINGS: Settings = {
  watchlist: ['EURUSD', 'GBPUSD', 'USDJPY'],
  defaultMode: 'simple',
  theme: 'dark',
};

const AVAILABLE_PAIRS = ['EURUSD', 'GBPUSD', 'USDJPY'];

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings>(DEFAULT_SETTINGS);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    // Load settings from localStorage
    const stored = localStorage.getItem('fx-alphalab-settings');
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        setSettings({ ...DEFAULT_SETTINGS, ...parsed });
      } catch (err) {
        console.error('Failed to parse settings:', err);
      }
    }
  }, []);

  const saveSettings = () => {
    localStorage.setItem('fx-alphalab-settings', JSON.stringify(settings));
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const togglePair = (pair: string) => {
    setSettings(prev => ({
      ...prev,
      watchlist: prev.watchlist.includes(pair)
        ? prev.watchlist.filter(p => p !== pair)
        : [...prev.watchlist, pair],
    }));
  };

  const resetToDefaults = () => {
    setSettings(DEFAULT_SETTINGS);
    localStorage.removeItem('fx-alphalab-settings');
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)' }}>
      {/* Header */}
      <div style={{
        background: 'var(--bg1)',
        borderBottom: '1px solid var(--border)',
        padding: '16px 24px',
      }}>
        <h1 className="mono" style={{ fontSize: 20, fontWeight: 600, color: 'var(--amber)', marginBottom: 4 }}>
          Settings
        </h1>
        <div style={{ fontSize: 13, color: 'var(--text3)' }}>
          Configure your FX AlphaLab preferences
        </div>
      </div>

      {/* Content */}
      <div style={{ padding: 24, maxWidth: 800 }}>
        {/* Watchlist Section */}
        <Section title="Pair Watchlist" description="Select which currency pairs to display">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {AVAILABLE_PAIRS.map(pair => (
              <label
                key={pair}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 12,
                  padding: 12,
                  background: 'var(--bg3)',
                  border: '1px solid var(--border)',
                  borderRadius: 6,
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                }}
                className="hover:border-border2"
              >
                <input
                  type="checkbox"
                  checked={settings.watchlist.includes(pair)}
                  onChange={() => togglePair(pair)}
                  style={{
                    width: 18,
                    height: 18,
                    cursor: 'pointer',
                    accentColor: 'var(--amber)',
                  }}
                />
                <span className="mono" style={{ fontSize: 14, fontWeight: 600 }}>
                  {pair}
                </span>
              </label>
            ))}
          </div>
        </Section>

        {/* Default Mode Section */}
        <Section 
          title="Default AlphaBot Mode" 
          description="Choose your preferred explanation style. You can quickly toggle this in the chat header."
        >
          <div style={{ display: 'flex', gap: 12 }}>
            <ModeButton
              label="Simple"
              description="Plain language, beginner-friendly"
              isSelected={settings.defaultMode === 'simple'}
              onClick={() => setSettings(prev => ({ ...prev, defaultMode: 'simple' }))}
            />
            <ModeButton
              label="Pro"
              description="Technical terminology, detailed metrics"
              isSelected={settings.defaultMode === 'pro'}
              onClick={() => setSettings(prev => ({ ...prev, defaultMode: 'pro' }))}
            />
          </div>
        </Section>

        {/* Theme Section */}
        <Section title="Theme" description="Visual appearance (more themes coming soon)">
          <div style={{
            padding: 16,
            background: 'var(--bg3)',
            border: '1px solid var(--border)',
            borderRadius: 6,
            display: 'flex',
            alignItems: 'center',
            gap: 12,
          }}>
            <div style={{
              width: 40,
              height: 40,
              background: 'linear-gradient(135deg, var(--bg), var(--amber))',
              borderRadius: 6,
              border: '2px solid var(--amber)',
            }} />
            <div>
              <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 2 }}>
                Dark (Amber)
              </div>
              <div style={{ fontSize: 12, color: 'var(--text3)' }}>
                Current theme
              </div>
            </div>
          </div>
        </Section>

        {/* Actions */}
        <div style={{
          display: 'flex',
          gap: 12,
          marginTop: 32,
          paddingTop: 24,
          borderTop: '1px solid var(--border)',
        }}>
          <button
            onClick={saveSettings}
            style={{
              background: 'var(--amber)',
              color: 'var(--bg)',
              border: 'none',
              padding: '12px 24px',
              borderRadius: 6,
              fontSize: 14,
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.2s ease',
            }}
          >
            {saved ? '✓ Saved' : 'Save Settings'}
          </button>
          <button
            onClick={resetToDefaults}
            style={{
              background: 'transparent',
              color: 'var(--text3)',
              border: '1px solid var(--border)',
              padding: '12px 24px',
              borderRadius: 6,
              fontSize: 14,
              cursor: 'pointer',
              transition: 'all 0.2s ease',
            }}
            className="hover:border-border2"
          >
            Reset to Defaults
          </button>
        </div>

        {/* Info */}
        <div style={{
          marginTop: 24,
          padding: 16,
          background: 'var(--bg2)',
          border: '1px solid var(--border)',
          borderRadius: 6,
          fontSize: 12,
          color: 'var(--text3)',
          lineHeight: 1.6,
        }}>
          <strong style={{ color: 'var(--text2)' }}>Note:</strong> Settings are stored locally in your browser.
          They will persist across sessions but won't sync between devices.
        </div>
      </div>
    </div>
  );
}

function Section({ title, description, children }: {
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <div style={{ marginBottom: 32 }}>
      <div style={{ marginBottom: 16 }}>
        <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 4 }}>
          {title}
        </h2>
        <p style={{ fontSize: 13, color: 'var(--text3)' }}>
          {description}
        </p>
      </div>
      {children}
    </div>
  );
}

function ModeButton({ label, description, isSelected, onClick }: {
  label: string;
  description: string;
  isSelected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      style={{
        flex: 1,
        padding: 16,
        background: isSelected ? 'var(--amber)20' : 'var(--bg3)',
        border: `2px solid ${isSelected ? 'var(--amber)' : 'var(--border)'}`,
        borderRadius: 6,
        cursor: 'pointer',
        transition: 'all 0.2s ease',
        textAlign: 'left',
      }}
      className={!isSelected ? 'hover:border-border2' : ''}
    >
      <div style={{
        fontSize: 14,
        fontWeight: 600,
        color: isSelected ? 'var(--amber)' : 'var(--text)',
        marginBottom: 4,
      }}>
        {label}
      </div>
      <div style={{ fontSize: 12, color: 'var(--text3)' }}>
        {description}
      </div>
    </button>
  );
}

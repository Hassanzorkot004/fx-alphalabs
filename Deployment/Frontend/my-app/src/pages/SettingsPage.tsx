import { useState, useEffect } from 'react';
import { useTheme } from '../context/ThemeContext';

interface Settings {
  watchlist: string[];
  defaultMode: 'simple' | 'pro';
  theme: 'dark' | 'light';
}

const DEFAULT_SETTINGS: Settings = {
  watchlist: ['EURUSD', 'GBPUSD', 'USDJPY'],
  defaultMode: 'simple',
  theme: 'dark',
};

const AVAILABLE_PAIRS = ['EURUSD', 'GBPUSD', 'USDJPY'];

export default function SettingsPage() {
  const { theme, setTheme } = useTheme();

  const [settings, setSettings] = useState<Settings>(DEFAULT_SETTINGS);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem('fx-alphalab-settings');

    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        const nextSettings = { ...DEFAULT_SETTINGS, ...parsed };

        setSettings(nextSettings);

        if (nextSettings.theme === 'dark' || nextSettings.theme === 'light') {
          setTheme(nextSettings.theme);
        }
      } catch (err) {
        console.error('Failed to parse settings:', err);
      }
    }
  }, [setTheme]);

  const saveSettings = () => {
    const nextSettings = {
      ...settings,
      theme,
    };

    localStorage.setItem('fx-alphalab-settings', JSON.stringify(nextSettings));

    setSettings(nextSettings);
    setSaved(true);

    setTimeout(() => setSaved(false), 2000);
  };

  const togglePair = (pair: string) => {
    setSettings((prev) => ({
      ...prev,
      watchlist: prev.watchlist.includes(pair)
        ? prev.watchlist.filter((p) => p !== pair)
        : [...prev.watchlist, pair],
    }));
  };

  const resetToDefaults = () => {
    setSettings(DEFAULT_SETTINGS);
    setTheme(DEFAULT_SETTINGS.theme);

    localStorage.removeItem('fx-alphalab-settings');

    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)' }}>
      <div
        style={{
          background: 'var(--bg1)',
          borderBottom: '1px solid var(--border)',
          padding: '16px 24px',
        }}
      >
        <h1
          className="mono"
          style={{
            fontSize: 20,
            fontWeight: 600,
            color: 'var(--amber)',
            marginBottom: 4,
          }}
        >
          Settings
        </h1>

        <div style={{ fontSize: 13, color: 'var(--text3)' }}>
          Configure your FX AlphaLab preferences
        </div>
      </div>

      <div style={{ padding: 24, maxWidth: 850 }}>
        <Section title="Pair Watchlist" description="Select which currency pairs to display">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {AVAILABLE_PAIRS.map((pair) => (
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

        <Section
          title="Default AlphaBot Mode"
          description="Choose your preferred explanation style. You can quickly toggle this in the chat header."
        >
          <div style={{ display: 'flex', gap: 12 }}>
            <ModeButton
              label="Simple"
              description="Plain language, beginner-friendly"
              isSelected={settings.defaultMode === 'simple'}
              onClick={() =>
                setSettings((prev) => ({
                  ...prev,
                  defaultMode: 'simple',
                }))
              }
            />

            <ModeButton
              label="Pro"
              description="Technical terminology, detailed metrics"
              isSelected={settings.defaultMode === 'pro'}
              onClick={() =>
                setSettings((prev) => ({
                  ...prev,
                  defaultMode: 'pro',
                }))
              }
            />
          </div>
        </Section>

        <Section title="Theme" description="Choose your platform appearance">
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: 12,
            }}
          >
            <ThemeCard
              label="Dark"
              description="Professional trading desk style"
              selected={theme === 'dark'}
              preview="linear-gradient(135deg, #0a0906, #e8a030)"
              onClick={() => {
                setTheme('dark');
                setSettings((prev) => ({
                  ...prev,
                  theme: 'dark',
                }));
              }}
            />

            <ThemeCard
              label="Light"
              description="Clean financial dashboard"
              selected={theme === 'light'}
              preview="linear-gradient(135deg, #ffffff, #c8841a)"
              onClick={() => {
                setTheme('light');
                setSettings((prev) => ({
                  ...prev,
                  theme: 'light',
                }));
              }}
            />
          </div>
        </Section>

        <div
          style={{
            display: 'flex',
            gap: 12,
            marginTop: 32,
            paddingTop: 24,
            borderTop: '1px solid var(--border)',
          }}
        >
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
          >
            Reset to Defaults
          </button>
        </div>

        <div
          style={{
            marginTop: 24,
            padding: 16,
            background: 'var(--bg2)',
            border: '1px solid var(--border)',
            borderRadius: 6,
            fontSize: 12,
            color: 'var(--text3)',
            lineHeight: 1.6,
          }}
        >
          <strong style={{ color: 'var(--text2)' }}>Note:</strong> Settings are stored locally in your
          browser. They will persist across sessions but won&apos;t sync between devices.
        </div>
      </div>
    </div>
  );
}

function Section({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <div style={{ marginBottom: 32 }}>
      <div style={{ marginBottom: 16 }}>
        <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 4 }}>{title}</h2>
        <p style={{ fontSize: 13, color: 'var(--text3)' }}>{description}</p>
      </div>

      {children}
    </div>
  );
}

function ModeButton({
  label,
  description,
  isSelected,
  onClick,
}: {
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
    >
      <div
        style={{
          fontSize: 14,
          fontWeight: 600,
          color: isSelected ? 'var(--amber)' : 'var(--text)',
          marginBottom: 4,
        }}
      >
        {label}
      </div>

      <div style={{ fontSize: 12, color: 'var(--text3)' }}>{description}</div>
    </button>
  );
}

function ThemeCard({
  label,
  description,
  selected,
  preview,
  onClick,
}: {
  label: string;
  description: string;
  selected: boolean;
  preview: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: 16,
        background: selected ? 'var(--amber)15' : 'var(--bg3)',
        border: `2px solid ${selected ? 'var(--amber)' : 'var(--border)'}`,
        borderRadius: 8,
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        gap: 14,
        transition: 'all 0.2s ease',
        textAlign: 'left',
      }}
    >
      <div
        style={{
          width: 44,
          height: 44,
          borderRadius: 8,
          background: preview,
          border: '2px solid rgba(255,255,255,0.12)',
          flexShrink: 0,
        }}
      />

      <div>
        <div
          style={{
            fontSize: 14,
            fontWeight: 700,
            color: selected ? 'var(--amber)' : 'var(--text)',
            marginBottom: 4,
          }}
        >
          {label}
        </div>

        <div style={{ fontSize: 12, color: 'var(--text3)' }}>{description}</div>
      </div>
    </button>
  );
}
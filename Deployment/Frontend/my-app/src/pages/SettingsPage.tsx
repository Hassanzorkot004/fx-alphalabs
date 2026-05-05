import { useState, useEffect } from 'react';
import { notificationManager } from '../utils/notifications';

interface Settings {
  watchlist: string[];
  defaultMode: 'simple' | 'pro';
  theme: 'dark';
  notifications: {
    enabled: boolean;
    newSignals: boolean;
    directionChanges: boolean;
    highConfidence: boolean;
    confidenceThreshold: number;
    significantConfidenceChange: number;
    agentDisagreement: boolean;
  };
}

const DEFAULT_SETTINGS: Settings = {
  watchlist: ['EURUSD', 'GBPUSD', 'USDJPY'],
  defaultMode: 'simple',
  theme: 'dark',
  notifications: {
    enabled: false,
    newSignals: true,
    directionChanges: true,
    highConfidence: true,
    confidenceThreshold: 0.70,
    significantConfidenceChange: 0.10,
    agentDisagreement: true,
  },
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
    notificationManager.setEnabled(settings.notifications.enabled);
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
    notificationManager.setEnabled(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const enableNotifications = async () => {
    const permission = await notificationManager.requestPermission();
    if (permission === 'granted') {
      setSettings(prev => ({
        ...prev,
        notifications: { ...prev.notifications, enabled: true },
      }));
    }
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

        {/* Notifications Section */}
        <Section 
          title="Notifications" 
          description="Get alerted when important signal changes occur"
        >
          {!notificationManager.isSupported() ? (
            <div style={{
              padding: 16,
              background: 'var(--red)10',
              border: '1px solid var(--red)40',
              borderRadius: 6,
              color: 'var(--red)',
              fontSize: 13,
            }}>
              ⚠️ Your browser doesn't support notifications
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              {/* Enable/Disable Toggle */}
              <div style={{
                padding: 16,
                background: settings.notifications.enabled ? 'var(--green)10' : 'var(--bg3)',
                border: `1px solid ${settings.notifications.enabled ? 'var(--green)40' : 'var(--border)'}`,
                borderRadius: 6,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 4 }}>
                      {settings.notifications.enabled ? '🔔 Notifications Enabled' : '🔕 Notifications Disabled'}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--text3)' }}>
                      {settings.notifications.enabled 
                        ? 'You\'ll receive alerts for signal changes'
                        : 'Enable to get real-time alerts'}
                    </div>
                  </div>
                  {!settings.notifications.enabled && notificationManager.getPermission() !== 'granted' ? (
                    <button
                      onClick={enableNotifications}
                      style={{
                        background: 'var(--amber)',
                        color: 'var(--bg)',
                        border: 'none',
                        padding: '8px 16px',
                        borderRadius: 4,
                        fontSize: 13,
                        fontWeight: 600,
                        cursor: 'pointer',
                      }}
                    >
                      Enable
                    </button>
                  ) : (
                    <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
                      <input
                        type="checkbox"
                        checked={settings.notifications.enabled}
                        onChange={(e) => setSettings(prev => ({
                          ...prev,
                          notifications: { ...prev.notifications, enabled: e.target.checked },
                        }))}
                        style={{
                          width: 20,
                          height: 20,
                          cursor: 'pointer',
                          accentColor: 'var(--amber)',
                        }}
                      />
                    </label>
                  )}
                </div>
              </div>

              {/* Notification Types */}
              {settings.notifications.enabled && (
                <div style={{
                  padding: 16,
                  background: 'var(--bg3)',
                  border: '1px solid var(--border)',
                  borderRadius: 6,
                }}>
                  <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 12, color: 'var(--text2)' }}>
                    Alert Types
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                    <NotificationToggle
                      label="New Signals"
                      description="When a new signal is generated"
                      checked={settings.notifications.newSignals}
                      onChange={(checked) => setSettings(prev => ({
                        ...prev,
                        notifications: { ...prev.notifications, newSignals: checked },
                      }))}
                    />
                    <NotificationToggle
                      label="Direction Changes"
                      description="When BUY/SELL direction flips"
                      checked={settings.notifications.directionChanges}
                      onChange={(checked) => setSettings(prev => ({
                        ...prev,
                        notifications: { ...prev.notifications, directionChanges: checked },
                      }))}
                    />
                    <NotificationToggle
                      label="High Confidence Signals"
                      description={`When confidence exceeds ${(settings.notifications.confidenceThreshold * 100).toFixed(0)}%`}
                      checked={settings.notifications.highConfidence}
                      onChange={(checked) => setSettings(prev => ({
                        ...prev,
                        notifications: { ...prev.notifications, highConfidence: checked },
                      }))}
                    />
                    <NotificationToggle
                      label="Agent Disagreements"
                      description="When agents conflict on direction"
                      checked={settings.notifications.agentDisagreement}
                      onChange={(checked) => setSettings(prev => ({
                        ...prev,
                        notifications: { ...prev.notifications, agentDisagreement: checked },
                      }))}
                    />
                  </div>

                  {/* Thresholds */}
                  <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid var(--border)' }}>
                    <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 12, color: 'var(--text2)' }}>
                      Thresholds
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                      <div>
                        <label style={{ fontSize: 12, color: 'var(--text3)', display: 'block', marginBottom: 6 }}>
                          High Confidence Threshold: {(settings.notifications.confidenceThreshold * 100).toFixed(0)}%
                        </label>
                        <input
                          type="range"
                          min="50"
                          max="90"
                          step="5"
                          value={settings.notifications.confidenceThreshold * 100}
                          onChange={(e) => setSettings(prev => ({
                            ...prev,
                            notifications: { ...prev.notifications, confidenceThreshold: parseInt(e.target.value) / 100 },
                          }))}
                          style={{ width: '100%', accentColor: 'var(--amber)' }}
                        />
                      </div>
                      <div>
                        <label style={{ fontSize: 12, color: 'var(--text3)', display: 'block', marginBottom: 6 }}>
                          Significant Confidence Change: {(settings.notifications.significantConfidenceChange * 100).toFixed(0)}%
                        </label>
                        <input
                          type="range"
                          min="5"
                          max="25"
                          step="5"
                          value={settings.notifications.significantConfidenceChange * 100}
                          onChange={(e) => setSettings(prev => ({
                            ...prev,
                            notifications: { ...prev.notifications, significantConfidenceChange: parseInt(e.target.value) / 100 },
                          }))}
                          style={{ width: '100%', accentColor: 'var(--amber)' }}
                        />
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
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

function NotificationToggle({ label, description, checked, onChange }: {
  label: string;
  description: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <label style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: 10,
      background: 'var(--bg4)',
      borderRadius: 4,
      cursor: 'pointer',
    }}>
      <div>
        <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 2 }}>
          {label}
        </div>
        <div style={{ fontSize: 11, color: 'var(--text3)' }}>
          {description}
        </div>
      </div>
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        style={{
          width: 18,
          height: 18,
          cursor: 'pointer',
          accentColor: 'var(--amber)',
        }}
      />
    </label>
  );
}

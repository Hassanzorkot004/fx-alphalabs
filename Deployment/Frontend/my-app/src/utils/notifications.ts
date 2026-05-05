/**
 * Browser notification utilities for FX AlphaLab
 */

export type NotificationPermission = 'granted' | 'denied' | 'default';

export interface NotificationOptions {
  title: string;
  body: string;
  icon?: string;
  tag?: string;
  requireInteraction?: boolean;
  silent?: boolean;
}

class NotificationManager {
  private permission: NotificationPermission = 'default';
  private enabled: boolean = false;

  constructor() {
    if ('Notification' in window) {
      this.permission = Notification.permission as NotificationPermission;
      this.loadSettings();
    }
  }

  private loadSettings() {
    try {
      const stored = localStorage.getItem('fx-alphalab-settings');
      if (stored) {
        const settings = JSON.parse(stored);
        this.enabled = settings.notifications?.enabled ?? false;
      }
    } catch (err) {
      console.error('Failed to load notification settings:', err);
    }
  }

  async requestPermission(): Promise<NotificationPermission> {
    if (!('Notification' in window)) {
      console.warn('Browser does not support notifications');
      return 'denied';
    }

    if (this.permission === 'granted') {
      return 'granted';
    }

    try {
      const permission = await Notification.requestPermission();
      this.permission = permission as NotificationPermission;
      return this.permission;
    } catch (err) {
      console.error('Failed to request notification permission:', err);
      return 'denied';
    }
  }

  isSupported(): boolean {
    return 'Notification' in window;
  }

  isEnabled(): boolean {
    return this.enabled && this.permission === 'granted';
  }

  setEnabled(enabled: boolean) {
    this.enabled = enabled;
  }

  getPermission(): NotificationPermission {
    return this.permission;
  }

  async show(options: NotificationOptions): Promise<void> {
    if (!this.isEnabled()) {
      return;
    }

    try {
      const notification = new Notification(options.title, {
        body: options.body,
        icon: options.icon || '/favicon.svg',
        tag: options.tag,
        requireInteraction: options.requireInteraction ?? false,
        silent: options.silent ?? false,
      });

      // Auto-close after 10 seconds unless requireInteraction is true
      if (!options.requireInteraction) {
        setTimeout(() => notification.close(), 10000);
      }

      // Focus window when notification is clicked
      notification.onclick = () => {
        window.focus();
        notification.close();
      };
    } catch (err) {
      console.error('Failed to show notification:', err);
    }
  }

  // Convenience methods for common notification types
  async notifyNewSignal(pair: string, direction: string, confidence: number) {
    const emoji = direction === 'BUY' ? '📈' : direction === 'SELL' ? '📉' : '⏸️';
    await this.show({
      title: `${emoji} New Signal: ${pair}`,
      body: `${direction} signal with ${(confidence * 100).toFixed(0)}% confidence`,
      tag: `signal-${pair}`,
    });
  }

  async notifyDirectionChange(pair: string, oldDirection: string, newDirection: string, confidence: number) {
    const emoji = newDirection === 'BUY' ? '📈' : '📉';
    await this.show({
      title: `${emoji} ${pair} Direction Changed`,
      body: `${oldDirection} → ${newDirection} (${(confidence * 100).toFixed(0)}% confidence)`,
      tag: `direction-${pair}`,
      requireInteraction: true,
    });
  }

  async notifyHighConfidence(pair: string, direction: string, confidence: number) {
    const emoji = direction === 'BUY' ? '🚀' : '⚡';
    await this.show({
      title: `${emoji} High Confidence Signal`,
      body: `${pair} ${direction} at ${(confidence * 100).toFixed(0)}% confidence`,
      tag: `high-conf-${pair}`,
      requireInteraction: true,
    });
  }

  async notifyConfidenceChange(pair: string, direction: string, oldConf: number, newConf: number) {
    const change = newConf - oldConf;
    const emoji = change > 0 ? '📊' : '📉';
    const changeStr = change > 0 ? `+${(change * 100).toFixed(0)}` : `${(change * 100).toFixed(0)}`;
    
    await this.show({
      title: `${emoji} ${pair} Confidence Update`,
      body: `${direction} signal: ${(oldConf * 100).toFixed(0)}% → ${(newConf * 100).toFixed(0)}% (${changeStr}%)`,
      tag: `conf-${pair}`,
    });
  }

  async notifyAgentDisagreement(pair: string, direction: string, agreement: string) {
    await this.show({
      title: `⚠️ ${pair} Agent Conflict`,
      body: `${direction} signal with ${agreement} agreement - review recommended`,
      tag: `conflict-${pair}`,
    });
  }
}

// Global instance
export const notificationManager = new NotificationManager();

import { useEffect, useRef } from 'react';
import { notificationManager } from '../utils/notifications';
import type { Signal } from '../Types';

interface NotificationSettings {
  enabled: boolean;
  newSignals: boolean;
  directionChanges: boolean;
  highConfidence: boolean;
  confidenceThreshold: number;
  significantConfidenceChange: number;
  agentDisagreement: boolean;
}

const DEFAULT_SETTINGS: NotificationSettings = {
  enabled: false,
  newSignals: true,
  directionChanges: true,
  highConfidence: true,
  confidenceThreshold: 0.70,
  significantConfidenceChange: 0.10,
  agentDisagreement: true,
};

export function useNotifications(signals: Signal[]) {
  const previousSignals = useRef<Map<string, Signal>>(new Map());
  const settings = useRef<NotificationSettings>(DEFAULT_SETTINGS);

  // Load settings
  useEffect(() => {
    try {
      const stored = localStorage.getItem('fx-alphalab-settings');
      if (stored) {
        const parsed = JSON.parse(stored);
        if (parsed.notifications) {
          settings.current = { ...DEFAULT_SETTINGS, ...parsed.notifications };
          notificationManager.setEnabled(settings.current.enabled);
        }
      }
    } catch (err) {
      console.error('Failed to load notification settings:', err);
    }
  }, []);

  // Monitor signal changes
  useEffect(() => {
    if (!settings.current.enabled || !notificationManager.isEnabled()) {
      return;
    }

    signals.forEach(signal => {
      const pair = signal.pair;
      const previous = previousSignals.current.get(pair);

      if (!previous) {
        // New signal (first time seeing this pair)
        if (settings.current.newSignals) {
          notificationManager.notifyNewSignal(
            pair.replace('=X', ''),
            signal.direction,
            signal.confidence
          );
        }

        // Check if it's high confidence
        if (settings.current.highConfidence && signal.confidence >= settings.current.confidenceThreshold) {
          notificationManager.notifyHighConfidence(
            pair.replace('=X', ''),
            signal.direction,
            signal.confidence
          );
        }

        // Check for agent disagreement
        if (settings.current.agentDisagreement && signal.agent_agreement === 'CONFLICT') {
          notificationManager.notifyAgentDisagreement(
            pair.replace('=X', ''),
            signal.direction,
            signal.agent_agreement
          );
        }
      } else {
        // Existing signal - check for changes
        
        // Direction change
        if (settings.current.directionChanges && previous.direction !== signal.direction) {
          notificationManager.notifyDirectionChange(
            pair.replace('=X', ''),
            previous.direction,
            signal.direction,
            signal.confidence
          );
        }

        // Significant confidence change
        const confChange = Math.abs(signal.confidence - previous.confidence);
        if (confChange >= settings.current.significantConfidenceChange) {
          notificationManager.notifyConfidenceChange(
            pair.replace('=X', ''),
            signal.direction,
            previous.confidence,
            signal.confidence
          );
        }

        // Crossed high confidence threshold
        if (settings.current.highConfidence) {
          const wasLow = previous.confidence < settings.current.confidenceThreshold;
          const isHigh = signal.confidence >= settings.current.confidenceThreshold;
          if (wasLow && isHigh) {
            notificationManager.notifyHighConfidence(
              pair.replace('=X', ''),
              signal.direction,
              signal.confidence
            );
          }
        }

        // New agent disagreement
        if (settings.current.agentDisagreement) {
          const hadAgreement = previous.agent_agreement !== 'CONFLICT';
          const hasConflict = signal.agent_agreement === 'CONFLICT';
          if (hadAgreement && hasConflict) {
            notificationManager.notifyAgentDisagreement(
              pair.replace('=X', ''),
              signal.direction,
              signal.agent_agreement
            );
          }
        }
      }

      // Update previous signals map
      previousSignals.current.set(pair, signal);
    });
  }, [signals]);

  return {
    isSupported: notificationManager.isSupported(),
    isEnabled: notificationManager.isEnabled(),
    permission: notificationManager.getPermission(),
    requestPermission: () => notificationManager.requestPermission(),
  };
}

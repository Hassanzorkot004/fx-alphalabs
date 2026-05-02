import { useState, useCallback, useEffect } from 'react';
import type { ChatMessage, Signal } from '../Types';
import { API_BASE_URL } from '../config/constants';

interface AlphaBotState {
  messages: ChatMessage[];
  isLoading: boolean;
  error: string | null;
  mode: 'simple' | 'pro';
}

function getAuthHeaders() {
  const token = localStorage.getItem('fx_token');

  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  };
}

function handleUnauthorized() {
  localStorage.removeItem('fx_token');
  localStorage.removeItem('fx_user');
  window.location.reload();
}

export function useAlphaBot(
  pair: string,
  signal: Signal | null,
  useStreaming: boolean = true
) {
  const getInitialMode = (): 'simple' | 'pro' => {
    try {
      const stored = localStorage.getItem('fx-alphalab-settings');
      if (stored) {
        const settings = JSON.parse(stored);
        return settings.defaultMode || 'simple';
      }
    } catch (err) {
      console.error('Failed to load default mode:', err);
    }

    return 'simple';
  };

  const [state, setState] = useState<AlphaBotState>({
    messages: [],
    isLoading: false,
    error: null,
    mode: getInitialMode(),
  });

  useEffect(() => {
    if (signal) {
      const welcomeMessage = formatWelcomeMessage(signal);

      setState(prev => ({
        ...prev,
        messages: [{ role: 'assistant', content: welcomeMessage }],
      }));
    } else {
      setState(prev => ({
        ...prev,
        messages: [],
      }));
    }
  }, [pair, signal]);

  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim()) return;

      const userMessage: ChatMessage = {
        role: 'user',
        content,
      };

      setState(prev => ({
        ...prev,
        messages: [...prev.messages, userMessage],
        isLoading: true,
        error: null,
      }));

      if (useStreaming) {
        try {
          const response = await fetch(`${API_BASE_URL}/api/alphabot/chat/stream`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
              pair,
              message: content,
              mode: state.mode,
              history: state.messages,
            }),
          });

          if (response.status === 401 || response.status === 403) {
            handleUnauthorized();
            return;
          }

          if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
          }

          const reader = response.body?.getReader();
          const decoder = new TextDecoder();
          let accumulatedContent = '';

          if (reader) {
            while (true) {
              const { done, value } = await reader.read();

              if (done) break;

              const chunk = decoder.decode(value);
              const lines = chunk.split('\n');

              for (const line of lines) {
                if (line.startsWith('data: ')) {
                  try {
                    const data = JSON.parse(line.slice(6));

                    if (data.error) {
                      setState(prev => ({
                        ...prev,
                        error: data.error,
                        isLoading: false,
                      }));
                      return;
                    }

                    if (data.content) {
                      accumulatedContent += data.content;

                      setState(prev => {
                        const newMessages = [...prev.messages];
                        const lastMsg = newMessages[newMessages.length - 1];

                        if (lastMsg && lastMsg.role === 'assistant') {
                          newMessages[newMessages.length - 1] = {
                            role: 'assistant',
                            content: accumulatedContent,
                          };
                        } else {
                          newMessages.push({
                            role: 'assistant',
                            content: accumulatedContent,
                          });
                        }

                        return {
                          ...prev,
                          messages: newMessages,
                          isLoading: !data.done,
                        };
                      });
                    }

                    if (data.done) {
                      setState(prev => ({
                        ...prev,
                        isLoading: false,
                      }));
                      return;
                    }
                  } catch {
                    // Ignore incomplete streaming chunks
                  }
                }
              }
            }
          }
        } catch (err) {
          const errorMsg =
            err instanceof Error ? err.message : 'Failed to reach AlphaBot';

          setState(prev => ({
            ...prev,
            error: errorMsg,
            isLoading: false,
          }));
        }
      } else {
        try {
          const response = await fetch(`${API_BASE_URL}/api/alphabot/chat`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
              pair,
              message: content,
              mode: state.mode,
              history: state.messages,
            }),
          });

          if (response.status === 401 || response.status === 403) {
            handleUnauthorized();
            return;
          }

          if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
          }

          const data = await response.json();

          const botMessage: ChatMessage = {
            role: 'assistant',
            content: data.reply,
          };

          setState(prev => ({
            ...prev,
            messages: [...prev.messages, botMessage],
            isLoading: false,
          }));
        } catch (err) {
          const errorMsg =
            err instanceof Error ? err.message : 'Failed to reach AlphaBot';

          setState(prev => ({
            ...prev,
            error: errorMsg,
            isLoading: false,
          }));
        }
      }
    },
    [pair, state.mode, state.messages, useStreaming]
  );

  const toggleMode = useCallback(() => {
    setState(prev => ({
      ...prev,
      mode: prev.mode === 'simple' ? 'pro' : 'simple',
    }));
  }, []);

  const clearChat = useCallback(() => {
    setState(prev => ({
      ...prev,
      messages: [],
      error: null,
    }));
  }, []);

  return {
    messages: state.messages,
    isLoading: state.isLoading,
    error: state.error,
    mode: state.mode,
    sendMessage,
    toggleMode,
    clearChat,
  };
}

function formatWelcomeMessage(signal: Signal): string {
  const pairName = signal.pair.replace('=X', '');
  const direction = signal.direction;
  const confidence = Math.round(signal.confidence * 100);

  return `We have a ${direction} signal for ${pairName}, with ${confidence}% confidence.

The reason for the ${direction} signal is that ${signal.reasoning}`;
}
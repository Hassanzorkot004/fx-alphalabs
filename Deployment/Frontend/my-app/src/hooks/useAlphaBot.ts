import { useState, useCallback } from 'react';
import type { ChatMessage } from '../Types';
import { API_BASE_URL } from '../config/constants';

interface AlphaBotState {
  messages: ChatMessage[];
  isLoading: boolean;
  error: string | null;
  mode: 'simple' | 'pro';
}

export function useAlphaBot(pair: string, useStreaming: boolean = true) {
  const [state, setState] = useState<AlphaBotState>({
    messages: [],
    isLoading: false,
    error: null,
    mode: 'simple',
  });

  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim()) return;

    const userMessage: ChatMessage = { role: 'user', content };
    
    setState(prev => ({
      ...prev,
      messages: [...prev.messages, userMessage],
      isLoading: true,
      error: null,
    }));

    if (useStreaming) {
      // Streaming mode
      try {
        const response = await fetch(`${API_BASE_URL}/api/alphabot/chat/stream`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            pair,
            message: content,
            mode: state.mode,
            history: state.messages,
          }),
        });

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
                    
                    // Update the last message (bot's response) in real-time
                    setState(prev => {
                      const newMessages = [...prev.messages];
                      const lastMsg = newMessages[newMessages.length - 1];
                      
                      if (lastMsg && lastMsg.role === 'assistant') {
                        // Update existing assistant message
                        newMessages[newMessages.length - 1] = {
                          role: 'assistant',
                          content: accumulatedContent,
                        };
                      } else {
                        // Add new assistant message
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
                    setState(prev => ({ ...prev, isLoading: false }));
                    return;
                  }
                } catch (e) {
                  // Ignore parse errors for incomplete chunks
                }
              }
            }
          }
        }
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Failed to reach AlphaBot';
        setState(prev => ({
          ...prev,
          error: errorMsg,
          isLoading: false,
        }));
      }
    } else {
      // Non-streaming mode (fallback)
      try {
        const response = await fetch(`${API_BASE_URL}/api/alphabot/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            pair,
            message: content,
            mode: state.mode,
            history: state.messages,
          }),
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();
        const botMessage: ChatMessage = { role: 'assistant', content: data.reply };

        setState(prev => ({
          ...prev,
          messages: [...prev.messages, botMessage],
          isLoading: false,
        }));
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Failed to reach AlphaBot';
        setState(prev => ({
          ...prev,
          error: errorMsg,
          isLoading: false,
        }));
      }
    }
  }, [pair, state.mode, state.messages, useStreaming]);

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

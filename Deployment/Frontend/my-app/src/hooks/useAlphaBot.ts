import { useState, useCallback, useEffect, useRef } from 'react';
import type { ChatMessage, Signal } from '../Types';
import { API_BASE_URL } from '../config/constants';

const HISTORY_KEY = 'alphabot_chat_history';
const MAX_THREADS = 20;

// ── Types ──────────────────────────────────────────────────────────────────
interface ChatThread {
  id: string;
  pair: string;
  title: string;
  messages: ChatMessage[];
  createdAt: string;
  updatedAt: string;
}

// ── localStorage helpers ──────────────────────────────────────────────────
function loadThreads(): ChatThread[] {
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch { return []; }
}

function saveThreads(threads: ChatThread[]) {
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(threads.slice(0, MAX_THREADS)));
  } catch {}
}

// ── Hook ───────────────────────────────────────────────────────────────────
export function useAlphaBot(pair: string, signal: Signal | null) {
  const [threads, setThreads] = useState<ChatThread[]>(loadThreads);
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<'simple' | 'pro'>(() => {
    try { return localStorage.getItem('alphabot_chat_mode') === 'pro' ? 'pro' : 'simple'; }
    catch { return 'simple'; }
  });
  const pairRef = useRef(pair);
  pairRef.current = pair;

  // Get active thread
  const activeThread = threads.find(t => t.id === activeThreadId) || null;
  const messages = activeThread?.messages || [];

  // Persist threads on change
  useEffect(() => { saveThreads(threads); }, [threads]);

  // Create new thread if none active
  const ensureThread = useCallback(() => {
    if (!activeThreadId) {
      const cleanPair = pairRef.current.replace('=X', '');
      const newThread: ChatThread = {
        id: Date.now().toString(36) + Math.random().toString(36).slice(2, 6),
        pair: cleanPair,
        title: `${cleanPair} Chat`,
        messages: [],
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };
      setThreads(prev => [newThread, ...prev]);
      setActiveThreadId(newThread.id);
      return newThread.id;
    }
    return activeThreadId;
  }, [activeThreadId]);

  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim()) return;

    const threadId = ensureThread();
    const userMessage: ChatMessage = { role: 'user', content };
    const currentPair = pairRef.current;

    // Add user message to thread
    setThreads(prev => prev.map(t => {
      if (t.id === threadId) {
        const title = t.messages.length === 0
          ? content.slice(0, 40) + (content.length > 40 ? '...' : '')
          : t.title;
        return {
          ...t,
          title,
          messages: [...t.messages, userMessage],
          pair: currentPair.replace('=X', ''),
          updatedAt: new Date().toISOString(),
        };
      }
      return t;
    }));

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/alphabot/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          pair: currentPair,
          message: content,
          mode,
          history: (activeThread?.messages || []).slice(-10),
        }),
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let accumulatedContent = '';

      if (reader) {
        // Add empty assistant placeholder
        setThreads(prev => prev.map(t => {
          if (t.id === threadId) {
            return { ...t, messages: [...t.messages, { role: 'assistant', content: '' }], updatedAt: new Date().toISOString() };
          }
          return t;
        }));

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));

                if (data.error) {
                  setError(data.error);
                  setIsLoading(false);
                  return;
                }

                if (data.content) {
                  accumulatedContent += data.content;
                  setThreads(prev => prev.map(t => {
                    if (t.id === threadId) {
                      const msgs = [...t.messages];
                      msgs[msgs.length - 1] = { role: 'assistant', content: accumulatedContent };
                      return { ...t, messages: msgs, updatedAt: new Date().toISOString() };
                    }
                    return t;
                  }));
                }

                if (data.done) {
                  setIsLoading(false);
                  return;
                }
              } catch { /* skip incomplete chunks */ }
            }
          }
        }
      }
    } catch (err) {
      // Fallback non-streaming
      try {
        const response = await fetch(`${API_BASE_URL}/api/alphabot/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ pair: currentPair, message: content, mode, history: (activeThread?.messages || []).slice(-10) }),
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        setThreads(prev => prev.map(t => {
          if (t.id === threadId) {
            return { ...t, messages: [...t.messages, { role: 'assistant', content: data.reply }], updatedAt: new Date().toISOString() };
          }
          return t;
        }));
      } catch (e) {
        setError(err instanceof Error ? err.message : 'Failed to reach AlphaBot');
      }
      setIsLoading(false);
    }
  }, [ensureThread, mode, activeThread]);

  const switchThread = useCallback((threadId: string) => {
    setActiveThreadId(threadId);
  }, []);

  const deleteThread = useCallback((threadId: string) => {
    setThreads(prev => {
      const filtered = prev.filter(t => t.id !== threadId);
      if (activeThreadId === threadId) {
        setActiveThreadId(filtered[0]?.id || null);
      }
      return filtered;
    });
  }, [activeThreadId]);

  const clearChat = useCallback(() => {
    setThreads([]);
    setActiveThreadId(null);
    localStorage.removeItem(HISTORY_KEY);
  }, []);

  const toggleMode = useCallback(() => {
    setMode(prev => {
      const next = prev === 'simple' ? 'pro' : 'simple';
      localStorage.setItem('alphabot_chat_mode', next);
      return next;
    });
  }, []);

  // Start a fresh thread when user sends from news/event click
  const startNewThread = useCallback(() => {
    setActiveThreadId(null);
  }, []);

  return {
    messages,
    threads,
    activeThreadId,
    isLoading,
    error,
    mode,
    sendMessage,
    toggleMode,
    clearChat,
    switchThread,
    deleteThread,
    startNewThread,
  };
}
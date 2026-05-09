import { useState, useCallback, useEffect, useRef } from 'react';
import type { ChatMessage, Signal } from '../Types';
import { API_BASE_URL } from '../config/constants';

// ── Data model ────────────────────────────────────────────────────
export interface Conversation {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  messages: ChatMessage[];
}

const STORAGE_KEY = 'fx-alphalab-conversations';

// ── Persistence helpers ───────────────────────────────────────────
function loadConversations(): Conversation[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw) as Conversation[];
  } catch { /* ignore */ }
  return [];
}

function saveConversations(convos: Conversation[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(convos));
  } catch { /* ignore */ }
}

function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function titleFromMessage(content: string): string {
  const trimmed = content.trim();
  return trimmed.length > 52 ? trimmed.slice(0, 52) + '…' : trimmed;
}

// ── Hook ──────────────────────────────────────────────────────────
interface AlphaBotState {
  conversations: Conversation[];
  activeId: string | null;
  isLoading: boolean;
  error: string | null;
  mode: 'simple' | 'pro';
}

function getInitialMode(): 'simple' | 'pro' {
  try {
    const raw = localStorage.getItem('fx-alphalab-settings');
    if (raw) return JSON.parse(raw).defaultMode || 'simple';
  } catch { /* ignore */ }
  return 'simple';
}

export function useAlphaBot(currentPair: string, _signal: Signal | null) {
  const [state, setState] = useState<AlphaBotState>(() => ({
    conversations: loadConversations(),
    activeId: null,
    isLoading: false,
    error: null,
    mode: getInitialMode(),
  }));

  const stateRef = useRef(state);
  useEffect(() => { stateRef.current = state; }, [state]);

  // Persist whenever conversations change
  useEffect(() => {
    saveConversations(state.conversations);
  }, [state.conversations]);

  const activeConversation = state.conversations.find(c => c.id === state.activeId) ?? null;
  const messages = activeConversation?.messages ?? [];

  // ── Create a new blank conversation ──────────────────────────
  const newConversation = useCallback(() => {
    const id = generateId();
    const now = new Date().toISOString();
    const convo: Conversation = {
      id,
      title: 'New conversation',
      createdAt: now,
      updatedAt: now,
      messages: [],
    };
    setState(prev => ({
      ...prev,
      conversations: [convo, ...prev.conversations],
      activeId: id,
      error: null,
    }));
    return id;
  }, []);

  // ── Switch to an existing conversation ───────────────────────
  const selectConversation = useCallback((id: string) => {
    setState(prev => ({ ...prev, activeId: id, error: null }));
  }, []);

  // ── Delete a conversation ─────────────────────────────────────
  const deleteConversation = useCallback((id: string) => {
    setState(prev => {
      const remaining = prev.conversations.filter(c => c.id !== id);
      const newActiveId = prev.activeId === id
        ? (remaining[0]?.id ?? null)
        : prev.activeId;
      return { ...prev, conversations: remaining, activeId: newActiveId };
    });
  }, []);

  // ── Send a message ────────────────────────────────────────────
  // currentPair is the dashboard's selected pair at the time of sending —
  // it's passed per-message to the backend, not locked to the conversation.
  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim()) return;

    // Auto-create a conversation if none is active
    let convId = stateRef.current.activeId;
    if (!convId) {
      convId = generateId();
      const now = new Date().toISOString();
      const convo: Conversation = {
        id: convId,
        title: titleFromMessage(content),
        createdAt: now,
        updatedAt: now,
        messages: [],
      };
      setState(prev => ({
        ...prev,
        conversations: [convo, ...prev.conversations],
        activeId: convId!,
      }));
    }

    const targetId = convId;
    const userMessage: ChatMessage = { role: 'user', content };

    setState(prev => {
      const convos = prev.conversations.map(c => {
        if (c.id !== targetId) return c;
        const isFirstUserMsg = !c.messages.some(m => m.role === 'user');
        return {
          ...c,
          title: isFirstUserMsg ? titleFromMessage(content) : c.title,
          updatedAt: new Date().toISOString(),
          messages: [...c.messages, userMessage],
        };
      });
      return { ...prev, conversations: convos, isLoading: true, error: null };
    });

    try {
      // Build history from what was in the convo before this message
      const prevMessages = stateRef.current.conversations.find(c => c.id === targetId)?.messages ?? [];
      const historyForApi = prevMessages.filter(m => m !== userMessage);

      const response = await fetch(`${API_BASE_URL}/api/alphabot/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          pair: currentPair,          // current dashboard pair, per-message
          message: content,
          mode: stateRef.current.mode,
          history: historyForApi,
        }),
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let accumulated = '';

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          for (const line of decoder.decode(value).split('\n')) {
            if (!line.startsWith('data: ')) continue;
            try {
              const data = JSON.parse(line.slice(6));

              if (data.error) {
                setState(prev => ({ ...prev, error: data.error, isLoading: false }));
                return;
              }

              if (data.content) {
                accumulated += data.content;
                setState(prev => {
                  const convos = prev.conversations.map(c => {
                    if (c.id !== targetId) return c;
                    const msgs = [...c.messages];
                    const last = msgs[msgs.length - 1];
                    if (last?.role === 'assistant') {
                      msgs[msgs.length - 1] = { role: 'assistant', content: accumulated };
                    } else {
                      msgs.push({ role: 'assistant', content: accumulated });
                    }
                    return { ...c, messages: msgs, updatedAt: new Date().toISOString() };
                  });
                  return { ...prev, conversations: convos, isLoading: !data.done };
                });
              }

              if (data.done) {
                setState(prev => ({ ...prev, isLoading: false }));
                return;
              }
            } catch { /* incomplete chunk */ }
          }
        }
      }
      setState(prev => ({ ...prev, isLoading: false }));
    } catch (err) {
      setState(prev => ({
        ...prev,
        error: err instanceof Error ? err.message : 'Failed to reach AlphaBot',
        isLoading: false,
      }));
    }
  }, [currentPair]);

  // ── Toggle mode ───────────────────────────────────────────────
  const toggleMode = useCallback(() => {
    setState(prev => ({ ...prev, mode: prev.mode === 'simple' ? 'pro' : 'simple' }));
  }, []);

  // ── Clear active conversation messages ────────────────────────
  const clearChat = useCallback(() => {
    setState(prev => {
      if (!prev.activeId) return prev;
      const convos = prev.conversations.map(c =>
        c.id === prev.activeId
          ? { ...c, messages: [], title: 'New conversation', updatedAt: new Date().toISOString() }
          : c
      );
      return { ...prev, conversations: convos, error: null };
    });
  }, []);

  return {
    conversations: state.conversations,
    activeId: state.activeId,
    activeConversation,
    messages,
    isLoading: state.isLoading,
    error: state.error,
    mode: state.mode,
    sendMessage,
    newConversation,
    selectConversation,
    deleteConversation,
    toggleMode,
    clearChat,
  };
}

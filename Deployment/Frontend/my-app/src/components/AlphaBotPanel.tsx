import { useState, useRef, useEffect, useCallback } from 'react';
import { useAlphaBot } from '../hooks/useAlphaBot';
import type { Signal } from '../Types';

interface AlphaBotPanelProps {
  pair: string;
  signal: Signal | null;
  onSendRef?: (fn: (msg: string) => void) => void;
  autoOpen?: boolean;
}

const FRIENDLY_EXAMPLES = [
  "Why this direction?",
  "Explain like I'm new to forex",
  "What's the biggest risk?",
  "Show me trade levels",
];

export default function AlphaBotPanel({ pair, signal, onSendRef, autoOpen }: AlphaBotPanelProps) {
  const { messages, threads, activeThreadId, isLoading, error, mode, sendMessage, toggleMode, clearChat, switchThread, deleteThread, startNewThread } = useAlphaBot(pair, signal);
  const [input, setInput] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => { onSendRef?.(sendMessage); }, [sendMessage, onSendRef]);
  useEffect(() => { if (autoOpen) { setIsOpen(true); startNewThread(); } }, [autoOpen]);
  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);
  useEffect(() => { if (isOpen) setTimeout(() => inputRef.current?.focus(), 100); }, [isOpen]);

  const handleSend = useCallback((text?: string) => {
    const msg = text || input.trim();
    if (!msg || isLoading) return;
    sendMessage(msg);
    setInput('');
  }, [input, isLoading, sendMessage]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  const cleanPair = pair.replace('=X', '');

  if (!isOpen) {
    return (
      <button onClick={() => setIsOpen(true)} style={{
        position: 'fixed', bottom: 24, right: 24, width: 56, height: 56, borderRadius: '50%',
        background: 'linear-gradient(135deg, #00e5ff, #00bfa5)', border: 'none', color: '#000',
        fontSize: 22, cursor: 'pointer', boxShadow: '0 4px 24px rgba(0,229,255,0.3)', zIndex: 1000,
        display: 'flex', alignItems: 'center', justifyContent: 'center', transition: 'transform 0.2s ease',
      }}
        onMouseEnter={e => { e.currentTarget.style.transform = 'scale(1.08)'; e.currentTarget.style.boxShadow = '0 6px 32px rgba(0,229,255,0.4)'; }}
        onMouseLeave={e => { e.currentTarget.style.transform = 'scale(1)'; e.currentTarget.style.boxShadow = '0 4px 24px rgba(0,229,255,0.3)'; }}
        title="Chat with AlphaBot">💬</button>
    );
  }

  return (
    <>
      <div onClick={() => setIsOpen(false)} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.45)', zIndex: 1001 }} />
      <div style={{
        position: 'fixed', bottom: 16, right: 16, width: showHistory ? 680 : 420, maxWidth: 'calc(100vw - 32px)',
        height: 580, maxHeight: 'calc(100vh - 100px)',
        background: 'var(--bg2)', border: '1px solid rgba(0,229,255,0.12)', borderRadius: 16,
        display: 'flex', flexDirection: 'column', zIndex: 1002,
        boxShadow: '0 8px 40px rgba(0,0,0,0.6), 0 0 0 1px rgba(0,229,255,0.06)',
        animation: 'slideUp 0.3s ease', transition: 'width 0.3s ease', backdropFilter: 'blur(24px)',
      }}>
        <div style={{ padding: '14px 18px', borderBottom: '1px solid rgba(0,229,255,0.08)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--bg3)', borderRadius: '16px 16px 0 0' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ fontSize: 22 }}>🤖</span>
            <div>
              <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text)' }}>AlphaBot</div>
              <div style={{ fontSize: 10, color: 'var(--text3)' }}>{cleanPair} · {mode === 'pro' ? 'Pro' : 'Friendly'}</div>
            </div>
          </div>
          <div style={{ display: 'flex', gap: 6 }}>
            <button onClick={() => setShowHistory(!showHistory)} style={chipStyle(showHistory)} title="Chats">💬</button>
            <button onClick={startNewThread} style={chipStyle(false)} title="New chat">+</button>
            <button onClick={toggleMode} style={chipStyle(mode === 'pro')}>{mode === 'pro' ? 'PRO' : 'SIM'}</button>
            <button onClick={clearChat} style={chipStyle(false)} title="Clear all">🗑</button>
            <button onClick={() => setIsOpen(false)} style={chipStyle(false)}>✕</button>
          </div>
        </div>

        <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
          {showHistory && (
            <div style={{ width: 260, borderRight: '1px solid rgba(0,229,255,0.06)', overflowY: 'auto', background: 'var(--bg1)', padding: 12 }}>
              <div style={{ fontSize: 10, color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 10, fontWeight: 600 }}>Conversations</div>
              {threads.length === 0 ? (
                <div style={{ fontSize: 11, color: 'var(--text3)', textAlign: 'center', marginTop: 20 }}>No conversations yet</div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                  {threads.map(t => (
                    <div key={t.id} style={{ padding: '10px 12px', borderRadius: 8, transition: 'all 0.15s ease',
                      background: t.id === activeThreadId ? 'rgba(0,229,255,0.08)' : 'var(--bg3)',
                      border: t.id === activeThreadId ? '1px solid rgba(0,229,255,0.25)' : '1px solid var(--border)',
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                        <div onClick={() => { switchThread(t.id); setShowHistory(false); }} style={{ flex: 1, cursor: 'pointer' }}>
                          <div style={{ fontSize: 10, color: 'var(--text3)', marginBottom: 2 }}>{t.pair} · {new Date(t.updatedAt).toLocaleDateString()}</div>
                          <div style={{ fontSize: 12, color: 'var(--text)', lineHeight: 1.3 }}>{t.title}</div>
                        </div>
                        <button onClick={(e) => { e.stopPropagation(); deleteThread(t.id); }} style={{ background: 'none', border: 'none', color: 'var(--text3)', cursor: 'pointer', fontSize: 12, padding: '2px 4px' }}>✕</button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          <div style={{ flex: 1, overflowY: 'auto', padding: 16, display: 'flex', flexDirection: 'column', gap: 10, background: 'transparent' }}>
            {messages.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '40px 20px' }}>
                <div style={{ fontSize: 40, marginBottom: 12 }}>🤖</div>
                <div style={{ color: 'var(--text)', fontSize: 13, lineHeight: 1.7, marginBottom: 20 }}>Hey! 👋 Ask me anything about the signals, market context, or news impact!</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, justifyContent: 'center' }}>
                  {FRIENDLY_EXAMPLES.map((q, i) => <button key={i} onClick={() => handleSend(q)} disabled={isLoading} style={exampleBtnStyle}>{q}</button>)}
                </div>
              </div>
            ) : (
              <>
                {messages.map((msg, idx) => (
                  <MessageBubble key={idx} message={msg} isStreaming={isLoading && idx === messages.length - 1 && msg.role === 'assistant'} />
                ))}
                {isLoading && messages[messages.length - 1]?.role !== 'assistant' && <TypingIndicator />}
              </>
            )}
            {error && <div style={errorStyle}>⚠️ {error}</div>}
            <div ref={messagesEndRef} />
          </div>
        </div>

        <div style={{ padding: 12, borderTop: '1px solid rgba(0,229,255,0.08)', display: 'flex', gap: 8, background: 'rgba(14,22,41,0.9)', borderRadius: '0 0 16px 16px' }}>
          <input ref={inputRef} value={input} onChange={e => setInput(e.target.value)} onKeyDown={handleKeyDown}
            placeholder={`Ask about ${cleanPair}...`} disabled={isLoading}
            style={{ flex: 1, background: 'rgba(10,20,38,0.8)', border: '1px solid rgba(0,229,255,0.1)', borderRadius: 10, padding: '10px 14px', color: 'var(--text)', fontSize: 13, outline: 'none' }} />
          <button onClick={() => handleSend()} disabled={!input.trim() || isLoading}
            style={{ background: input.trim() && !isLoading ? 'linear-gradient(135deg, #00e5ff, #00bfa5)' : 'var(--bg3)', border: 'none', color: input.trim() && !isLoading ? '#000' : 'var(--text3)', padding: '10px 16px', borderRadius: 10, fontSize: 14, fontWeight: 600, cursor: input.trim() && !isLoading ? 'pointer' : 'not-allowed' }}>
            ➤
          </button>
        </div>
      </div>
      <style>{`@keyframes slideUp{from{opacity:0;transform:translateY(24px) scale(0.96)}to{opacity:1;transform:translateY(0) scale(1)}}`}</style>
    </>
  );
}

function MessageBubble({ message, isStreaming }: { message: { role: string; content: string }; isStreaming?: boolean }) {
  const isUser = message.role === 'user';
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: isUser ? 'flex-end' : 'flex-start' }}>
      <div style={{ fontSize: 9, color: 'var(--text3)', marginBottom: 2 }}>{isUser ? 'You' : '🤖 AlphaBot'}</div>
      <div style={{
        background: isUser ? 'rgba(0,229,255,0.08)' : 'rgba(14,22,41,0.9)',
        border: `1px solid ${isUser ? 'rgba(0,229,255,0.2)' : 'rgba(0,229,255,0.06)'}`,
        color: 'var(--text)', padding: '10px 14px', borderRadius: isUser ? '14px 14px 4px 14px' : '14px 14px 14px 4px',
        maxWidth: '85%', fontSize: 12.5, lineHeight: 1.65, whiteSpace: 'pre-wrap', wordBreak: 'break-word',
      }}>
        {message.content.split(/(\*\*[^*]+\*\*)/g).map((part, i) => part.startsWith('**') ? <strong key={i} style={{ color: '#00e5ff' }}>{part.slice(2, -2)}</strong> : <span key={i}>{part}</span>)}
        {isStreaming && <span style={{ animation: 'blink 1s step-end infinite', color: '#00e5ff' }}>▌</span>}
      </div>
      <style>{`@keyframes blink{50%{opacity:0}}`}</style>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '12px 16px', background: 'rgba(14,22,41,0.9)', border: '1px solid rgba(0,229,255,0.06)', borderRadius: '14px 14px 14px 4px', width: 'fit-content' }}>
      <span style={{ fontSize: 12, color: 'var(--text3)' }}>AlphaBot is thinking</span>
      {[0, 1, 2].map(i => <div key={i} style={{ width: 5, height: 5, borderRadius: '50%', background: '#00e5ff', animation: 'bounce 1.4s ease-in-out infinite', animationDelay: `${i * 0.2}s` }} />)}
    </div>
  );
}

const chipStyle = (active: boolean): React.CSSProperties => ({
  background: active ? 'rgba(0,229,255,0.12)' : 'var(--bg3)',
  border: `1px solid ${active ? 'rgba(0,229,255,0.3)' : 'var(--border)'}`,
  color: active ? '#00e5ff' : 'var(--text3)', padding: '4px 8px', borderRadius: 6, fontSize: 10, fontWeight: 600, cursor: 'pointer',
});

const exampleBtnStyle: React.CSSProperties = {
  background: 'var(--bg3)', border: '1px solid var(--border)', color: 'var(--text2)',
  padding: '8px 14px', borderRadius: 20, fontSize: 12, cursor: 'pointer',
};

const errorStyle: React.CSSProperties = {
  background: 'rgba(255,23,68,0.1)', border: '1px solid rgba(255,23,68,0.2)',
  color: 'var(--sell)', padding: 10, borderRadius: 8, fontSize: 12,
};
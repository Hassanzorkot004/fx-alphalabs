import { useState, useRef, useEffect } from 'react';
import { useAlphaBot } from '../hooks/useAlphaBot';
import type { Signal } from '../Types';
import ChartRenderer from './charts/ChartRenderer';

interface AlphaBotPanelProps {
  pair: string;
  signal: Signal | null;
  onSendMessage?: (fn: (message: string) => Promise<void>) => void;
  onClose?: () => void;
}

export default function AlphaBotPanel({ pair, signal: _signal, onSendMessage, onClose }: AlphaBotPanelProps) {
  const {
    conversations,
    activeId,
    activeConversation,
    messages,
    isLoading,
    error,
    mode,
    sendMessage,
    newConversation,
    selectConversation,
    deleteConversation,
    toggleMode,
    clearChat,
  } = useAlphaBot(pair, _signal);

  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Expose sendMessage to parent (for news/calendar click-to-ask)
  useEffect(() => {
    if (onSendMessage) onSendMessage(sendMessage);
  }, [sendMessage, onSendMessage]);

  // Auto-scroll on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = () => {
    if (input.trim() && !isLoading) {
      sendMessage(input);
      setInput('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const quickQuestions = [
    'Why this direction?',
    "Explain like I'm new to forex",
    "What's the biggest risk?",
    'Show me trade levels',
  ];

  // The active pair is always the current dashboard pair — passed per-message
  const activePair = pair;

  return (
    <div
      style={{
        position: 'fixed',
        bottom: 24,
        right: 24,
        width: 720,
        height: 540,
        background: 'var(--bg2)',
        border: '1px solid var(--border2)',
        borderRadius: 12,
        display: 'flex',
        flexDirection: 'column',
        zIndex: 200,
        boxShadow: '0 20px 60px rgba(0,0,0,0.65)',
        overflow: 'hidden',
        animation: 'slide-up 0.2s ease',
      }}
      onClick={e => e.stopPropagation()}
    >
      {/* ── Header ─────────────────────────────────────────────── */}
      <div style={{
        padding: '10px 14px',
        borderBottom: '1px solid var(--border)',
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        flexShrink: 0,
        background: 'var(--bg3)',
      }}>
        {/* Avatar */}
        <div style={{
          width: 28,
          height: 28,
          borderRadius: '50%',
          background: 'linear-gradient(135deg, var(--cyan), var(--cyan2))',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
          fontSize: 13,
        }}>
          🤖
        </div>

        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="mono" style={{ fontSize: 13, fontWeight: 700, color: 'var(--text)', lineHeight: 1.2 }}>
            AlphaBot
          </div>
          <div className="mono" style={{ fontSize: 10, color: 'var(--text3)' }}>
            {activePair} · {mode === 'simple' ? 'Friendly' : 'Pro'}
          </div>
        </div>

        {/* Mode toggle */}
        <button
          onClick={toggleMode}
          title={`Switch to ${mode === 'simple' ? 'Pro' : 'Simple'} mode`}
          style={{
            background: mode === 'pro' ? 'var(--cyan)' : 'var(--bg4)',
            border: `1px solid ${mode === 'pro' ? 'var(--cyan)' : 'var(--border)'}`,
            color: mode === 'pro' ? '#0d1117' : 'var(--text3)',
            padding: '3px 10px',
            borderRadius: 4,
            fontSize: 10,
            fontWeight: 700,
            cursor: 'pointer',
            letterSpacing: '0.05em',
            transition: 'all 0.15s ease',
          }}
        >
          {mode === 'pro' ? 'PRO' : 'SIMPLE'}
        </button>

        {/* New chat */}
        <button
          onClick={() => newConversation()}
          title="New conversation"
          style={{
            background: 'transparent',
            border: '1px solid var(--border)',
            color: 'var(--text3)',
            padding: '3px 8px',
            borderRadius: 4,
            fontSize: 11,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: 4,
            transition: 'all 0.15s ease',
          }}
          onMouseEnter={e => {
            (e.currentTarget as HTMLElement).style.borderColor = 'var(--cyan)';
            (e.currentTarget as HTMLElement).style.color = 'var(--cyan)';
          }}
          onMouseLeave={e => {
            (e.currentTarget as HTMLElement).style.borderColor = 'var(--border)';
            (e.currentTarget as HTMLElement).style.color = 'var(--text3)';
          }}
        >
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
            <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          New
        </button>

        {/* Clear current */}
        {activeId && messages.length > 0 && (
          <button
            onClick={clearChat}
            title="Clear this conversation"
            style={{
              background: 'transparent',
              border: '1px solid var(--border)',
              color: 'var(--text3)',
              padding: '3px 8px',
              borderRadius: 4,
              fontSize: 10,
              cursor: 'pointer',
            }}
          >
            CLR
          </button>
        )}

        {/* Close */}
        <button
          onClick={onClose}
          style={{
            background: 'transparent',
            border: 'none',
            color: 'var(--text3)',
            fontSize: 16,
            cursor: 'pointer',
            lineHeight: 1,
            padding: '2px 4px',
            borderRadius: 4,
          }}
          onMouseEnter={e => (e.currentTarget.style.color = 'var(--text)')}
          onMouseLeave={e => (e.currentTarget.style.color = 'var(--text3)')}
        >
          ✕
        </button>
      </div>

      {/* ── Body ───────────────────────────────────────────────── */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>

        {/* ── Sidebar: conversation list ──────────────────────── */}
        <div style={{
          width: 210,
          borderRight: '1px solid var(--border)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          flexShrink: 0,
          background: 'var(--bg1)',
        }}>
          {/* Sidebar header */}
          <div style={{
            padding: '10px 12px 8px',
            borderBottom: '1px solid var(--border)',
            flexShrink: 0,
          }}>
            <span className="mono" style={{ fontSize: 9, color: 'var(--text3)', letterSpacing: '0.1em', textTransform: 'uppercase' }}>
              Conversations
            </span>
          </div>

          {/* List */}
          <div style={{ flex: 1, overflowY: 'auto' }}>
            {conversations.length === 0 ? (
              <div style={{ padding: '20px 12px', fontSize: 11, color: 'var(--text3)', textAlign: 'center', lineHeight: 1.5 }}>
                No conversations yet.{'\n'}Click "New" to start one.
              </div>
            ) : (
              conversations.map(conv => (
                <ConversationItem
                  key={conv.id}
                  conv={conv}
                  isActive={conv.id === activeId}
                  onSelect={() => selectConversation(conv.id)}
                  onDelete={() => deleteConversation(conv.id)}
                />
              ))
            )}
          </div>
        </div>

        {/* ── Chat area ──────────────────────────────────────── */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>

          {/* Messages */}
          <div style={{
            flex: 1,
            overflowY: 'auto',
            padding: '16px',
            display: 'flex',
            flexDirection: 'column',
            gap: 10,
          }}>
            {/* Empty state — no active conversation */}
            {!activeId && (
              <EmptyState
                pair={pair}
                quickQuestions={quickQuestions}
                onQuestion={q => { sendMessage(q); }}
                onNew={() => newConversation()}
              />
            )}

            {/* Active conversation — no messages yet */}
            {activeId && messages.length === 0 && (
              <EmptyState
                pair={activePair}
                quickQuestions={quickQuestions}
                onQuestion={q => sendMessage(q)}
                onNew={() => newConversation()}
              />
            )}

            {/* Messages */}
            {messages.map((msg, idx) => (
              <MessageBubble key={idx} message={msg} pair={activePair} />
            ))}

            {/* Thinking indicator */}
            {isLoading && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--text3)', fontSize: 12, paddingLeft: 2 }}>
                <span>AlphaBot is thinking</span>
                {[0, 1, 2].map(i => (
                  <span key={i} style={{
                    width: 5,
                    height: 5,
                    borderRadius: '50%',
                    background: 'var(--text3)',
                    display: 'inline-block',
                    animation: 'thinking-dot 1.4s ease-in-out infinite',
                    animationDelay: `${i * 0.2}s`,
                  }} />
                ))}
              </div>
            )}

            {/* Error */}
            {error && (
              <div style={{
                background: 'rgba(255,71,87,0.1)',
                border: '1px solid rgba(255,71,87,0.3)',
                color: 'var(--red)',
                padding: '8px 12px',
                borderRadius: 6,
                fontSize: 12,
              }}>
                {error}
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div style={{
            padding: '10px 12px',
            borderTop: '1px solid var(--border)',
            display: 'flex',
            gap: 8,
            flexShrink: 0,
          }}>
            <input
              type="text"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={`Ask about ${activePair}…`}
              disabled={isLoading}
              style={{
                flex: 1,
                background: 'var(--bg3)',
                border: '1px solid var(--border)',
                borderRadius: 6,
                padding: '8px 12px',
                color: 'var(--text)',
                fontSize: 12,
                outline: 'none',
                transition: 'border-color 0.15s ease',
              }}
              onFocus={e => (e.target.style.borderColor = 'var(--cyan)')}
              onBlur={e => (e.target.style.borderColor = 'var(--border)')}
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || isLoading}
              style={{
                background: input.trim() && !isLoading ? 'var(--cyan)' : 'var(--bg4)',
                border: 'none',
                color: input.trim() && !isLoading ? '#0d1117' : 'var(--text3)',
                width: 36,
                height: 36,
                borderRadius: 6,
                cursor: input.trim() && !isLoading ? 'pointer' : 'not-allowed',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                transition: 'all 0.15s ease',
                flexShrink: 0,
              }}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ── Conversation sidebar item ─────────────────────────────────── */
function ConversationItem({
  conv, isActive, onSelect, onDelete,
}: {
  conv: import('../hooks/useAlphaBot').Conversation;
  isActive: boolean;
  onSelect: () => void;
  onDelete: () => void;
}) {
  const [hovered, setHovered] = useState(false);

  const date = new Date(conv.updatedAt);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  const timeLabel =
    diffMins < 1   ? 'just now' :
    diffMins < 60  ? `${diffMins}m ago` :
    diffHours < 24 ? `${diffHours}h ago` :
    diffDays < 7   ? `${diffDays}d ago` :
    date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

  return (
    <div
      onClick={onSelect}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        padding: '9px 12px',
        cursor: 'pointer',
        borderLeft: `2px solid ${isActive ? 'var(--cyan)' : 'transparent'}`,
        background: isActive ? 'var(--bg3)' : hovered ? 'rgba(255,255,255,0.03)' : 'transparent',
        transition: 'background 0.1s ease',
        position: 'relative',
        borderBottom: '1px solid var(--border)',
      }}
    >
      {/* Time */}
      <div style={{ fontSize: 9, color: 'var(--text3)', marginBottom: 3, fontFamily: 'var(--font-mono)' }}>
        {timeLabel}
      </div>

      {/* Title */}
      <div style={{
        fontSize: 11,
        color: isActive ? 'var(--text)' : 'var(--text2)',
        lineHeight: 1.4,
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
        paddingRight: hovered ? 20 : 0,
        transition: 'padding-right 0.1s ease',
      }}>
        {conv.title}
      </div>

      {/* Delete button — appears on hover */}
      {hovered && (
        <button
          onClick={e => { e.stopPropagation(); onDelete(); }}
          title="Delete conversation"
          style={{
            position: 'absolute',
            right: 8,
            top: '50%',
            transform: 'translateY(-50%)',
            background: 'transparent',
            border: 'none',
            color: 'var(--text3)',
            cursor: 'pointer',
            fontSize: 13,
            lineHeight: 1,
            padding: '2px 3px',
            borderRadius: 3,
          }}
          onMouseEnter={e => (e.currentTarget.style.color = 'var(--red)')}
          onMouseLeave={e => (e.currentTarget.style.color = 'var(--text3)')}
        >
          ✕
        </button>
      )}
    </div>
  );
}

/* ── Empty / welcome state ─────────────────────────────────────── */
function EmptyState({
  pair, quickQuestions, onQuestion,
}: {
  pair: string;
  quickQuestions: string[];
  onQuestion: (q: string) => void;
  onNew: () => void;
}) {
  return (
    <div style={{ textAlign: 'center', marginTop: 24, padding: '0 16px' }}>
      <div style={{ fontSize: 38, marginBottom: 10 }}>🤖</div>
      <div style={{ fontSize: 13, color: 'var(--text2)', marginBottom: 4 }}>
        Hey! 👋 Ask me anything about the signals, market context, or news impact!
      </div>
      <div style={{ fontSize: 11, color: 'var(--text3)', marginBottom: 18 }}>
        Currently focused on <span className="mono" style={{ color: 'var(--cyan)' }}>{pair}</span>
      </div>
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', justifyContent: 'center' }}>
        {quickQuestions.map(q => (
          <button
            key={q}
            onClick={() => onQuestion(q)}
            style={{
              background: 'var(--bg3)',
              border: '1px solid var(--border2)',
              color: 'var(--text2)',
              padding: '6px 12px',
              borderRadius: 6,
              fontSize: 11,
              cursor: 'pointer',
              transition: 'all 0.15s ease',
            }}
            onMouseEnter={e => {
              (e.currentTarget as HTMLElement).style.borderColor = 'var(--cyan)';
              (e.currentTarget as HTMLElement).style.color = 'var(--cyan)';
            }}
            onMouseLeave={e => {
              (e.currentTarget as HTMLElement).style.borderColor = 'var(--border2)';
              (e.currentTarget as HTMLElement).style.color = 'var(--text2)';
            }}
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}

/* ── Message bubble ────────────────────────────────────────────── */
function MessageBubble({ message, pair }: { message: { role: string; content: string }; pair: string }) {
  const isUser = message.role === 'user';

  const chartRegex = /\[CHART:([^\]]+)\]/g;
  const charts: string[] = [];
  let textContent = message.content;
  let match;
  while ((match = chartRegex.exec(message.content)) !== null) {
    charts.push(match[0]);
    textContent = textContent.replace(match[0], '').trim();
  }

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: isUser ? 'flex-end' : 'flex-start',
    }}>
      {textContent && (
        <div style={{
          background: isUser ? 'rgba(0,212,255,0.12)' : 'var(--bg3)',
          border: `1px solid ${isUser ? 'rgba(0,212,255,0.25)' : 'var(--border)'}`,
          color: 'var(--text)',
          padding: '9px 13px',
          borderRadius: isUser ? '10px 10px 2px 10px' : '10px 10px 10px 2px',
          maxWidth: '84%',
          fontSize: 12,
          lineHeight: 1.65,
          whiteSpace: 'pre-wrap',
        }}>
          {textContent}
        </div>
      )}
      {!isUser && charts.length > 0 && (
        <div style={{ width: '100%', maxWidth: '84%' }}>
          {charts.map((cmd, idx) => (
            <ChartRenderer key={idx} chartCommand={cmd} pair={pair} />
          ))}
        </div>
      )}
    </div>
  );
}

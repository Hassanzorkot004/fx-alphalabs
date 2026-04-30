import { useState, useRef, useEffect } from 'react';
import { useAlphaBot } from '../hooks/useAlphaBot';

interface AlphaBotPanelProps {
  pair: string;
}

export default function AlphaBotPanel({ pair }: AlphaBotPanelProps) {
  const { messages, isLoading, error, mode, sendMessage, toggleMode, clearChat } = useAlphaBot(pair);
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

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

  const commandChips = [
    '/explain',
    '/agents',
    '/risk',
    '/levels',
  ];

  return (
    <div style={{
      background: 'var(--bg2)',
      border: '1px solid var(--border)',
      borderRadius: 8,
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      minHeight: 500,
    }}>
      {/* Header */}
      <div style={{
        padding: '12px 16px',
        borderBottom: '1px solid var(--border)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div className="mono" style={{ fontSize: 13, fontWeight: 600, color: 'var(--amber)' }}>
            AlphaBot
          </div>
          <div className="mono" style={{ fontSize: 11, color: 'var(--text3)' }}>
            {pair}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            onClick={toggleMode}
            style={{
              background: mode === 'pro' ? 'var(--amber)20' : 'var(--bg3)',
              border: `1px solid ${mode === 'pro' ? 'var(--amber)' : 'var(--border)'}`,
              color: mode === 'pro' ? 'var(--amber)' : 'var(--text3)',
              padding: '4px 10px',
              borderRadius: 4,
              fontSize: 10,
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.2s ease',
            }}
          >
            {mode.toUpperCase()}
          </button>
          <button
            onClick={clearChat}
            style={{
              background: 'var(--bg3)',
              border: '1px solid var(--border)',
              color: 'var(--text3)',
              padding: '4px 10px',
              borderRadius: 4,
              fontSize: 10,
              cursor: 'pointer',
            }}
          >
            Clear
          </button>
        </div>
      </div>

      {/* Messages */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: 16,
        display: 'flex',
        flexDirection: 'column',
        gap: 12,
      }}>
        {messages.length === 0 && (
          <div style={{ 
            textAlign: 'center', 
            color: 'var(--text3)', 
            fontSize: 13,
            marginTop: 40,
          }}>
            <div style={{ fontSize: 32, marginBottom: 12 }}>💬</div>
            <div>Ask me about the {pair} signal</div>
            <div style={{ fontSize: 11, marginTop: 8 }}>
              Try: "Why is this a {mode === 'simple' ? 'buy' : 'BUY'} signal?"
            </div>
          </div>
        )}

        {messages.map((msg, idx) => (
          <MessageBubble key={idx} message={msg} />
        ))}

        {isLoading && <TypingIndicator />}
        {error && (
          <div style={{
            background: 'var(--red)20',
            border: '1px solid var(--red)40',
            color: 'var(--red)',
            padding: 12,
            borderRadius: 6,
            fontSize: 12,
          }}>
            {error}
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Command chips */}
      {messages.length === 0 && (
        <div style={{ padding: '0 16px 12px', display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {commandChips.map(cmd => (
            <button
              key={cmd}
              onClick={() => setInput(cmd + ' ')}
              style={{
                background: 'var(--bg3)',
                border: '1px solid var(--border)',
                color: 'var(--text2)',
                padding: '6px 12px',
                borderRadius: 12,
                fontSize: 11,
                cursor: 'pointer',
                transition: 'all 0.2s ease',
              }}
              className="hover:border-amber"
            >
              {cmd}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div style={{
        padding: 12,
        borderTop: '1px solid var(--border)',
        display: 'flex',
        gap: 8,
      }}>
        <div style={{
          flex: 1,
          display: 'flex',
          alignItems: 'center',
          background: 'var(--bg3)',
          border: '1px solid var(--border)',
          borderRadius: 6,
          padding: '8px 12px',
          transition: 'border-color 0.2s ease',
        }}
        className="focus-within:border-amber"
        >
          <span className="mono" style={{ color: 'var(--amber)', marginRight: 8 }}>▸</span>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about this signal..."
            disabled={isLoading}
            style={{
              flex: 1,
              background: 'transparent',
              border: 'none',
              outline: 'none',
              color: 'var(--text)',
              fontSize: 13,
            }}
          />
        </div>
        <button
          onClick={handleSend}
          disabled={!input.trim() || isLoading}
          style={{
            background: input.trim() && !isLoading ? 'var(--amber)' : 'var(--bg3)',
            border: 'none',
            color: input.trim() && !isLoading ? 'var(--bg)' : 'var(--text3)',
            padding: '8px 16px',
            borderRadius: 6,
            fontSize: 13,
            fontWeight: 600,
            cursor: input.trim() && !isLoading ? 'pointer' : 'not-allowed',
            transition: 'all 0.2s ease',
          }}
        >
          Send
        </button>
      </div>
    </div>
  );
}

function MessageBubble({ message }: { message: { role: string; content: string } }) {
  const isUser = message.role === 'user';

  return (
    <div style={{
      display: 'flex',
      justifyContent: isUser ? 'flex-end' : 'flex-start',
    }}>
      <div style={{
        background: isUser ? 'var(--amber)20' : 'var(--bg3)',
        border: `1px solid ${isUser ? 'var(--amber)40' : 'var(--border)'}`,
        color: 'var(--text)',
        padding: '10px 14px',
        borderRadius: 8,
        maxWidth: '80%',
        fontSize: 13,
        lineHeight: 1.5,
        whiteSpace: 'pre-wrap',
      }}>
        {message.content}
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div style={{
      display: 'flex',
      gap: 4,
      padding: '10px 14px',
      background: 'var(--bg3)',
      border: '1px solid var(--border)',
      borderRadius: 8,
      width: 'fit-content',
    }}>
      {[0, 1, 2].map(i => (
        <div
          key={i}
          style={{
            width: 6,
            height: 6,
            borderRadius: '50%',
            background: 'var(--text3)',
            animation: 'pulse-dot 1.4s ease-in-out infinite',
            animationDelay: `${i * 0.2}s`,
          }}
        />
      ))}
    </div>
  );
}

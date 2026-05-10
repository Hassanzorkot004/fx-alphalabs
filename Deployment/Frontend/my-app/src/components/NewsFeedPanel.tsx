import { useState } from 'react';
import type { NewsArticle } from '../Types';

export default function NewsFeedPanel({ articles, selectedPair, onArticleClick }: {
  articles: NewsArticle[]; selectedPair?: string; onArticleClick?: (a: NewsArticle) => void;
}) {
  const [collapsed, setCollapsed] = useState(false);
  const filtered = selectedPair
        ? articles.filter(a => { const c: string[] = (selectedPair.replace('=X', '').match(/.{3}/g) || []); return a.tags.some((t: string) => c.includes(t)); })
    : articles;

  return (
    <div style={{
      padding: 14, maxHeight: collapsed ? 40 : 320, overflow: 'hidden', transition: 'max-height 0.3s ease',
      background: 'var(--bg2)', border: '1px solid var(--border)', borderRadius: 12,
      backdropFilter: 'blur(16px)',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: collapsed ? 0 : 10, cursor: 'pointer' }} onClick={() => setCollapsed(!collapsed)}>
        <span className="mono" style={{ fontSize: 10, fontWeight: 600, color: '#80deea', letterSpacing: '1px' }}>NEWS WIRE</span>
        <span style={{ fontSize: 10, color: 'var(--text3)' }}>{filtered.length} articles {collapsed ? '▸' : '▾'}</span>
      </div>
      {!collapsed && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6, overflowY: 'auto', maxHeight: 260 }}>
          {filtered.slice(0, 8).map((a, i) => (
            <div key={i} onClick={() => onArticleClick?.(a)}
              style={{ padding: '8px 10px', background: 'rgba(10,20,38,0.8)', border: '1px solid rgba(0,229,255,0.06)', borderRadius: 6, cursor: 'pointer', transition: 'all 0.15s ease' }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = '#80deea'; e.currentTarget.style.background = 'rgba(0,229,255,0.04)'; }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(0,229,255,0.06)'; e.currentTarget.style.background = 'rgba(10,20,38,0.8)'; }}>
              <div style={{ display: 'flex', gap: 4, marginBottom: 3, flexWrap: 'wrap' }}>
                {a.tags.slice(0, 2).map(t => <span key={t} className="badge" style={{ background: 'rgba(128,222,234,0.12)', color: '#80deea', fontSize: 7 }}>{t}</span>)}
                <span className="mono" style={{ fontSize: 8, color: 'var(--text3)', marginLeft: 'auto' }}>{a.age_label}</span>
              </div>
              <div style={{ fontSize: 11, color: 'var(--text)', lineHeight: 1.4 }}>{a.title}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
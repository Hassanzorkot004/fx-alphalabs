import type { NewsArticle } from '../Types';

interface NewsFeedPanelProps {
  articles: NewsArticle[];
  selectedPair?: string;
  onArticleClick?: (article: NewsArticle) => void;
}

export default function NewsFeedPanel({ articles, selectedPair, onArticleClick }: NewsFeedPanelProps) {
  const filteredArticles = selectedPair
    ? articles.filter(article => {
        const pairCurrencies: string[] = selectedPair.replace('=X', '').match(/.{3}/g) || [];
        return article.tags.some(tag => pairCurrencies.includes(tag));
      })
    : articles;

  const recentArticles = filteredArticles.slice(0, 10);

  return (
    <div style={{
      background: 'var(--bg2)',
      border: '1px solid var(--border)',
      borderRadius: 8,
      overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        padding: '10px 16px',
        borderBottom: '1px solid var(--border)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        background: 'var(--bg3)',
      }}>
        <span className="mono" style={{ fontSize: 10, fontWeight: 700, color: 'var(--text3)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
          News Wire
        </span>
        <span className="mono" style={{ fontSize: 10, color: 'var(--text3)' }}>
          {recentArticles.length} article{recentArticles.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Articles */}
      <div style={{ maxHeight: 320, overflowY: 'auto' }}>
        {recentArticles.length === 0 ? (
          <div style={{ padding: '20px 16px', color: 'var(--text3)', fontSize: 12, textAlign: 'center' }}>
            No recent articles
          </div>
        ) : (
          recentArticles.map((article, idx) => (
            <ArticleItem
              key={idx}
              article={article}
              onClick={onArticleClick}
              isLast={idx === recentArticles.length - 1}
            />
          ))
        )}
      </div>
    </div>
  );
}

function ArticleItem({
  article,
  onClick,
  isLast,
}: {
  article: NewsArticle;
  onClick?: (article: NewsArticle) => void;
  isLast: boolean;
}) {
  return (
    <div
      onClick={() => onClick?.(article)}
      title="Click to ask AlphaBot about this"
      style={{
        padding: '10px 16px',
        borderBottom: isLast ? 'none' : '1px solid var(--border)',
        cursor: 'pointer',
        transition: 'background 0.12s ease',
        display: 'flex',
        gap: 12,
        alignItems: 'flex-start',
      }}
      onMouseEnter={e => (e.currentTarget as HTMLElement).style.background = 'var(--bg3)'}
      onMouseLeave={e => (e.currentTarget as HTMLElement).style.background = 'transparent'}
    >
      {/* Tags */}
      <div style={{ display: 'flex', gap: 4, flexShrink: 0, paddingTop: 2 }}>
        {article.tags.slice(0, 2).map(tag => (
          <span key={tag} className="mono" style={{
            fontSize: 9,
            color: 'var(--cyan)',
            background: 'rgba(0,212,255,0.1)',
            border: '1px solid rgba(0,212,255,0.2)',
            padding: '2px 5px',
            borderRadius: 3,
            fontWeight: 600,
          }}>
            {tag}
          </span>
        ))}
      </div>

      {/* Title */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 12, color: 'var(--text)', lineHeight: 1.45 }}>
          {article.title}
        </div>
      </div>

      {/* Age */}
      <span className="mono" style={{ fontSize: 10, color: 'var(--text3)', flexShrink: 0, paddingTop: 2 }}>
        {article.age_label}
      </span>
    </div>
  );
}

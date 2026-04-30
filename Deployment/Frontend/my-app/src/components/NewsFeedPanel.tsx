import type { NewsArticle } from '../Types';

interface NewsFeedPanelProps {
  articles: NewsArticle[];
}

export default function NewsFeedPanel({ articles }: NewsFeedPanelProps) {
  const recentArticles = articles.slice(0, 10);

  return (
    <div style={{
      background: 'var(--bg2)',
      border: '1px solid var(--border)',
      borderRadius: 8,
      padding: 16,
      maxHeight: 400,
      overflowY: 'auto',
    }}>
      <div className="mono" style={{ fontSize: 12, fontWeight: 600, color: 'var(--text3)', marginBottom: 12 }}>
        NEWS FEED
      </div>

      {recentArticles.length === 0 ? (
        <div style={{ color: 'var(--text3)', fontSize: 12 }}>
          No recent articles
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {recentArticles.map((article, idx) => (
            <ArticleItem key={idx} article={article} />
          ))}
        </div>
      )}
    </div>
  );
}

function ArticleItem({ article }: { article: NewsArticle }) {
  return (
    <div style={{
      padding: 10,
      background: 'var(--bg3)',
      border: '1px solid var(--border)',
      borderRadius: 6,
      cursor: 'pointer',
      transition: 'border-color 0.2s ease',
    }}
    className="hover:border-border2"
    >
      <div style={{ display: 'flex', gap: 6, marginBottom: 6, flexWrap: 'wrap' }}>
        {article.tags.map(tag => (
          <span
            key={tag}
            className="mono"
            style={{
              fontSize: 9,
              color: 'var(--amber)',
              background: 'var(--amber)20',
              padding: '2px 6px',
              borderRadius: 3,
              fontWeight: 600,
            }}
          >
            {tag}
          </span>
        ))}
        <span className="mono" style={{ fontSize: 9, color: 'var(--text3)', marginLeft: 'auto' }}>
          {article.age_label}
        </span>
      </div>
      <div style={{ fontSize: 12, color: 'var(--text)', lineHeight: 1.4 }}>
        {article.title}
      </div>
    </div>
  );
}

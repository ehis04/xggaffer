import React from 'react';
import type { ArticleListItem } from '../../types/articles';
import styles from './ArticleCard.module.css';

interface Props {
  article: ArticleListItem;
  onOpen?: (id: number) => void;
  onLike?: (id: number) => void;
  onDislike?: (id: number) => void;
}

function StarRating({ value }: { value: number }) {
  return (
    <span className={styles.stars} aria-label={`${value.toFixed(1)} stars`}>
      {[1, 2, 3, 4, 5].map((n) => (
        <span key={n} className={n <= Math.round(value) ? styles.starFilled : styles.starEmpty}>
          ★
        </span>
      ))}
    </span>
  );
}

const ArticleCard: React.FC<Props> = ({ article, onOpen, onLike, onDislike }) => {
  const canOpenSource = (() => {
    try {
      const parsed = new URL(article.url);
      // Ignore placeholder/local domains that are commonly used in seed data.
      return ['http:', 'https:'].includes(parsed.protocol) && !parsed.hostname.endsWith('.local');
    } catch {
      return false;
    }
  })();

  const handleOpen = () => {
    if (onOpen) {
      onOpen(article.id);
      return;
    }

    if (canOpenSource) {
      window.open(article.url, '_blank', 'noopener,noreferrer');
    }
  };

  return (
    <article
      className={styles.card}
      onClick={handleOpen}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && handleOpen()}
    >
      {article.image_url && (
        <img
          className={styles.thumbnail}
          src={article.image_url}
          alt=""
          loading="lazy"
        />
      )}
      <div className={styles.body}>
        <div className={styles.meta}>
          {article.site.logo_url && (
            <img className={styles.siteLogo} src={article.site.logo_url} alt={article.site.name} />
          )}
          <span className={styles.siteName}>{article.site.name}</span>
          <span className={styles.dot}>·</span>
          <span className={styles.date}>
            {new Date(article.publication_date).toLocaleDateString(undefined, {
              day: 'numeric', month: 'short', year: 'numeric',
            })}
          </span>
          {article.is_read && <span className={styles.readBadge}>Read</span>}
        </div>

        <h3 className={styles.title}>{article.title}</h3>

        {article.summary && (
          <p className={styles.summary}>{article.summary.slice(0, 180)}{article.summary.length > 180 ? '…' : ''}</p>
        )}

        <div className={styles.topics}>
          {article.topics.map((t) => (
            <span key={t.id} className={styles.topicChip}>{t.name}</span>
          ))}
        </div>

        <div className={styles.footer}>
          <span className={styles.readTime}>{article.read_time_minutes} min read</span>

          {article.total_ratings > 0 && (
            <span className={styles.ratingGroup}>
              <StarRating value={article.average_rating} />
              <span className={styles.ratingCount}>({article.total_ratings})</span>
            </span>
          )}

          <button
            className={`${styles.feedbackBtn} ${article.user_feedback === 'LIKE' ? styles.active : ''}`}
            onClick={(e) => {
              e.stopPropagation();
              onLike?.(article.id);
            }}
            aria-label="Like"
          >
            👍 {article.total_likes > 0 ? article.total_likes : ''}
          </button>
          <button
            className={`${styles.feedbackBtn} ${article.user_feedback === 'DISLIKE' ? styles.active : ''}`}
            onClick={(e) => {
              e.stopPropagation();
              onDislike?.(article.id);
            }}
            aria-label="Dislike"
          >
            👎 {article.total_dislikes > 0 ? article.total_dislikes : ''}
          </button>
          <button
            type="button"
            className={styles.openSourceBtn}
            onClick={(e) => {
              e.stopPropagation();
              if (canOpenSource) {
                window.open(article.url, '_blank', 'noopener,noreferrer');
              }
            }}
            disabled={!canOpenSource}
            title={canOpenSource ? 'Open source article' : 'Source link unavailable'}
          >
            {canOpenSource ? 'Read Source' : 'Source Unavailable'}
          </button>
        </div>
      </div>
    </article>
  );
};

export default ArticleCard;

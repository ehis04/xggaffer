import { useMemo, useState, type CSSProperties } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ProfileCard } from '../../components/BoxSections/ProfileCard';
import { SearchBar } from '../../components/Navigation/SearchBar';
import { Sidebar } from '../../components/Navigation/SideBar';
import { SocialUserButtons } from '../../components/Social/SocialUserButtons';
import articlesApi from '../../services/api/articlesApi';
import '../social/css/SocialPage.css';
import styles from './css/ArticleDetailPage.module.css';

const normalizeForCompare = (value: string): string =>
  value
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .replace(/[.,!?;:\"'()\[\]{}]/g, '')
    .trim();

const extractParagraphs = (value: string): string[] => {
  if (!value) {
    return [];
  }

  const normalized = value
    .replace(/\r\n/g, '\n')
    .replace(/\r/g, '\n')
    .replace(/\n\s*\n+/g, '\n\n')
    .trim();

  if (!normalized) {
    return [];
  }

  return normalized
    .split('\n\n')
    .map((paragraph) => paragraph.trim())
    .filter((paragraph) => paragraph.length > 0);
};

const splitDenseParagraph = (value: string): string[] => {
  const normalized = value.trim();
  if (!normalized) {
    return [];
  }

  const pieces = normalized
    .split(/(?<=[.!?])\s+(?=(?:\[)?[A-Z])/)
    .map((part) => (typeof part === 'string' ? part.trim() : ''))
    .filter((part) => part.length > 0);

  if (pieces.length <= 1) {
    return [normalized];
  }

  return pieces;
};

const ArticleDetailPage = () => {
  const navigate = useNavigate();
  const { articleId } = useParams<{ articleId: string }>();
  const numericId = Number(articleId);
  const [isLowResImage, setIsLowResImage] = useState(false);
  const [heroMaxWidth, setHeroMaxWidth] = useState<number | null>(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['article-detail', numericId],
    queryFn: () => articlesApi.getArticle(numericId),
    enabled: Number.isFinite(numericId) && numericId > 0,
  });

  const sourceIsValid = useMemo(() => {
    if (!data?.url) {
      return false;
    }

    try {
      const parsed = new URL(data.url);
      return ['http:', 'https:'].includes(parsed.protocol) && !parsed.hostname.endsWith('.local');
    } catch {
      return false;
    }
  }, [data?.url]);

  const summaryText = useMemo(() => (data?.summary || '').trim(), [data?.summary]);

  const bodyParagraphs = useMemo(() => {
    const sourceText = (data?.content || '').trim() || summaryText;
    let rawParagraphs = extractParagraphs(sourceText);
    if (rawParagraphs.length === 1) {
      rawParagraphs = splitDenseParagraph(rawParagraphs[0]);
    }

    if (!rawParagraphs.length) {
      return [];
    }

    const seen = new Set<string>();
    const summaryKey = normalizeForCompare(summaryText);

    return rawParagraphs.filter((paragraph) => {
      const key = normalizeForCompare(paragraph);
      if (!key || key === summaryKey || seen.has(key)) {
        return false;
      }
      seen.add(key);
      return true;
    });
  }, [data?.content, summaryText]);

  return (
    <div className="social-page">
      <div className="sidebar-section">
        <Sidebar />
      </div>
      <div className="searchBar-section">
        <SearchBar placeholder="Search articles" />
      </div>
      <div className="right-section">
        <div className="right-header">
          <SocialUserButtons />
        </div>
      </div>
      <div className="trendingBox-section">
        <ProfileCard />
      </div>

      <div className="main-section">
        <div className={styles.detailShell}>
          <button type="button" className={styles.backButton} onClick={() => navigate('/articles')}>
            Back to news feed
          </button>

          {isLoading && <div className={styles.state}>Loading article...</div>}
          {isError && <div className={styles.stateError}>Failed to load article.</div>}

          {data && (
            <article className={styles.detailCard}>
              <header className={styles.header}>
                <h1 className={styles.title}>{data.title}</h1>
                <p className={styles.meta}>
                  {data.site?.name} · {new Date(data.publication_date).toLocaleDateString()}
                </p>
              </header>

              {data.image_url && (
                <img
                  className={`${styles.hero} ${isLowResImage ? styles.heroLowRes : ''}`}
                  src={data.image_url}
                  alt=""
                  loading="eager"
                  style={
                    isLowResImage && heroMaxWidth
                      ? ({ '--hero-max-width': `${heroMaxWidth}px` } as CSSProperties)
                      : undefined
                  }
                  onLoad={(event) => {
                    const img = event.currentTarget;
                    const devicePixelRatio = Math.max(window.devicePixelRatio || 1, 1);
                    const effectiveWidth = Math.floor(img.naturalWidth / devicePixelRatio);
                    const effectiveHeight = Math.floor(img.naturalHeight / devicePixelRatio);
                    const needsConstraint = effectiveWidth < 760 || effectiveHeight < 420;

                    setIsLowResImage(needsConstraint);

                    if (needsConstraint) {
                      setHeroMaxWidth(Math.max(420, Math.min(760, effectiveWidth)));
                    } else {
                      setHeroMaxWidth(null);
                    }
                  }}
                />
              )}

              {summaryText && <p className={styles.summary}>{summaryText}</p>}

              {bodyParagraphs.length > 0 ? (
                <div className={styles.content}>
                  {bodyParagraphs.map((paragraph) => (
                    <p key={paragraph} className={styles.paragraph}>
                      {paragraph}
                    </p>
                  ))}
                </div>
              ) : !summaryText ? (
                <div className={styles.content}>No preview content available for this article yet.</div>
              ) : null}

              <footer className={styles.footer}>
                {sourceIsValid ? (
                  <a
                    href={data.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={styles.sourceLink}
                  >
                    Visit original source
                  </a>
                ) : (
                  <span className={styles.sourceUnavailable}>Original source link unavailable</span>
                )}
              </footer>
            </article>
          )}
        </div>
      </div>
    </div>
  );
};

export default ArticleDetailPage;

import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ProfileCard } from '../../components/BoxSections/ProfileCard';
import { SearchBar } from '../../components/Navigation/SearchBar';
import { Sidebar } from '../../components/Navigation/SideBar';
import { SocialUserButtons } from '../../components/Social/SocialUserButtons';
import articlesApi, { type PaginatedArticles } from '../../services/api/articlesApi';
import ArticleCard from '../../components/articles/ArticleCard';
import type { ArticleAuthor, ArticleListItem, ArticleSite, ArticleTopic } from '../../types/articles';
import '../social/css/SocialPage.css';
import styles from './css/ArticlesPage.module.css';

const FEED_QUERY_KEY = 'articles-feed';
const TOPICS_QUERY_KEY = 'articles-topics';
const SITES_QUERY_KEY = 'articles-sites';
const AUTHORS_QUERY_KEY = 'articles-authors';

const FILTER_PREVIEW_COUNT = 5;

type FilterOption = { id: number; name: string };

function FilterRow({
  label,
  options,
  activeId,
  onSelect,
  expanded,
  onToggleExpand,
}: {
  label: string;
  options: FilterOption[];
  activeId?: number;
  onSelect: (id?: number) => void;
  expanded: boolean;
  onToggleExpand: () => void;
}) {
  const visibleOptions = expanded ? options : options.slice(0, FILTER_PREVIEW_COUNT);
  const hasMore = options.length > FILTER_PREVIEW_COUNT;

  return (
    <div className={styles.filterRow}>
      <span className={styles.filterLabel}>{label}</span>
      <div className={styles.filterPills}>
        <button
          className={`${styles.topicBtn} ${activeId === undefined ? styles.topicBtnActive : ''}`}
          onClick={() => onSelect(undefined)}
        >
          All
        </button>
        {visibleOptions.map((option) => (
          <button
            key={option.id}
            className={`${styles.topicBtn} ${activeId === option.id ? styles.topicBtnActive : ''}`}
            onClick={() => onSelect(option.id)}
            title={option.name}
          >
            {option.name}
          </button>
        ))}
      </div>
      {hasMore && (
        <button className={styles.expandBtn} onClick={onToggleExpand}>
          {expanded ? 'Less' : 'More'}
        </button>
      )}
    </div>
  );
}

const ArticlesPage: React.FC = () => {
  const navigate = useNavigate();
  const qc = useQueryClient();

  const [searchInput, setSearchInput] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [activeTopic, setActiveTopic] = useState<number | undefined>(undefined);
  const [activeSite, setActiveSite] = useState<number | undefined>(undefined);
  const [activeAuthor, setActiveAuthor] = useState<number | undefined>(undefined);

  const [topicsExpanded, setTopicsExpanded] = useState(false);
  const [sitesExpanded, setSitesExpanded] = useState(false);
  const [authorsExpanded, setAuthorsExpanded] = useState(false);

  const [page, setPage] = useState(1);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setSearchQuery(searchInput.trim());
    }, 300);
    return () => window.clearTimeout(timer);
  }, [searchInput]);

  useEffect(() => {
    setPage(1);
  }, [searchQuery, activeTopic, activeSite, activeAuthor]);

  const { data: topicsData } = useQuery<ArticleTopic[]>({
    queryKey: [TOPICS_QUERY_KEY],
    queryFn: () => articlesApi.getTopics(),
    staleTime: 1000 * 60 * 10,
  });

  const { data: sitesData } = useQuery<ArticleSite[]>({
    queryKey: [SITES_QUERY_KEY],
    queryFn: () => articlesApi.getSites(),
    staleTime: 1000 * 60 * 10,
  });

  const { data: authorsData } = useQuery<ArticleAuthor[]>({
    queryKey: [AUTHORS_QUERY_KEY],
    queryFn: () => articlesApi.getAuthors(),
    staleTime: 1000 * 60 * 10,
  });

  const { data: feedData, isLoading, isError } = useQuery<PaginatedArticles>({
    queryKey: [FEED_QUERY_KEY, searchQuery, activeTopic, activeSite, activeAuthor, page],
    queryFn: () =>
      articlesApi.getFeed({
        q: searchQuery || undefined,
        topic: activeTopic,
        site: activeSite,
        author: activeAuthor,
        page,
      }),
    staleTime: 1000 * 60 * 2,
  });

  const feedbackMutation = useMutation({
    mutationFn: ({ articleId, type }: { articleId: number; type: 'LIKE' | 'DISLIKE' }) =>
      articlesApi.submitFeedback({ target_type: 'ARTICLE', target_id: articleId, feedback_type: type, article_id: articleId }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [FEED_QUERY_KEY] });
    },
  });

  const handleLike = (id: number) => feedbackMutation.mutate({ articleId: id, type: 'LIKE' });
  const handleDislike = (id: number) => feedbackMutation.mutate({ articleId: id, type: 'DISLIKE' });

  const totalPages = feedData ? Math.ceil(feedData.count / 20) : 1;

  const topicOptions = useMemo<FilterOption[]>(
    () => (topicsData ?? []).map((topic) => ({ id: topic.id, name: topic.name })),
    [topicsData],
  );

  const siteOptions = useMemo<FilterOption[]>(
    () => (sitesData ?? []).map((site) => ({ id: site.id, name: site.name })),
    [sitesData],
  );

  const authorOptions = useMemo<FilterOption[]>(
    () => (authorsData ?? []).map((author) => ({ id: author.id, name: author.name })),
    [authorsData],
  );

  return (
    <div className="social-page">
      <div className="sidebar-section">
        <Sidebar />
      </div>
      <div className="searchBar-section">
        <SearchBar
          placeholder="Search articles"
          onChange={setSearchInput}
          onSearch={setSearchInput}
        />
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
        <div className={styles.feedShell}>
          <header className={styles.header}>
            <h1 className={styles.heading}>Football News</h1>
            <p className={styles.subheading}>Personalised articles from across the football world</p>
          </header>

          <nav className={styles.topicBar} aria-label="Article filters">
            <FilterRow
              label="Topics"
              options={topicOptions}
              activeId={activeTopic}
              onSelect={setActiveTopic}
              expanded={topicsExpanded}
              onToggleExpand={() => setTopicsExpanded((prev) => !prev)}
            />
            <FilterRow
              label="Sources"
              options={siteOptions}
              activeId={activeSite}
              onSelect={setActiveSite}
              expanded={sitesExpanded}
              onToggleExpand={() => setSitesExpanded((prev) => !prev)}
            />
            <FilterRow
              label="Writers"
              options={authorOptions}
              activeId={activeAuthor}
              onSelect={setActiveAuthor}
              expanded={authorsExpanded}
              onToggleExpand={() => setAuthorsExpanded((prev) => !prev)}
            />
          </nav>

          {isLoading && <div className={styles.state}>Loading articles...</div>}
          {isError && <div className={styles.stateError}>Failed to load articles. Please try again.</div>}

          {feedData && feedData.results.length === 0 && (
            <div className={styles.state}>No articles found. Check back soon.</div>
          )}

          {feedData && (
            <ul className={styles.list}>
              {feedData.results.map((article: ArticleListItem) => (
                <li key={article.id}>
                  <ArticleCard
                    article={article}
                    onOpen={(id) => navigate(`/articles/${id}`)}
                    onLike={handleLike}
                    onDislike={handleDislike}
                  />
                </li>
              ))}
            </ul>
          )}

          {totalPages > 1 && (
            <div className={styles.pagination}>
              <button
                className={styles.pageBtn}
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
              >
                Previous
              </button>
              <span className={styles.pageInfo}>Page {page} of {totalPages}</span>
              <button
                className={styles.pageBtn}
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ArticlesPage;

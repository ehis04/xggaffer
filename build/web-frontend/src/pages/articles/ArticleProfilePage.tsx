import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQuery } from '@tanstack/react-query';
import { ProfileCard } from '../../components/BoxSections/ProfileCard';
import { SearchBar } from '../../components/Navigation/SearchBar';
import { Sidebar } from '../../components/Navigation/SideBar';
import { SocialUserButtons } from '../../components/Social/SocialUserButtons';
import articlesApi from '../../services/api/articlesApi';
import type { ArticleAuthor, ArticleSite, ArticleTopic, UserArticleProfileUpdatePayload } from '../../types/articles';
import '../social/css/SocialPage.css';
import styles from './css/ArticlesPage.module.css';

function SelectionGroup({
  label,
  options,
  selected,
  onToggle,
}: {
  label: string;
  options: Array<{ id: number; name: string }>;
  selected: Set<number>;
  onToggle: (id: number) => void;
}) {
  return (
    <div className={styles.prefGroup}>
      <h3 className={styles.prefGroupTitle}>{label}</h3>
      <div className={styles.filterPills}>
        {options.map((option) => {
          const active = selected.has(option.id);
          return (
            <button
              key={option.id}
              type="button"
              className={`${styles.topicBtn} ${active ? styles.topicBtnActive : ''}`}
              onClick={() => onToggle(option.id)}
            >
              {option.name}
            </button>
          );
        })}
      </div>
    </div>
  );
}

const ArticleProfilePage: React.FC = () => {
  const navigate = useNavigate();

  const { data: profile, refetch, isLoading, isError } = useQuery({
    queryKey: ['articles-profile'],
    queryFn: () => articlesApi.getProfile(),
  });

  const { data: topics = [] } = useQuery<ArticleTopic[]>({
    queryKey: ['articles-topics'],
    queryFn: () => articlesApi.getTopics(),
  });
  const { data: sites = [] } = useQuery<ArticleSite[]>({
    queryKey: ['articles-sites'],
    queryFn: () => articlesApi.getSites(),
  });
  const { data: authors = [] } = useQuery<ArticleAuthor[]>({
    queryKey: ['articles-authors'],
    queryFn: () => articlesApi.getAuthors(),
  });

  const [preferredTopics, setPreferredTopics] = useState<Set<number>>(new Set());
  const [dislikedTopics, setDislikedTopics] = useState<Set<number>>(new Set());
  const [preferredSites, setPreferredSites] = useState<Set<number>>(new Set());
  const [dislikedSites, setDislikedSites] = useState<Set<number>>(new Set());
  const [preferredAuthors, setPreferredAuthors] = useState<Set<number>>(new Set());
  const [dislikedAuthors, setDislikedAuthors] = useState<Set<number>>(new Set());

  const [qualityThreshold, setQualityThreshold] = useState(50);
  const [minReadTime, setMinReadTime] = useState(0);
  const [maxReadTime, setMaxReadTime] = useState(30);

  useEffect(() => {
    if (!profile) return;
    setPreferredTopics(new Set(profile.preferred_topics.map((item) => item.id)));
    setDislikedTopics(new Set(profile.disliked_topics.map((item) => item.id)));
    setPreferredSites(new Set(profile.preferred_sites.map((item) => item.id)));
    setDislikedSites(new Set(profile.disliked_sites.map((item) => item.id)));
    setPreferredAuthors(new Set(profile.preferred_authors.map((item) => item.id)));
    setDislikedAuthors(new Set(profile.disliked_authors.map((item) => item.id)));
    setQualityThreshold(Math.round(profile.preferred_quality_threshold));
    setMinReadTime(profile.min_read_time);
    setMaxReadTime(profile.max_read_time || 30);
  }, [profile]);

  const saveMutation = useMutation({
    mutationFn: (payload: UserArticleProfileUpdatePayload) => articlesApi.updateProfile(payload),
    onSuccess: () => {
      refetch();
    },
  });

  const toggleFromSet = (setter: React.Dispatch<React.SetStateAction<Set<number>>>) => (id: number) => {
    setter((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const saveProfile = () => {
    saveMutation.mutate({
      preferred_topic_ids: Array.from(preferredTopics),
      disliked_topic_ids: Array.from(dislikedTopics),
      preferred_site_ids: Array.from(preferredSites),
      disliked_site_ids: Array.from(dislikedSites),
      preferred_author_ids: Array.from(preferredAuthors),
      disliked_author_ids: Array.from(dislikedAuthors),
      preferred_quality_threshold: qualityThreshold,
      min_read_time: minReadTime,
      max_read_time: maxReadTime,
    });
  };

  const topicOptions = useMemo(() => topics.map((t) => ({ id: t.id, name: t.name })), [topics]);
  const siteOptions = useMemo(() => sites.map((s) => ({ id: s.id, name: s.name })), [sites]);
  const authorOptions = useMemo(() => authors.map((a) => ({ id: a.id, name: a.name })), [authors]);

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
        <div className={styles.feedShell}>
          <header className={styles.header}>
            <h1 className={styles.heading}>Article Profile</h1>
            <p className={styles.subheading}>How your likes/dislikes shape recommendations and what you want to see more of</p>
            <div className={styles.pageTabs}>
              <button type="button" className={styles.tabBtn} onClick={() => navigate('/articles')}>
                Feed
              </button>
              <button type="button" className={styles.tabBtn} onClick={() => navigate('/articles/favourites')}>
                Favourites
              </button>
              <button type="button" className={`${styles.tabBtn} ${styles.tabBtnActive}`}>
                Article Profile
              </button>
            </div>
          </header>

          {isLoading && <div className={styles.state}>Loading profile...</div>}
          {isError && <div className={styles.stateError}>Failed to load article profile.</div>}

          {profile && (
            <>
              <section className={styles.topicBar}>
                <h2 className={styles.prefSectionTitle}>Feed shaping summary</h2>
                <div className={styles.metricsRow}>
                  <div className={styles.metricCard}><strong>{profile.articles_liked}</strong><span>Liked</span></div>
                  <div className={styles.metricCard}><strong>{profile.articles_disliked}</strong><span>Disliked</span></div>
                  <div className={styles.metricCard}><strong>{profile.articles_favorited}</strong><span>Favorited</span></div>
                </div>
                <div className={styles.insightBlock}>
                  <p className={styles.filterLabel}>Top liked topics:</p>
                  <div className={styles.filterPills}>
                    {profile.liked_topics.length ? profile.liked_topics.map((topic) => (
                      <span key={topic.id} className={styles.topicBtnActive}>{topic.name}</span>
                    )) : <span className={styles.subheading}>No topic signal yet.</span>}
                  </div>
                </div>
                <div className={styles.insightBlock}>
                  <p className={styles.filterLabel}>Top disliked topics from feedback:</p>
                  <div className={styles.filterPills}>
                    {profile.inferred_disliked_topics.length ? profile.inferred_disliked_topics.map((topic) => (
                      <span key={topic.id} className={styles.topicBtn}>{topic.name}</span>
                    )) : <span className={styles.subheading}>No negative topic signal yet.</span>}
                  </div>
                </div>
              </section>

              <section className={styles.topicBar}>
                <h2 className={styles.prefSectionTitle}>Tune your feed preferences</h2>
                <SelectionGroup
                  label="Topics you want more of"
                  options={topicOptions}
                  selected={preferredTopics}
                  onToggle={toggleFromSet(setPreferredTopics)}
                />
                <SelectionGroup
                  label="Topics you want less of"
                  options={topicOptions}
                  selected={dislikedTopics}
                  onToggle={toggleFromSet(setDislikedTopics)}
                />
                <SelectionGroup
                  label="Sources you prefer"
                  options={siteOptions}
                  selected={preferredSites}
                  onToggle={toggleFromSet(setPreferredSites)}
                />
                <SelectionGroup
                  label="Sources you dislike"
                  options={siteOptions}
                  selected={dislikedSites}
                  onToggle={toggleFromSet(setDislikedSites)}
                />
                <SelectionGroup
                  label="Writers you prefer"
                  options={authorOptions}
                  selected={preferredAuthors}
                  onToggle={toggleFromSet(setPreferredAuthors)}
                />
                <SelectionGroup
                  label="Writers you dislike"
                  options={authorOptions}
                  selected={dislikedAuthors}
                  onToggle={toggleFromSet(setDislikedAuthors)}
                />

                <div className={styles.numericControls}>
                  <label className={styles.numericLabel}>
                    Quality threshold: {qualityThreshold}
                    <input
                      type="range"
                      min={0}
                      max={100}
                      value={qualityThreshold}
                      onChange={(event) => setQualityThreshold(Number(event.target.value))}
                    />
                  </label>
                  <label className={styles.numericLabel}>
                    Min read time (minutes)
                    <input
                      type="number"
                      min={0}
                      value={minReadTime}
                      onChange={(event) => setMinReadTime(Number(event.target.value || 0))}
                    />
                  </label>
                  <label className={styles.numericLabel}>
                    Max read time (minutes)
                    <input
                      type="number"
                      min={0}
                      value={maxReadTime}
                      onChange={(event) => setMaxReadTime(Number(event.target.value || 0))}
                    />
                  </label>
                </div>

                <button
                  type="button"
                  className={styles.pageBtn}
                  onClick={saveProfile}
                  disabled={saveMutation.isPending}
                >
                  {saveMutation.isPending ? 'Saving...' : 'Save preferences'}
                </button>
              </section>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default ArticleProfilePage;

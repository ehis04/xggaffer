/**
 * TrendSection.tsx
 *
 * Horizontal card grid showing trend highlights — top-performing teams,
 * top scorers, hat-tricks, or striker lulls.
 * Supports both 'team' and 'player' card variants.
 *
 * CSS: LiveFootballBasePage.module.css  (prefix: lfb-)
 */

import React from 'react';
import { Link } from 'react-router-dom';
import type {
  LiveFootballTrendPlayerCard,
  LiveFootballTrendTeamCard,
} from '../../../types/livefootball';
import { buildLiveFootballLink } from './linking';
import SectionFrame from './SectionFrame';
import styles from '../../../pages/livefootball/css/LiveFootballBasePage.module.css';

// ─── Helpers ─────────────────────────────────────────────────────────────────

const formatUpdatedAt = (value?: string | null): string | null => {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' });
};

const formatFormLabel = (value?: string | null): string => {
  const cleaned = (value || '').trim().replace(/\s*,\s*/g, '-');
  return cleaned;
};

const getFormTokens = (value?: string | null): string[] => {
  const cleaned = (value || '').trim();
  if (!cleaned) return [];
  return cleaned
    .split(/[-,]/)
    .map((t) => t.trim().toUpperCase())
    .filter((t) => t === 'W' || t === 'D' || t === 'L');
};

const formPillClass = (token: string): string => {
  if (token === 'W') return `${styles['lfb-form-pill']} ${styles['lfb-form-pill-win']}`;
  if (token === 'D') return `${styles['lfb-form-pill']} ${styles['lfb-form-pill-draw']}`;
  return `${styles['lfb-form-pill']} ${styles['lfb-form-pill-loss']}`;
};

const hasPlayer = (
  item: LiveFootballTrendTeamCard | LiveFootballTrendPlayerCard,
): item is LiveFootballTrendPlayerCard => 'player' in item;

const hasVisibleTeamCardData = (item: LiveFootballTrendTeamCard): boolean =>
  Boolean((item.team.short_name || item.team.name || '').trim())
  && Boolean((item.competition.name || '').trim())
  && Boolean((item.summary || '').trim())
  && Boolean((item.metric_label || '').trim())
  && Boolean((item.metric_value || '').trim());

const hasVisiblePlayerCardData = (item: LiveFootballTrendPlayerCard): boolean =>
  Boolean((item.player.short_name || item.player.name || '').trim())
  && Boolean((item.team.short_name || item.team.name || '').trim())
  && Boolean((item.summary || '').trim());

const hasVisibleTrendCardData = (
  item: LiveFootballTrendTeamCard | LiveFootballTrendPlayerCard,
  variant: 'team' | 'player',
): boolean => {
  if (variant === 'team') {
    return !hasPlayer(item) && hasVisibleTeamCardData(item as LiveFootballTrendTeamCard);
  }
  return hasPlayer(item) && hasVisiblePlayerCardData(item);
};

// ─── Props ────────────────────────────────────────────────────────────────────

interface Props {
  title: string;
  subtitle?: string;
  actionLabel: string;
  actionTo: string;
  items: Array<LiveFootballTrendTeamCard | LiveFootballTrendPlayerCard>;
  updatedAt?: string | null;
  variant?: 'team' | 'player';
}

// ─── Component ────────────────────────────────────────────────────────────────

const TrendSection: React.FC<Props> = ({
  title,
  subtitle,
  actionLabel,
  actionTo,
  items,
  updatedAt,
  variant = 'player',
}) => {
  const updatedAtLabel = formatUpdatedAt(updatedAt);
  const populatedItems = items.filter((item) => hasVisibleTrendCardData(item, variant));

  if (populatedItems.length === 0) return null;

  return (
    <SectionFrame
      title={title}
      subtitle={subtitle}
      actionLabel={actionLabel}
      actionTo={actionTo}
      meta={
        updatedAtLabel ? (
          <span className={styles['lfb-meta-text']}>Updated {updatedAtLabel}</span>
        ) : undefined
      }
    >
      <div className={styles['lfb-trend-grid']}>
          {populatedItems.map((item, i) => {
            const ctaTo = item.cta
              ? buildLiveFootballLink(item.cta.path, item.cta.query)
              : null;
            const formTokens = getFormTokens((item as LiveFootballTrendTeamCard).form_label);

            return (
              <article key={i} className={`${styles['lfb-info-card']} ${styles['lfb-card-fill']}`}>
                {variant === 'team' ? (
                  <>
                    <div className={styles['lfb-card-header-stack']}>
                      <div className={styles['lfb-compact-title']}>
                        {item.team.short_name || item.team.name}
                      </div>
                      <div className={`${styles['lfb-meta-text']} ${styles['lfb-meta-clamp-one']}`}>
                        {item.competition.name}
                      </div>
                      {'metric_label' in item && item.metric_label && item.metric_value && (
                        <div className={styles['lfb-metric-pill']}>
                          {item.metric_label}: {item.metric_value}
                        </div>
                      )}
                    </div>

                    {formTokens.length > 0 && (
                      <div
                        className={styles['lfb-form-pill-row']}
                        aria-label={`Recent form ${formatFormLabel((item as LiveFootballTrendTeamCard).form_label)}`}
                      >
                        <span className={styles['lfb-meta-text']}>Recent form</span>
                        <div className={styles['lfb-form-pill-list']}>
                          {formTokens.map((token, tokenIdx) => (
                            <span key={`${i}-${token}-${tokenIdx}`} className={formPillClass(token)}>
                              {token}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </>
                ) : hasPlayer(item) ? (
                  <div className={styles['lfb-card-header-stack']}>
                    <div className={styles['lfb-compact-title']}>
                      {item.player.short_name || item.player.name}
                    </div>
                    <div className={`${styles['lfb-meta-text']} ${styles['lfb-meta-clamp-one']}`}>
                      {item.team.short_name || item.team.name}
                      {item.competition.name ? ` • ${item.competition.name}` : ''}
                    </div>
                    {item.metric_label && item.metric_value && (
                      <div className={styles['lfb-metric-pill']}>
                        {item.metric_label}: {item.metric_value}
                      </div>
                    )}
                  </div>
                ) : null}

                <div className={`${styles['lfb-body-text']} ${styles['lfb-summary-clamp-three']}`}>
                  {item.summary}
                </div>

                <div className={styles['lfb-card-footer-row']}>
                  <span className={styles['lfb-meta-text']}>Rank {item.rank ?? '-'}</span>
                  {item.cta && ctaTo && (
                    <Link className={styles['lfb-compact-action-link']} to={ctaTo}>
                      {item.cta.label}
                    </Link>
                  )}
                </div>
              </article>
            );
          })}
        </div>
    </SectionFrame>
  );
};

export default TrendSection;

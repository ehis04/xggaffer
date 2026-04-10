import React from 'react';
import { Link } from 'react-router-dom';
import type {
  LiveFootballTrendPlayerCard,
  LiveFootballTrendTeamCard,
} from '../../../types/livefootball';
import { buildLiveFootballLink } from './linking';
import SectionFrame from './SectionFrame';
import styles from '../../../pages/livefootball/css/LiveFootballBasePage.module.css';

interface Props {
  title: string;
  subtitle?: string;
  actionLabel: string;
  actionTo: string;
  items: Array<LiveFootballTrendTeamCard | LiveFootballTrendPlayerCard>;
  updatedAt?: string | null;
  emptyMessage: string;
  variant?: 'team' | 'player';
}

const formatUpdatedAt = (value?: string | null): string | null => {
  if (!value) {
    return null;
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return null;
  }

  return date.toLocaleString('en-GB', {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
};

const formatFormLabel = (value?: string | null): string => {
  const cleaned = (value || '').trim().replace(/\s*,\s*/g, '-');
  return cleaned || 'No form data';
};

const getFormTokens = (value?: string | null): string[] => {
  const cleaned = (value || '').trim();
  if (!cleaned) {
    return [];
  }

  return cleaned
    .split(/[-,]/)
    .map((token) => token.trim().toUpperCase())
    .filter((token) => token === 'W' || token === 'D' || token === 'L');
};

const getFormPillClassName = (token: string): string => {
  if (token === 'W') {
    return `${styles.formPill} ${styles.formPillWin}`;
  }
  if (token === 'D') {
    return `${styles.formPill} ${styles.formPillDraw}`;
  }
  return `${styles.formPill} ${styles.formPillLoss}`;
};

const hasPlayer = (
  item: LiveFootballTrendTeamCard | LiveFootballTrendPlayerCard
): item is LiveFootballTrendPlayerCard => 'player' in item;

const TrendSection: React.FC<Props> = ({
  title,
  subtitle,
  actionLabel,
  actionTo,
  items,
  updatedAt,
  emptyMessage,
  variant = 'player',
}) => {
  const updatedAtLabel = formatUpdatedAt(updatedAt);

  return (
    <SectionFrame
      title={title}
      subtitle={subtitle}
      actionLabel={actionLabel}
      actionTo={actionTo}
      meta={
        updatedAtLabel ? (
          <span className={styles.metaText}>Updated {updatedAtLabel}</span>
        ) : undefined
      }
    >
      {items.length === 0 ? (
        <div className={styles.emptyState}>{emptyMessage}</div>
      ) : (
        <div className={styles.trendGrid}>
          {items.map((item, i) => {
            const ctaTo = item.cta
              ? buildLiveFootballLink(item.cta.path, item.cta.query)
              : null;

            return (
              <article key={i} className={`${styles.infoCard} ${styles.cardFill}`}>
                {variant === 'team' ? (
                  <>
                    <div className={styles.cardHeaderStack}>
                      <div className={styles.compactTitle}>
                        {item.team.short_name || item.team.name}
                      </div>

                      <div className={`${styles.metaText} ${styles.metaClampOne}`}>
                        {item.competition.name}
                      </div>

                      {'metric_label' in item && item.metric_label && item.metric_value ? (
                        <div className={styles.metricPill}>
                          {item.metric_label}: {item.metric_value}
                        </div>
                      ) : null}
                    </div>

                    {getFormTokens((item as LiveFootballTrendTeamCard).form_label).length > 0 ? (
                      <div
                        className={styles.formPillRow}
                        aria-label={`Recent form ${formatFormLabel(
                          (item as LiveFootballTrendTeamCard).form_label
                        )}`}
                      >
                        <span className={styles.metaText}>Recent form</span>
                        <div className={styles.formPillList}>
                          {getFormTokens((item as LiveFootballTrendTeamCard).form_label).map(
                            (token, tokenIndex) => (
                              <span
                                key={`${i}-${token}-${tokenIndex}`}
                                className={getFormPillClassName(token)}
                              >
                                {token}
                              </span>
                            )
                          )}
                        </div>
                      </div>
                    ) : (
                      <div className={styles.metaText}>Recent form: No form data</div>
                    )}
                  </>
                ) : hasPlayer(item) ? (
                  <>
                    <div className={styles.cardHeaderStack}>
                      <div className={styles.compactTitle}>
                        {item.player.short_name || item.player.name}
                      </div>

                      <div className={`${styles.metaText} ${styles.metaClampOne}`}>
                        {item.team.short_name || item.team.name}
                        {item.competition.name ? ` • ${item.competition.name}` : ''}
                      </div>

                      {item.metric_label && item.metric_value ? (
                        <div className={styles.metricPill}>
                          {item.metric_label}: {item.metric_value}
                        </div>
                      ) : null}
                    </div>
                  </>
                ) : null}

                <div className={`${styles.bodyText} ${styles.summaryClampThree}`}>
                  {item.summary}
                </div>

                <div className={styles.cardFooterRow}>
                  <span className={styles.metaText}>
                    Rank {item.rank ?? '-'}
                  </span>

                  {item.cta && ctaTo ? (
                    <Link className={styles.compactActionLink} to={ctaTo}>
                      {item.cta.label}
                    </Link>
                  ) : null}
                </div>
              </article>
            );
          })}
        </div>
      )}
    </SectionFrame>
  );
};

export default TrendSection;
import React from 'react';
import type { CommentaryBlock } from '../../../types/livefootball';
import styles from './css/CommentaryPanel.module.css';

interface CommentaryPanelProps {
  commentary: CommentaryBlock[];
  title?: string;
  emptyMessage?: string;
}

const CommentaryPanel: React.FC<CommentaryPanelProps> = ({
  commentary,
  title = 'Model commentary',
  emptyMessage = 'No commentary is available for this selection.',
}) => {
  return (
    <section className={styles.section}>
      <div className={styles.header}>
        <h2 className={styles.title}>{title}</h2>
      </div>

      {commentary.length === 0 ? (
        <div className={styles.emptyState}>{emptyMessage}</div>
      ) : (
        <div className={styles.list}>
          {commentary.map((block, index) => (
            <article
              key={`${block.type}-${index}-${block.text.slice(0, 20)}`}
              className={`${styles.card} ${styles[`type_${block.type}`]} ${styles[`confidence_${block.confidence}`]}`}
            >
              <div className={styles.cardMeta}>
                <span className={styles.typeLabel}>{block.type}</span>
                <span className={styles.confidenceLabel}>{block.confidence} confidence</span>
              </div>

              <p className={styles.text}>{block.text}</p>

              {block.related_teams.length > 0 ? (
                <div className={styles.relatedTeams}>
                  {block.related_teams.map((team) => (
                    <span key={team} className={styles.teamBadge}>
                      {team}
                    </span>
                  ))}
                </div>
              ) : null}
            </article>
          ))}
        </div>
      )}
    </section>
  );
};

export default CommentaryPanel;
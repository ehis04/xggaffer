import React, { useState, useEffect } from 'react';
import { Link, useParams } from 'react-router-dom';
import { teamsheetApi } from '../../../services/api';
import type { TeamsheetListItem } from '../../../types/teamsheet';
import styles from './TeamsheetListPage.module.css';

const TeamsheetListPage: React.FC = () => {
  const { clubId } = useParams<{ clubId: string }>();
  const [teamsheets, setTeamsheets] = useState<TeamsheetListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!clubId) return;

    const fetchTeamsheets = async () => {
      try {
        setLoading(true);
        const data = await teamsheetApi.list(Number(clubId));
        setTeamsheets(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load teamsheets');
      } finally {
        setLoading(false);
      }
    };

    fetchTeamsheets();
  }, [clubId]);

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'No date';
    return new Date(dateStr).toLocaleDateString('en-IE', {
      day: 'numeric',
      month: 'short',
    });
  };

  if (loading) {
    return (
      <div className={styles.container}>
        <div className={styles.loading}>Loading teamsheets...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.container}>
        <div className={styles.error}>{error}</div>
      </div>
    );
  }

  const templates = teamsheets.filter(t => t.is_template);
  const matches = teamsheets.filter(t => !t.is_template);

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1 className={styles.title}>Teamsheets</h1>
        <Link to={`/clubs/${clubId}/teamsheets/new`} className={styles.createButton}>
          + New Teamsheet
        </Link>
      </div>

      {templates.length > 0 && (
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>Templates</h2>
          <div className={styles.grid}>
            {templates.map(sheet => (
              <Link
                key={sheet.id}
                to={`/clubs/${clubId}/teamsheets/${sheet.id}`}
                className={styles.card}
              >
                <div className={styles.cardHeader}>
                  <span className={styles.formation}>{sheet.formation_display}</span>
                  <span className={styles.templateBadge}>Template</span>
                </div>
                <h3 className={styles.cardTitle}>{sheet.title}</h3>
                <div className={styles.cardMeta}>
                  <span className={sheet.is_complete ? styles.complete : styles.incomplete}>
                    {sheet.is_complete ? '✓ Complete' : `${sheet.starter_count}/11`}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        </section>
      )}

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Match Teamsheets</h2>
        {matches.length === 0 ? (
          <div className={styles.empty}>
            <p>No match teamsheets yet</p>
            <Link to={`/clubs/${clubId}/teamsheets/new`}>Create your first teamsheet</Link>
          </div>
        ) : (
          <div className={styles.grid}>
            {matches.map(sheet => (
              <Link
                key={sheet.id}
                to={`/clubs/${clubId}/teamsheets/${sheet.id}`}
                className={styles.card}
              >
                <div className={styles.cardHeader}>
                  <span className={styles.formation}>{sheet.formation_display}</span>
                  {sheet.match_date && (
                    <span className={styles.date}>{formatDate(sheet.match_date)}</span>
                  )}
                </div>
                <h3 className={styles.cardTitle}>{sheet.title}</h3>
                {sheet.opponent && (
                  <p className={styles.opponent}>vs {sheet.opponent}</p>
                )}
                <div className={styles.cardMeta}>
                  <span className={sheet.is_complete ? styles.complete : styles.incomplete}>
                    {sheet.is_complete ? '✓ Complete' : `${sheet.starter_count}/11`}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </section>
    </div>
  );
};

export default TeamsheetListPage;
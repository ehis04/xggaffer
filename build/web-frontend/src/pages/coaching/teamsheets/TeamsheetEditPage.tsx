import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { teamsheetApi } from '../../../services/api';
import type { Teamsheet } from '../../../types/teamsheet';
import styles from './css/TeamsheetCreatePage.module.css';

const TeamsheetEditPage: React.FC = () => {
  const { clubId, teamsheetId } = useParams<{ clubId: string; teamsheetId: string }>();
  const navigate = useNavigate();

  const [teamsheet, setTeamsheet] = useState<Teamsheet | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [title, setTitle] = useState('');
  const [matchDate, setMatchDate] = useState('');
  const [opponent, setOpponent] = useState('');
  const [notes, setNotes] = useState('');
  const [isTemplate, setIsTemplate] = useState(false);

  useEffect(() => {
    if (!clubId || !teamsheetId) return;
    teamsheetApi
      .get(Number(clubId), Number(teamsheetId))
      .then((data) => {
        setTeamsheet(data);
        setTitle(data.title);
        setMatchDate(data.match_date ?? '');
        setOpponent(data.opponent ?? '');
        setNotes(data.notes ?? '');
        setIsTemplate(data.is_template);
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load teamsheet'))
      .finally(() => setLoading(false));
  }, [clubId, teamsheetId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!clubId || !teamsheetId || !title.trim()) return;

    try {
      setSaving(true);
      setError(null);
      await teamsheetApi.update(Number(clubId), Number(teamsheetId), {
        title: title.trim(),
        match_date: matchDate || null,
        opponent: opponent.trim(),
        notes: notes.trim(),
        is_template: isTemplate,
      });
      navigate(`/clubs/${clubId}/teamsheets/${teamsheetId}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save changes');
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    navigate(`/clubs/${clubId}/teamsheets/${teamsheetId}`);
  };

  if (loading) {
    return (
      <div className={styles.container}>
        <div className={styles.loading}>Loading teamsheet...</div>
      </div>
    );
  }

  if (!teamsheet) {
    return (
      <div className={styles.container}>
        <div className={styles.loading}>Teamsheet not found</div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <form onSubmit={handleSubmit}>
        <div className={styles.header}>
          <h1 className={styles.title}>Edit Teamsheet</h1>
          <div className={styles.headerActions}>
            <button type="button" className={styles.cancelButton} onClick={handleCancel}>
              Cancel
            </button>
            <button
              type="submit"
              className={styles.submitButton}
              disabled={saving || !title.trim()}
            >
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </div>

        {error && <div className={styles.error}>{error}</div>}

        <div className={styles.section}>
          <h2 className={styles.sectionTitle}>Details</h2>

          <div className={styles.formGroup}>
            <label className={styles.label}>Title *</label>
            <input
              type="text"
              className={styles.input}
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
            />
          </div>

          <div className={styles.formRow}>
            <div className={styles.formGroup}>
              <label className={styles.label}>Match Date</label>
              <input
                type="date"
                className={styles.input}
                value={matchDate}
                onChange={(e) => setMatchDate(e.target.value)}
              />
            </div>

            <div className={styles.formGroup}>
              <label className={styles.label}>Opponent</label>
              <input
                type="text"
                className={styles.input}
                value={opponent}
                onChange={(e) => setOpponent(e.target.value)}
                placeholder="e.g., Liverpool"
              />
            </div>
          </div>

          <div className={styles.formGroup}>
            <label className={styles.label}>Notes</label>
            <textarea
              className={styles.textarea}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Tactical notes, key points, etc."
              rows={4}
            />
          </div>

          <div className={styles.checkbox}>
            <input
              type="checkbox"
              id="isTemplate"
              checked={isTemplate}
              onChange={(e) => setIsTemplate(e.target.checked)}
            />
            <label htmlFor="isTemplate">Save as template</label>
          </div>
        </div>
      </form>
    </div>
  );
};

export default TeamsheetEditPage;

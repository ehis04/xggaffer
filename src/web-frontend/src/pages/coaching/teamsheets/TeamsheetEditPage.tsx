import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { teamsheetApi } from '../../../services/api';
import type { Teamsheet } from '../../../types/teamsheet';
import { Sidebar } from '../../../components/Navigation/SideBar';
import { CoachingNavBar } from '../../../components/Navigation/CoachingNavBar';
import { SocialUserButtons } from '../../../components/Social/SocialUserButtons';
import styles from './TeamsheetEditPage.module.css';


const initials = (name: string) =>
  name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map(w => w[0].toUpperCase())
    .join('');

const formatMatchDate = (dateStr: string | null) => {
  if (!dateStr) return null;
  return new Date(dateStr).toLocaleDateString('en-IE', {
    weekday: 'short',
    day: '2-digit',
    month: 'short',
  });
};

const TeamsheetEditPage: React.FC = () => {
  const { clubId, teamsheetId } = useParams<{ clubId: string; teamsheetId: string }>();
  const navigate = useNavigate();

  const [teamsheet, setTeamsheet] = useState<Teamsheet | null>(null);
  const [loading, setLoading]     = useState(true);
  const [saving, setSaving]       = useState(false);
  const [error, setError]         = useState<string | null>(null);

  const [title, setTitle]           = useState('');
  const [matchDate, setMatchDate]   = useState('');
  const [kickoff, setKickoff]       = useState('');
  const [opponent, setOpponent]     = useState('');
  const [competition, setCompetition] = useState('');
  const [venue, setVenue]           = useState('');
  const [notes, setNotes]           = useState('');
  const [isTemplate, setIsTemplate] = useState(false);

  useEffect(() => {
    if (!clubId || !teamsheetId) return;
    teamsheetApi
      .get(Number(clubId), Number(teamsheetId))
      .then(data => {
        setTeamsheet(data);
        setTitle(data.title);
        setMatchDate(data.match_date ?? '');
        setOpponent(data.opponent ?? '');
        setNotes(data.notes ?? '');
        setIsTemplate(data.is_template);
        setKickoff((data as any).kickoff_time ?? '');
        setCompetition((data as any).competition ?? '');
        setVenue((data as any).venue ?? '');
      })
      .catch(err =>
        setError(err instanceof Error ? err.message : 'Failed to load teamsheet'),
      )
      .finally(() => setLoading(false));
  }, [clubId, teamsheetId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!clubId || !teamsheetId || !title.trim()) return;

    try {
      setSaving(true);
      setError(null);
      await teamsheetApi.update(Number(clubId), Number(teamsheetId), {
        title:       title.trim(),
        match_date:  matchDate || null,
        opponent:    opponent.trim(),
        notes:       notes.trim(),
        is_template: isTemplate,
      });
      navigate(`/clubs/${clubId}/teamsheets/${teamsheetId}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save changes');
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () =>
    navigate(`/clubs/${clubId}/teamsheets/${teamsheetId}`);


  const shell = (children: React.ReactNode) => (
    <div className={styles.teamsheetEditContainer}>
      <div className={styles.teamsheetEditSidebarSection}>
        <Sidebar />
      </div>
      <div className={styles.teamsheetEditMain}>
        <header className={styles.teamsheetEditHeader}>
          <div className={styles.teamsheetEditHeaderLeft}>
            Edit Teamsheet
          </div>
          <div>
            <CoachingNavBar />
          </div>
          <div className={styles.teamsheetEditHeaderRight}>
            <SocialUserButtons />
          </div>
        </header>
        {children}
      </div>
    </div>
  );

  if (loading) {
    return shell(
      <div className={styles.teamsheetEditStateWrap}>Loading teamsheet…</div>,
    );
  }

  if (!teamsheet) {
    return shell(
      <div className={styles.teamsheetEditStateWrap}>Teamsheet not found.</div>,
    );
  }

  const clubName     = (teamsheet as any).club_name ?? 'Your Club';
  const clubInitials = initials(clubName);
  const awayName     = opponent.trim() || 'Opponent';
  const awayInitials = initials(awayName);
  const dateLabel    = formatMatchDate(matchDate);


  return shell(
    <form onSubmit={handleSubmit}>
      <div className={styles.teamsheetEditContent}>

        <nav className={styles.teamsheetEditBreadcrumb}>
          <span>Teamsheets</span>
          <span className={styles.teamsheetEditBreadcrumbSep}>/</span>
          <span>{teamsheet.title}</span>
          <span className={styles.teamsheetEditBreadcrumbSep}>/</span>
          <span className={styles.teamsheetEditBreadcrumbCurrent}>Edit</span>
        </nav>

        <div className={styles.teamsheetEditActionBar}>
          <button
            type="button"
            className={styles.teamsheetEditCancelButton}
            onClick={handleCancel}
            disabled={saving}
          >
            Cancel
          </button>
          <button
            type="submit"
            className={styles.teamsheetEditSaveButton}
            disabled={saving || !title.trim()}
          >
            {saving ? 'Saving…' : 'Save Changes'}
          </button>
        </div>

        {error && (
          <div className={styles.teamsheetEditError}>{error}</div>
        )}

        <div className={styles.teamsheetEditHeroCard}>
          <div className={styles.teamsheetEditHeroHome}>
            <div className={styles.teamsheetEditHeroAvatar}>{clubInitials}</div>
            <div>
              <p className={styles.teamsheetEditHeroTeamName}>{clubName}</p>
              <p className={styles.teamsheetEditHeroTeamSub}>
                {teamsheet.formation_display ?? '—'} · Home
              </p>
            </div>
          </div>

          <div className={styles.teamsheetEditHeroVs}>
            {dateLabel && (
              <span className={styles.teamsheetEditHeroDate}>
                {dateLabel}{kickoff ? ` · ${kickoff}` : ''}
              </span>
            )}
            <span className={styles.teamsheetEditHeroVsLabel}>VS</span>
            {competition && (
              <span className={styles.teamsheetEditHeroCompetition}>
                {competition}
              </span>
            )}
          </div>

          <div className={styles.teamsheetEditHeroAway}>
            <div>
              <p className={styles.teamsheetEditHeroAwayName}>{awayName}</p>
              <p className={styles.teamsheetEditHeroAwaySub}>Away</p>
            </div>
            <div className={styles.teamsheetEditHeroAwayAvatar}>{awayInitials}</div>
          </div>
        </div>

        <div className={styles.teamsheetEditStatRow}>
          <div className={styles.teamsheetEditStatPill}>
            <span className={styles.teamsheetEditStatLabel}>Formation</span>
            <span className={styles.teamsheetEditStatValue}>
              {teamsheet.formation_display ?? '—'}
            </span>
          </div>
          <div className={styles.teamsheetEditStatPill}>
            <span className={styles.teamsheetEditStatLabel}>Starters</span>
            <span className={styles.teamsheetEditStatValue}>
              {teamsheet.starter_count ?? '—'} / 11
            </span>
          </div>
          <div className={styles.teamsheetEditStatPill}>
            <span className={styles.teamsheetEditStatLabel}>Status</span>
            <span className={styles.teamsheetEditStatValue}>
              {teamsheet.is_complete ? 'Complete' : 'Draft'}
            </span>
          </div>
          <div className={styles.teamsheetEditStatPill}>
            <span className={styles.teamsheetEditStatLabel}>Template</span>
            <span className={styles.teamsheetEditStatValue}>
              {isTemplate ? 'Yes' : 'No'}
            </span>
          </div>
        </div>

        <div className={styles.teamsheetEditFormGrid}>

          <div className={styles.teamsheetEditSection}>
            <h2 className={styles.teamsheetEditSectionTitle}>Match Details</h2>

            <div className={styles.teamsheetEditFormGroup}>
              <label htmlFor="ts-title" className={styles.teamsheetEditLabel}>
                Title *
              </label>
              <input
                id="ts-title"
                type="text"
                className={styles.teamsheetEditInput}
                value={title}
                onChange={e => setTitle(e.target.value)}
                placeholder="e.g. vs Northgate FC — League"
                required
              />
            </div>

            <div className={styles.teamsheetEditFormRow}>
              <div className={styles.teamsheetEditFormGroup}>
                <label htmlFor="ts-date" className={styles.teamsheetEditLabel}>
                  Match Date
                </label>
                <input
                  id="ts-date"
                  type="date"
                  className={styles.teamsheetEditInput}
                  value={matchDate}
                  onChange={e => setMatchDate(e.target.value)}
                />
              </div>

              <div className={styles.teamsheetEditFormGroup}>
                <label htmlFor="ts-kickoff" className={styles.teamsheetEditLabel}>
                  Kick Off
                </label>
                <input
                  id="ts-kickoff"
                  type="time"
                  className={styles.teamsheetEditInput}
                  value={kickoff}
                  onChange={e => setKickoff(e.target.value)}
                />
              </div>
            </div>

            <div className={styles.teamsheetEditFormRow}>
              <div className={styles.teamsheetEditFormGroup}>
                <label htmlFor="ts-opponent" className={styles.teamsheetEditLabel}>
                  Opposition
                </label>
                <input
                  id="ts-opponent"
                  type="text"
                  className={styles.teamsheetEditInput}
                  value={opponent}
                  onChange={e => setOpponent(e.target.value)}
                  placeholder="e.g. Northgate FC"
                />
              </div>

              <div className={styles.teamsheetEditFormGroup}>
                <label htmlFor="ts-competition" className={styles.teamsheetEditLabel}>
                  Competition
                </label>
                <input
                  id="ts-competition"
                  type="text"
                  className={styles.teamsheetEditInput}
                  value={competition}
                  onChange={e => setCompetition(e.target.value)}
                  placeholder="e.g. League — Premier Div"
                />
              </div>
            </div>

            <div className={styles.teamsheetEditFormGroup}>
              <label htmlFor="ts-venue" className={styles.teamsheetEditLabel}>
                Venue
              </label>
              <input
                id="ts-venue"
                type="text"
                className={styles.teamsheetEditInput}
                value={venue}
                onChange={e => setVenue(e.target.value)}
                placeholder="e.g. Riverside Park · Pitch 2"
              />
            </div>

            <hr className={styles.teamsheetEditInfoDivider} />

            <h2 className={styles.teamsheetEditSectionTitle}>Coach Notes</h2>

            <div className={styles.teamsheetEditFormGroup}>
              <label htmlFor="ts-notes" className={styles.teamsheetEditLabel}>
                Notes
              </label>
              <textarea
                id="ts-notes"
                className={styles.teamsheetEditTextarea}
                value={notes}
                onChange={e => setNotes(e.target.value)}
                placeholder="Tactical notes, key points for the match, set-piece instructions…"
                rows={5}
              />
            </div>

            <label
              className={styles.teamsheetEditCheckboxRow}
              htmlFor="ts-template"
            >
              <input
                id="ts-template"
                type="checkbox"
                className={styles.teamsheetEditCheckbox}
                checked={isTemplate}
                onChange={e => setIsTemplate(e.target.checked)}
              />
              <span className={styles.teamsheetEditCheckboxLabel}>
                Save as template
              </span>
            </label>
          </div>

          <div className={styles.teamsheetEditSidePanel}>

            <div className={styles.teamsheetEditInfoCard}>
              <h3 className={styles.teamsheetEditInfoTitle}>Teamsheet Info</h3>

              <div className={styles.teamsheetEditInfoRow}>
                <span className={styles.teamsheetEditInfoRowLabel}>Formation</span>
                <span className={styles.teamsheetEditInfoRowValue}>
                  {teamsheet.formation_display ?? '—'}
                </span>
              </div>

              <hr className={styles.teamsheetEditInfoDivider} />

              <div className={styles.teamsheetEditInfoRow}>
                <span className={styles.teamsheetEditInfoRowLabel}>Starters</span>
                <span className={styles.teamsheetEditInfoRowValue}>
                  {teamsheet.starter_count ?? 0} / 11
                </span>
              </div>

              <hr className={styles.teamsheetEditInfoDivider} />

              <div className={styles.teamsheetEditInfoRow}>
                <span className={styles.teamsheetEditInfoRowLabel}>Substitutes</span>
                <span className={styles.teamsheetEditInfoRowValue}>
                  {(teamsheet.players?.filter(p => p.is_substitute).length) ?? 0}
                </span>
              </div>

              <hr className={styles.teamsheetEditInfoDivider} />

              <div className={styles.teamsheetEditInfoRow}>
                <span className={styles.teamsheetEditInfoRowLabel}>Completion</span>
                <span className={styles.teamsheetEditInfoRowValue}>
                  {teamsheet.is_complete ? '✓ Complete' : 'Incomplete'}
                </span>
              </div>
            </div>

            <div className={styles.teamsheetEditDangerCard}>
              <h3 className={styles.teamsheetEditDangerTitle}>Danger Zone</h3>
              <button
                type="button"
                className={styles.teamsheetEditDangerButton}
                onClick={() =>
                  navigate(
                    `/clubs/${clubId}/teamsheets/${teamsheetId}?action=trash`,
                  )
                }
              >
                Move to trash
              </button>
            </div>

          </div>
        </div>
      </div>
    </form>,
  );
};

export default TeamsheetEditPage;
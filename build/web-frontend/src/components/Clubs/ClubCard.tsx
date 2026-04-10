import type { Club } from '../../types/club';
import styles from './css/ClubCard.module.css';

interface ClubCardProps {
  club: Club;
  variant: 'browse' | 'mine';
  onCopy?: (club: Club) => void;
  onClick?: (club: Club) => void;
}

const getClubTypeLabel = (club: Club): string | null => {
  if (club.club_type === 'user_fictional') {
    return club.fictional_basis === 'real_club_copy'
      ? 'Fictional copy'
      : 'Fictional club';
  }

  if (club.club_type === 'user_real_non_pro') {
    return 'Real non-pro club';
  }

  if (club.club_type === 'system_professional') {
    return 'System professional club';
  }

  return null;
};

const getDiscoveryLabel = (club: Club): string | null => {
  if (club.directory_visibility === 'hidden_code_only') {
    return 'Hidden club';
  }

  if (club.directory_visibility === 'listed') {
    return 'Listed club';
  }

  return null;
};

const getJoinPolicyLabel = (club: Club): string | null => {
  if (club.join_policy === 'approval_required') {
    return 'Approval required';
  }

  if (club.join_policy === 'invite_only') {
    return 'Invite only';
  }

  if (club.join_policy === 'system_managed') {
    return 'System managed';
  }

  return null;
};

const getVerificationLabel = (club: Club): string | null => {
  if (club.verification_status === 'pending') {
    return 'Pending verification';
  }

  if (club.verification_status === 'approved') {
    return 'Verified';
  }

  if (club.verification_status === 'rejected') {
    return 'Verification rejected';
  }

  return null;
};

const buildTags = (club: Club): string[] => {
  return [
    getClubTypeLabel(club),
    getDiscoveryLabel(club),
    getJoinPolicyLabel(club),
    getVerificationLabel(club),
  ].filter(Boolean) as string[];
};

export const ClubCard: React.FC<ClubCardProps> = ({ club, variant, onCopy, onClick }) => {
  const clickable = Boolean(onClick);
  const tags = buildTags(club);

  const handleClick = () => {
    onClick?.(club);
  };

  return (
    <div
      className={`${styles.card} ${clickable ? styles.clickable : ''}`}
      onClick={handleClick}
    >
      <div className={styles.cardHeader}>
        <div className={styles.badge}>
          {club.badge ? (
            <img src={club.badge} alt={club.name} className={styles.badgeImg} />
          ) : (
            <span className={styles.badgePlaceholder}>{club.name.charAt(0)}</span>
          )}
        </div>

        <div className={styles.headerInfo}>
          <h3 className={styles.name}>{club.name}</h3>
          {club.division && <span className={styles.division}>{club.division}</span>}
        </div>
      </div>

      {tags.length > 0 && (
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: '0.5rem',
            marginBottom: '0.85rem',
          }}
        >
          {tags.map((tag) => (
            <span
              key={tag}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                minHeight: '28px',
                padding: '0 0.75rem',
                borderRadius: '999px',
                background: 'rgba(255,255,255,0.08)',
                border: '1px solid rgba(255,255,255,0.14)',
                color: 'rgba(255,255,255,0.86)',
                fontSize: '0.78rem',
                fontWeight: 600,
              }}
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      {club.city && (
        <p className={styles.location}>
          {club.city}
          {club.country ? `, ${club.country}` : ''}
        </p>
      )}

      {club.source_real_club_name && (
        <p
          style={{
            margin: '0 0 0.75rem 0',
            color: 'rgba(255,255,255,0.65)',
            fontSize: '0.82rem',
          }}
        >
          Reference club: {club.source_real_club_name}
        </p>
      )}

      <p className={styles.description}>
        {club.description.length > 120
          ? `${club.description.slice(0, 120)}...`
          : club.description}
      </p>

      <div className={styles.stats}>
        <span className={styles.stat}>{club.player_count} players</span>
        <span className={styles.stat}>{club.member_count} members</span>
      </div>

      {variant === 'mine' && club.directory_visibility === 'hidden_code_only' && club.join_code && (
        <div
          style={{
            marginTop: '0.9rem',
            padding: '0.75rem',
            borderRadius: '10px',
            background: 'rgba(59,130,246,0.10)',
            border: '1px solid rgba(59,130,246,0.20)',
            color: 'white',
          }}
        >
          <div style={{ fontSize: '0.78rem', color: 'rgba(255,255,255,0.72)', marginBottom: '0.2rem' }}>
            Join code
          </div>
          <div style={{ fontWeight: 700, letterSpacing: '0.08em' }}>{club.join_code}</div>
        </div>
      )}

      {variant === 'browse' && onCopy && (
        <button
          className={styles.copyButton}
          onClick={(event) => {
            event.stopPropagation();
            onCopy(club);
          }}
        >
          Copy Club
        </button>
      )}
    </div>
  );
};
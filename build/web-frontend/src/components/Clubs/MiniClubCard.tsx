import { roleColors, statusColors } from "../../pages/coaching/clubs/MyClubsPage";
import type { MiniClubCardProps } from "../../pages/coaching/clubs/MyClubsPage";
import styles from '../../pages/coaching/clubs/css/MyClubsPage.module.css'

export const MiniClubCard: React.FC<MiniClubCardProps> = ({
  club,
  onClick,
  roleLabel,
  onTrash,
  onSelect,
  isSelected,
  isTrashView,
  trashLoading,
}) => {
  const initials = club.name.slice(0, 2).toUpperCase();
  const statusKey = (club as any).status ?? "active";
  const statusStyle = statusColors[statusKey] ?? statusColors.active;
  const roleColor = roleLabel
    ? (roleColors[roleLabel.toLowerCase().replace(/\s/g, "_")] ?? "#6b7280")
    : "#6b7280";
  const tags: string[] =
    ((club as any).age_groups ?? (club as any).division)
      ? [(club as any).division].filter(Boolean)
      : [];

  return (
    <div
      className={`${styles.miniCard} ${isSelected ? styles.miniCardSelected : ""}`}
      onClick={() => onClick(club)}
      style={{ cursor: "pointer" }}
    >
      <div className={styles.miniCardTop}>
        <div
          className={styles.miniCardBadge}
          style={{
            background: `${roleColor}22`,
            border: `1.5px solid ${roleColor}55`,
          }}
        >
          {club.badge ? (
            <img
              src={club.badge}
              alt={club.name}
              className={styles.miniCardBadgeImg}
            />
          ) : (
            <span
              style={{ color: roleColor, fontWeight: 700, fontSize: "0.95rem" }}
            >
              {initials}
            </span>
          )}
        </div>
        <div className={styles.miniCardInfo}>
          <div className={styles.miniCardName}>{club.name}</div>
          {roleLabel && <div className={styles.miniCardRole}>{roleLabel}</div>}
        </div>
        <div className={styles.miniCardStatus} style={statusStyle}>
          {statusKey.charAt(0).toUpperCase() + statusKey.slice(1)}
        </div>
      </div>

      {tags.length > 0 && (
        <div className={styles.miniCardTags}>
          {tags.map((t) => (
            <span key={t} className={styles.miniCardTag}>
              {t}
            </span>
          ))}
        </div>
      )}

      {club.description && (
        <p className={styles.miniCardDesc}>
          {club.description.length > 90
            ? club.description.slice(0, 90) + "…"
            : club.description}
        </p>
      )}

      <div className={styles.miniCardStats}>
        <div className={styles.miniCardStat}>
          <span className={styles.miniCardStatVal}>{club.member_count}</span>
          <span className={styles.miniCardStatLbl}>MEMBERS</span>
        </div>
        <div className={styles.miniCardStat}>
          <span className={styles.miniCardStatVal}>
            {(club as any).session_count ?? club.player_count}
          </span>
          <span className={styles.miniCardStatLbl}>SESSIONS</span>
        </div>
      </div>

      {isTrashView && (
        <div
          className={styles.miniCardActions}
          onClick={(e) => e.stopPropagation()}
        >
          <button
            className={`${styles.ghostBtn} ${isSelected ? styles.ghostBtnActive : ""}`}
            onClick={() => onSelect?.(club)}
          >
            {isSelected ? "Selected" : "Select"}
          </button>
          <button
            className={styles.dangerBtn}
            disabled={trashLoading}
            onClick={() => onTrash?.(club)}
          >
            {trashLoading ? "Moving…" : "Send to Trash"}
          </button>
        </div>
      )}
    </div>
  );
};
import { getInitials } from "./functions/getInitials";
import { statusConfig } from "./functions/statusConfig";
import type { PlayerCardData } from "./types/DashboardTypes";
import "./css/PlayerCarousel.css";

interface PlayerCardProps {
  player: PlayerCardData;
  isSelected: boolean;
  isUnavailable: boolean;
  onPlayerSelect?: (player: PlayerCardData) => void;
  status: (typeof statusConfig)[keyof typeof statusConfig];
}

export const PlayerCard = ({
  player,
  isSelected,
  isUnavailable,
  onPlayerSelect,
  status,
}: PlayerCardProps) => {
  return (
    <button
      className={[
        "player-card",
        isSelected ? "player-card--selected" : "",
        isUnavailable ? "player-card--unavailable" : "",
      ].join(" ")}
      onClick={() => onPlayerSelect?.(player)}
      aria-label={`${player.display_name}, ${player.position}, ${status.label}`}
      aria-pressed={isSelected}
    >
      <div
        className="p-card-status-dot"
        style={{ background: status.colour }}
        title={status.label}
      />
      <div className="player-card-profile">
        <span>{getInitials(player.display_name)}</span>
      </div>
      <span className="player-card-name">
        {player.display_name.split(" ")[0]}
      </span>
      <span className="player-card-pos">{player.position}</span>
    </button>
  );
};

import { useNavigate } from "react-router-dom";
import "./css/ProfileTopBar.css";

interface ProfileTopBarProps {
  displayName?: string;
  postCount?: number;
  isOwnProfile?: boolean;
  onShare?: () => void;
}

export const ProfileTopBar = ({
  displayName,
  postCount,
  isOwnProfile = false,
  onShare,
}: ProfileTopBarProps) => {
  const navigate = useNavigate();

  return (
    <div className="ptb-container">

      <div className="ptb-left">
        <button
          className="ptb-back-btn"
          onClick={() => navigate(-1)}
          aria-label="Go back"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="15 18 9 12 15 6" />
          </svg>
        </button>

        {displayName && (
          <div className="ptb-title-block">
            <span className="ptb-display-name">{displayName}</span>
            {postCount !== undefined && (
              <span className="ptb-post-count">
                {postCount.toLocaleString()} {postCount === 1 ? "post" : "posts"}
              </span>
            )}
          </div>
        )}
      </div>

    </div>
  );
};
import { ProfileButton } from "../Buttons/ProfileButton";
import type { FollowStatus, ProfileData } from "./types/ProfileTypes";
import "./css/ProfileHeader.css";

interface ProfileHeaderProps {
  userData: ProfileData | null;
  loggedInUser: ProfileData | null;
  followStatus: FollowStatus | null;
  isOwnProfile: boolean;
  onEditProfile: () => void;
  onFollow: () => void;
}

export const ProfileHeader = ({
  userData,
  loggedInUser,
  followStatus,
  isOwnProfile,
  onEditProfile,
  onFollow,
}: ProfileHeaderProps) => {
  const getFollowLabel = () => {
    if (followStatus?.follow_request_pending) return "Requested";
    if (followStatus?.is_following) return "Following";
    return "Follow";
  };

  const getVisibilityLabel = () => {
    if (userData?.visibility === "PRIVATE") return "Private";
    if (userData?.visibility === "FOLLOWERS") return "Followers";
    return "Public";
  };

  const formatJoinDate = (dateStr?: string) => {
    if (!dateStr) return null;
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString("en-IE", {
        month: "long",
        year: "numeric",
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="ph-container">
      <div className="ph-top-row">
        <div className="ph-avatar-wrap">
          {userData && (
            <ProfileButton username={userData.username} size="extra-large" />
          )}
          {isOwnProfile && (
            <div className="ph-avatar-overlay">
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
                <circle cx="12" cy="13" r="4" />
              </svg>
              <span>Photo</span>
            </div>
          )}
        </div>

        <div className="ph-actions">
          {isOwnProfile ? (
            <>
              <button className="ph-btn-primary" onClick={onEditProfile}>
                Edit Profile
              </button>
              <button className="ph-btn-icon" title="Share profile">
                <svg
                  width="15"
                  height="15"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <circle cx="18" cy="5" r="3" />
                  <circle cx="6" cy="12" r="3" />
                  <circle cx="18" cy="19" r="3" />
                  <line x1="8.59" y1="13.51" x2="15.42" y2="17.49" />
                  <line x1="15.41" y1="6.51" x2="8.59" y2="10.49" />
                </svg>
              </button>
            </>
          ) : (
            <>
              <button
                className={`ph-btn-follow${followStatus?.is_following ? " ph-btn-following" : ""}`}
                onClick={onFollow}
              >
                {getFollowLabel()}
              </button>
              <button className="ph-btn-primary">Message</button>
            </>
          )}
        </div>
      </div>

      <div className="ph-names">
        <span className="ph-display-name">
          {userData?.display_name || userData?.username}
        </span>
        <span className="ph-username">@{userData?.username}</span>
        {!isOwnProfile && followStatus?.followed_by && (
          <span className="ph-follows-you">Follows you</span>
        )}
      </div>

      {userData?.bio ? (
        <div className="ph-bio">{userData.bio}</div>
      ) : isOwnProfile ? (
        <div className="ph-bio ph-bio-empty" onClick={onEditProfile}>
          Add a bio...
        </div>
      ) : null}

      <div className="ph-meta">
        {userData?.created_at && (
          <div className="ph-meta-item">
            <svg
              width="13"
              height="13"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
              <line x1="16" y1="2" x2="16" y2="6" />
              <line x1="8" y1="2" x2="8" y2="6" />
              <line x1="3" y1="10" x2="21" y2="10" />
            </svg>
            <span>Joined {formatJoinDate(userData.created_at)}</span>
          </div>
        )}
        {isOwnProfile && userData?.visibility && (
          <div className="ph-meta-item">
            <span
              className={`ph-visibility-badge${userData.visibility === "PRIVATE" ? " ph-visibility-private" : ""}`}
              onClick={isOwnProfile ? onEditProfile : undefined}
            >
              {getVisibilityLabel()}
            </span>
          </div>
        )}
      </div>

      {userData?.roles && userData.roles.length > 0 && (
        <div className="ph-tags">
          {userData.roles.map((role) => (
            <span key={role.id} className="ph-tag ph-tag-role">
              {role.role_display}
            </span>
          ))}
        </div>
      )}

      <div className="ph-stats">
        <div className="ph-stat-item">
          <span className="ph-stat-num">{userData?.followers_count ?? 0}</span>
          <span className="ph-stat-label">followers</span>
        </div>
        <div className="ph-stat-item">
          <span className="ph-stat-num">{userData?.following_count ?? 0}</span>
          <span className="ph-stat-label">following</span>
        </div>
      </div>
    </div>
  );
};

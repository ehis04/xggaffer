import type React from "react";
import "./css/ProfileButton.css";

export interface ProfileButtonProps {
  username: string;
  profileImage?: string;
  size?: "small" | "medium" | "large" | "extra-large";
  onClick?: (username: string) => void;
  showLabel?: boolean;
}

export const ProfileButton: React.FC<ProfileButtonProps> = ({
  username,
  profileImage,
  size = "small",
  onClick,
  showLabel,
}) => {
  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (onClick) {
      onClick(username);
    } else {
      globalThis.location.href = `/profile/${username}`;
    }
  };

  const getInitial = () => {
    return username ? username[0].toUpperCase() : "?";
  };

  return (
    <div className="profile-button-container">
      <button className={`profile-button ${size}`} onClick={handleClick}>
        <div className="profile-button-pic">
          {profileImage ? (
            <img
              src={profileImage}
              alt={username || "User"}
              className="profile-pic"
            />
          ) : (
            <div className="profile-placeholder">{getInitial()}</div>
          )}
        </div>
        {showLabel && (
            <div className="profile-button-info">
                <span className="profile-button-name">
                    {username}
                </span>
                <span className="profile-button-username">
                    @{username}
                </span>
            </div>
        )}
      </button>
    </div>
  );
};

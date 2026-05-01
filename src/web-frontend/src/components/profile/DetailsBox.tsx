import type { ProfileData } from "./types/ProfileTypes";
import "./css/DetailsBox.css";

interface DetailsBoxProps {
  userData: ProfileData | null;
}

const formatJoinDate = (dateStr?: string) => {
  if (!dateStr) return "—";
  try {
    return new Date(dateStr).toLocaleDateString("en-IE", {
      month: "short",
      year: "numeric",
    });
  } catch {
    return dateStr;
  }
};

const visibilityLabel = (v?: string) => {
  if (v === "PR" || v === "PRIVATE") return "Private";
  return "Public";
};

export const DetailsBox = ({ userData }: DetailsBoxProps) => {
  return (
    <div className="dbox-container">
      <div className="dbox-title">Your details</div>
      <div className="dbox-card">
        <div className="dbox-row">
          <span className="dbox-key">Display name</span>
          <span className="dbox-val">{userData?.display_name || userData?.username || "—"}</span>
        </div>

        {userData?.roles && userData.roles.length > 0 && (
          <div className="dbox-row">
            <span className="dbox-key">Role</span>
            <div className="dbox-badges">
              {userData.roles.map((role) => (
                <span key={role.id} className="dbox-badge">{role.role_display}</span>
              ))}
            </div>
          </div>
        )}

        <div className="dbox-row">
          <span className="dbox-key">Gender</span>
          <span className="dbox-val">{userData?.gender || "—"}</span>
        </div>

        <div className="dbox-row">
          <span className="dbox-key">Visibility</span>
          <span className="dbox-val">{visibilityLabel(userData?.visibility)}</span>
        </div>

        <div className="dbox-row dbox-row--last">
          <span className="dbox-key">Member since</span>
          <span className="dbox-val">{formatJoinDate(userData?.created_at)}</span>
        </div>
      </div>
    </div>
  );
};

import type { ProfileData } from "./types/ProfileTypes";
import "./css/YourRoles.css";

const ALL_ROLES = [
  { key: "COACH",   label: "Coach" },
  { key: "REFEREE", label: "Referee" },
  { key: "PLAYER",  label: "Player" },
  { key: "FAN",     label: "Fan" },
] as const;

type RoleKey = typeof ALL_ROLES[number]["key"];

interface YourRolesProps {
  userData: ProfileData | null;
  onRoleToggle: (roleKey: RoleKey, willBeActive: boolean) => void;
}

const hasRole = (
  roles: ProfileData["roles"],
  key: RoleKey,
  label: string,
): boolean => {
  if (!roles || roles.length === 0) return false;
  return roles.some(
    (r) =>
      r.role_display.toLowerCase() === label.toLowerCase() ||
      r.role.toUpperCase() === key,
  );
};

export const YourRoles = ({ userData, onRoleToggle }: YourRolesProps) => {
  return (
    <div className="yr-container">
      <div className="yr-title">Your roles</div>
      <div className="yr-card">
        {ALL_ROLES.map((role, idx) => {
          const isActive = hasRole(userData?.roles, role.key, role.label);
          return (
            <div
              key={role.key}
              className={`yr-row${idx === ALL_ROLES.length - 1 ? " yr-row--last" : ""}`}
            >
              <div className={`yr-label${!isActive ? " yr-label--inactive" : ""}`}>
                <span className={`yr-dot${!isActive ? " yr-dot--inactive" : ""}`} />
                {role.label}
              </div>
              <button
                className={`yr-toggle${isActive ? " yr-toggle--on" : " yr-toggle--off"}`}
                title={isActive ? "Active — click to remove" : "Inactive — click to add"}
                onClick={() => onRoleToggle(role.key, !isActive)}
                aria-pressed={isActive}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
};
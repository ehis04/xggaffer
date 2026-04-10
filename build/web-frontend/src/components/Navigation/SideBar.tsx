import React, { useEffect, useState } from "react";
import { ProfileButton } from "../Buttons/ProfileButton";
import "./css/SideBar.css";
import { getUserProfile } from "./functions/getUserProfile";
import { useAuth } from '../../context/useAuth';

interface NavItem {
  id: string;
  icon: React.ReactNode;
  label: string;
  badge?: number;
  onClick?: () => void;
  link: string;
}

interface SidebarProps {
  items?: NavItem[];
  logo?: React.ReactNode;
  bottomItems?: NavItem[];
}

export interface UserData {
  username: string;
  profile_image?: string;
}

const http = "http://localhost:5173/";

export const Sidebar: React.FC<SidebarProps> = ({ items, logo, bottomItems }) => {
  const [isHovered, setIsHovered] = useState(false);
  const [userData, setUserData] = useState<UserData | null>(null);

  const { logout, user } = useAuth();

  useEffect(() => {
    getUserProfile(setUserData);
  }, []);

  const handleProfileClick = (username: string) => {
    globalThis.location.href = `/profile/${username}`;
  };

  const defaultItems: NavItem[] = [
    {
      id: "home",
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" className="bi bi-house-door" viewBox="0 0 16 16">
          <path d="M8.354 1.146a.5.5 0 0 0-.708 0l-6 6A.5.5 0 0 0 1.5 7.5v7a.5.5 0 0 0 .5.5h4.5a.5.5 0 0 0 .5-.5v-4h2v4a.5.5 0 0 0 .5.5H14a.5.5 0 0 0 .5-.5v-7a.5.5 0 0 0-.146-.354L13 5.793V2.5a.5.5 0 0 0-.5-.5h-1a.5.5 0 0 0-.5.5v1.293zM2.5 14V7.707l5.5-5.5 5.5 5.5V14H10v-4a.5.5 0 0 0-.5-.5h-3a.5.5 0 0 0-.5.5v4z" />
        </svg>
      ),
      label: "Home",
      onClick: () => (globalThis.location.href = "/"),
      link: "/",
    },
    {
      id: "explore",
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" className="bi bi-compass" viewBox="0 0 16 16">
          <path d="M8 16.016a7.5 7.5 0 0 0 1.962-14.74A1 1 0 0 0 9 0H7a1 1 0 0 0-.962 1.276A7.5 7.5 0 0 0 8 16.016m6.5-7.5a6.5 6.5 0 1 1-13 0 6.5 6.5 0 0 1 13 0" />
          <path d="m6.94 7.44 4.95-2.83-2.83 4.95-4.949 2.83 2.828-4.95z" />
        </svg>
      ),
      label: "Explore",
      onClick: () => (globalThis.location.href = "/explore"),
      link: "/explore",
    },
    {
      id: "coaching",
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" className="bi bi-clipboard-check" viewBox="0 0 16 16">
          <path fillRule="evenodd" d="M10.854 7.146a.5.5 0 0 1 0 .708l-3 3a.5.5 0 0 1-.708 0l-1.5-1.5a.5.5 0 1 1 .708-.708L7.5 9.793l2.646-2.647a.5.5 0 0 1 .708 0" />
          <path d="M4 1.5H3a2 2 0 0 0-2 2V14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V3.5a2 2 0 0 0-2-2h-1v1h1a1 1 0 0 1 1 1V14a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3.5a1 1 0 0 1 1-1h1z" />
          <path d="M9.5 1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-3a.5.5 0 0 1-.5-.5v-1a.5.5 0 0 1 .5-.5zm-3-1A1.5 1.5 0 0 0 5 1.5v1A1.5 1.5 0 0 0 6.5 4h3A1.5 1.5 0 0 0 11 2.5v-1A1.5 1.5 0 0 0 9.5 0z" />
        </svg>
      ),
      label: "Coaching",
      onClick: () => (globalThis.location.href = "/coaching"),
      link: "/coaching",
    },
  ];

  const defaultBottomItems: NavItem[] = [
    {
      id: "logout",
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" className="bi bi-power" viewBox="0 0 16 16">
          <path d="M7.5 1v7h1V1z" />
          <path d="M3 8.812a5 5 0 0 1 2.578-4.375l-.485-.874A6 6 0 1 0 11 3.616l-.501.865A5 5 0 1 1 3 8.812" />
        </svg>
      ),
      label: "Logout",
      onClick: logout,
      link: http,
    },
  ];

  const navItems = items ?? defaultItems;
  const bottomNavItems = bottomItems ?? defaultBottomItems;

  return (
    <>
      <aside
        className={`sidebar ${isHovered ? "expanded" : "collapsed"}`}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
      >
        <div className="sidebar-content">
          <div className="sidebar-logo">
            {logo ?? (
              <svg xmlns="http://www.w3.org/2000/svg" width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" className="icon icon-tabler icon-tabler-ball-football">
                <path stroke="none" d="M0 0h24v24H0z" fill="none" />
                <path d="M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0 -18 0" />
                <path d="M12 7l4.76 3.45l-1.76 5.55h-6l-1.76 -5.55z" />
                <path d="M12 7v-4m3 13l2.5 3m-.74 -8.55l3.74 -1.45m-11.44 7.05l-2.56 2.95m.74 -8.55l-3.74 -1.45" />
              </svg>
            )}
          </div>

          <div className="sidebar-profile">
            {userData && (
              <ProfileButton
                username={userData.username}
                size="small"
                showLabel={isHovered}
                onClick={handleProfileClick}
              />
            )}
          </div>

          <nav className="sidebar-nav">
            {navItems.map((item) => (
              <button
                key={item.id}
                className="sidebar-button"
                onClick={item.onClick ?? (() => (globalThis.location.href = item.link))}
                aria-label={item.label}
                type="button"
              >
                <div className="sidebar-item-icon">
                  {item.icon}
                  {item.badge && item.badge > 0 && (
                    <span className="sidebar-badge">
                      {item.badge > 99 ? "99+" : item.badge}
                    </span>
                  )}
                </div>
                <span className="sidebar-item-label">{item.label}</span>
              </button>
            ))}
          </nav>

          <nav className="sidebar-nav-bottom">
            {bottomNavItems.map((item) => (
              <button
                key={item.id}
                className="sidebar-button"
                onClick={item.onClick ?? (() => (globalThis.location.href = item.link))}
                aria-label={item.label}
                type="button"
              >
                <div className="sidebar-item-icon">{item.icon}</div>
                <span className="sidebar-item-label">{item.label}</span>
              </button>
            ))}
          </nav>
        </div>
      </aside>

      <button
        onClick={logout}
        style={{
          padding: "10px 16px",
          background: "#dc3545",
          color: "white",
          border: "none",
          borderRadius: "8px",
          cursor: "pointer",
        }}
        type="button"
      >
        Logout {user?.email ? `(${user.email})` : ""}
      </button>
    </>
  );
};

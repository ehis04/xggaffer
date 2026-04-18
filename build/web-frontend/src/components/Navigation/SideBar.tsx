import { ProfileButton } from "../Buttons/ProfileButton";
import "./css/SideBar.css";
import React, { useEffect, useState } from "react";
import { getUserProfile } from "./functions/getUserProfile";
import { Navigate } from "react-router-dom";

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

export interface User {
    id: number;
    username: string;
    email: string;
    first_name: string;
    last_name: string;
  };

export interface UserRole {
  id: number;
  role: string;
  role_display: string;
  created_at: string;
}
export interface UserData {
  user: User;
  username: string;
  display_name?: string;
  bio?: string;
  followers_count: number;
  following_count: number;
  gender: string;
  profile_image?: string;
  roles: UserRole[];
  visibility: string;
  created_at: string;
}



const http = "http://localhost:5173/";

export const Sidebar: React.FC<SidebarProps> = ({
  items,
  logo,
  bottomItems,
}) => {
  const [isHovered, setIsHovered] = useState(false);
  const [userData, setUserData] = useState<UserData | null>(null);

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
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="16"
          height="16"
          fill="currentColor"
          className="bi bi-house-door"
          viewBox="0 0 16 16"
        >
          <path d="M8.354 1.146a.5.5 0 0 0-.708 0l-6 6A.5.5 0 0 0 1.5 7.5v7a.5.5 0 0 0 .5.5h4.5a.5.5 0 0 0 .5-.5v-4h2v4a.5.5 0 0 0 .5.5H14a.5.5 0 0 0 .5-.5v-7a.5.5 0 0 0-.146-.354L13 5.793V2.5a.5.5 0 0 0-.5-.5h-1a.5.5 0 0 0-.5.5v1.293zM2.5 14V7.707l5.5-5.5 5.5 5.5V14H10v-4a.5.5 0 0 0-.5-.5h-3a.5.5 0 0 0-.5.5v4z" />
        </svg>
      ),
      label: "Home",
      onClick: () => console.log("Home clicked"),
      link: "",
    },
    {
      id: "social",
      icon: (
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="16"
          height="16"
          fill="currentColor"
          className="bi bi-chat-square-quote"
          viewBox="0 0 16 16"
        >
          <path d="M14 1a1 1 0 0 1 1 1v8a1 1 0 0 1-1 1h-2.5a2 2 0 0 0-1.6.8L8 14.333 6.1 11.8a2 2 0 0 0-1.6-.8H2a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1zM2 0a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2.5a1 1 0 0 1 .8.4l1.9 2.533a1 1 0 0 0 1.6 0l1.9-2.533a1 1 0 0 1 .8-.4H14a2 2 0 0 0 2-2V2a2 2 0 0 0-2-2z" />
          <path d="M7.066 4.76A1.665 1.665 0 0 0 4 5.668a1.667 1.667 0 0 0 2.561 1.406c-.131.389-.375.804-.777 1.22a.417.417 0 1 0 .6.58c1.486-1.54 1.293-3.214.682-4.112zm4 0A1.665 1.665 0 0 0 8 5.668a1.667 1.667 0 0 0 2.561 1.406c-.131.389-.375.804-.777 1.22a.417.417 0 1 0 .6.58c1.486-1.54 1.293-3.214.682-4.112z" />
        </svg>
      ),
      label: "Social",
      onClick: () => console.log("Social clicked"),
      link: "http://localhost:5173/social",
    },
    {
      id: "explore",
      icon: (
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="16"
          height="16"
          fill="currentColor"
          className="bi bi-compass"
          viewBox="0 0 16 16"
        >
          <path d="M8 16.016a7.5 7.5 0 0 0 1.962-14.74A1 1 0 0 0 9 0H7a1 1 0 0 0-.962 1.276A7.5 7.5 0 0 0 8 16.016m6.5-7.5a6.5 6.5 0 1 1-13 0 6.5 6.5 0 0 1 13 0" />
          <path d="m6.94 7.44 4.95-2.83-2.83 4.95-4.949 2.83 2.828-4.95z" />
        </svg>
      ),
      label: "Explore",
      onClick: () => console.log("Explore clicked"),
      link: "",
    },
    {
      id: "coaching",
      icon: (
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="16"
          height="16"
          fill="currentColor"
          className="bi bi-clipboard-check"
          viewBox="0 0 16 16"
        >
          <path
            fillRule="evenodd"
            d="M10.854 7.146a.5.5 0 0 1 0 .708l-3 3a.5.5 0 0 1-.708 0l-1.5-1.5a.5.5 0 1 1 .708-.708L7.5 9.793l2.646-2.647a.5.5 0 0 1 .708 0"
          />
          <path d="M4 1.5H3a2 2 0 0 0-2 2V14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V3.5a2 2 0 0 0-2-2h-1v1h1a1 1 0 0 1 1 1V14a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3.5a1 1 0 0 1 1-1h1z" />
          <path d="M9.5 1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-3a.5.5 0 0 1-.5-.5v-1a.5.5 0 0 1 .5-.5zm-3-1A1.5 1.5 0 0 0 5 1.5v1A1.5 1.5 0 0 0 6.5 4h3A1.5 1.5 0 0 0 11 2.5v-1A1.5 1.5 0 0 0 9.5 0z" />
        </svg>
      ),
      label: "Coaching",
      onClick: () => console.log("Coaching clicked"),
      link: "http://localhost:5173/coaching/dashboard",
    },
    {
      id: "referee",
      icon: (
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 23 23"
          width="23"
          height="23"
          fill="none"
          stroke="white"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M3.10372 11.5252C4.5522 9.4378 7.06815 8.86485 8.53763 9.00054H11.0609C11.5887 9.09126 11.734 9.30978 12.3879 10.3428C12.5068 10.6673 14.4421 10.4487 14.9506 10.5017C15.5091 9.96055 14.9506 8.85082 16.1911 9.00826C18.3195 9.00826 20.359 8.91699 21.2926 9.0542C21.678 9.11085 21.8634 9.45879 21.9189 9.84439C22.1422 11.3942 21.8764 12.5285 21.6192 12.7882C20.9324 14.004 18.9502 15.1828 17.9677 14.9959C15.133 14.9959 14.52 14.9221 14.2742 15.3924L13.4101 17.6267C12.833 18.8562 10.8098 21.283 7.41618 20.9705C4.02257 20.6581 2.54699 17.9449 2.24399 16.6574C1.94099 15.8329 1.65427 13.6141 3.10372 11.5252Z" />
          <path d="M13.4893 5.00318V3.00195M10.9942 6.00379L9.99609 5.00318M15.9845 6.00379L16.9826 5.00318" />
          <path d="M8.08398 17C9.18855 17 10.084 16.1046 10.084 15C10.084 13.8954 9.18855 13 8.08398 13C6.97941 13 6.08398 13.8954 6.08398 15C6.08398 16.1046 6.97941 17 8.08398 17Z" />
        </svg>
      ),
      label: "Referee",
      onClick: () => console.log("Referee clicked"),
      link: "http://localhost:5173/referee",
    },
    {
      id: "trash",
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" className="bi bi-trash3" viewBox="0 0 16 16">
          <path d="M6.5 1h3a1 1 0 0 1 1 1V3h3.5a.5.5 0 0 1 0 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4H2a.5.5 0 0 1 0-1H5.5V2a1 1 0 0 1 1-1Zm1 2h1V2h-1v1ZM4 4v9a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4H4Zm2.5 2.5a.5.5 0 0 1 1 0V12a.5.5 0 0 1-1 0V6.5Zm3 0a.5.5 0 0 1 1 0V12a.5.5 0 0 1-1 0V6.5Z" />
        </svg>
      ),
      label: "Trash",
      onClick: () => (globalThis.location.href = "/trash"),
      link: "/trash",
    },
  ];

  const defaultBottomItems: NavItem[] = [
    {
      id: "logout",
      icon: (
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="16"
          height="16"
          fill="currentColor"
          className="bi bi-power"
          viewBox="0 0 16 16"
        >
          <path d="M7.5 1v7h1V1z" />
          <path d="M3 8.812a5 5 0 0 1 2.578-4.375l-.485-.874A6 6 0 1 0 11 3.616l-.501.865A5 5 0 1 1 3 8.812" />
        </svg>
      ),
      label: "logout",
      onClick: () => console.log("Logout clicked"),
      link: http,
    },
    {
      id: "settings",
      icon: (
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="16"
          height="16"
          fill="currentColor"
          className="bi bi-gear"
          viewBox="0 0 16 16"
        >
          <path d="M8 4.754a3.246 3.246 0 1 0 0 6.492 3.246 3.246 0 0 0 0-6.492M5.754 8a2.246 2.246 0 1 1 4.492 0 2.246 2.246 0 0 1-4.492 0" />
          <path d="M9.796 1.343c-.527-1.79-3.065-1.79-3.592 0l-.094.319a.873.873 0 0 1-1.255.52l-.292-.16c-1.64-.892-3.433.902-2.54 2.541l.159.292a.873.873 0 0 1-.52 1.255l-.319.094c-1.79.527-1.79 3.065 0 3.592l.319.094a.873.873 0 0 1 .52 1.255l-.16.292c-.892 1.64.901 3.434 2.541 2.54l.292-.159a.873.873 0 0 1 1.255.52l.094.319c.527 1.79 3.065 1.79 3.592 0l.094-.319a.873.873 0 0 1 1.255-.52l.292.16c1.64.893 3.434-.902 2.54-2.541l-.159-.292a.873.873 0 0 1 .52-1.255l.319-.094c1.79-.527 1.79-3.065 0-3.592l-.319-.094a.873.873 0 0 1-.52-1.255l.16-.292c.893-1.64-.902-3.433-2.541-2.54l-.292.159a.873.873 0 0 1-1.255-.52zm-2.633.283c.246-.835 1.428-.835 1.674 0l.094.319a1.873 1.873 0 0 0 2.693 1.115l.291-.16c.764-.415 1.6.42 1.184 1.185l-.159.292a1.873 1.873 0 0 0 1.116 2.692l.318.094c.835.246.835 1.428 0 1.674l-.319.094a1.873 1.873 0 0 0-1.115 2.693l.16.291c.415.764-.42 1.6-1.185 1.184l-.291-.159a1.873 1.873 0 0 0-2.693 1.116l-.094.318c-.246.835-1.428.835-1.674 0l-.094-.319a1.873 1.873 0 0 0-2.692-1.115l-.292.16c-.764.415-1.6-.42-1.184-1.185l.159-.291A1.873 1.873 0 0 0 1.945 8.93l-.319-.094c-.835-.246-.835-1.428 0-1.674l.319-.094A1.873 1.873 0 0 0 3.06 4.377l-.16-.292c-.415-.764.42-1.6 1.185-1.184l.292.159a1.873 1.873 0 0 0 2.692-1.115z" />
        </svg>
      ),
      label: "Settings",
      onClick: () => console.log("Settings clicked"),
      link: "",
    },
    {
      id: "help",
      icon: (
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="16"
          height="16"
          fill="currentColor"
          className="bi bi-question-circle"
          viewBox="0 0 16 16"
        >
          <path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14m0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16" />
          <path d="M5.255 5.786a.237.237 0 0 0 .241.247h.825c.138 0 .248-.113.266-.25.09-.656.54-1.134 1.342-1.134.686 0 1.314.343 1.314 1.168 0 .635-.374.927-.965 1.371-.673.489-1.206 1.06-1.168 1.987l.003.217a.25.25 0 0 0 .25.246h.811a.25.25 0 0 0 .25-.25v-.105c0-.718.273-.927 1.01-1.486.609-.463 1.244-.977 1.244-2.056 0-1.511-1.276-2.241-2.673-2.241-1.267 0-2.655.59-2.75 2.286m1.557 5.763c0 .533.425.927 1.01.927.609 0 1.028-.394 1.028-.927 0-.552-.42-.94-1.029-.94-.584 0-1.009.388-1.009.94" />
        </svg>
      ),
      label: "Help",
      onClick: () => console.log("Help clicked"),
      link: "",
    },
  ];

  const navItems = items || defaultItems;
  const bottomNavItems = bottomItems || defaultBottomItems;

  return (
    <aside
      className={`sidebar ${isHovered ? "expanded" : "collapsed"}`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div className="sidebar-content">
        <div className="sidebar-logo">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="30"
            height="30"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.3"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="icon icon-tabler icons-tabler-outline icon-tabler-ball-football"
          >
            <path stroke="none" d="M0 0h24v24H0z" fill="none" />
            <path d="M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0 -18 0" />
            <path d="M12 7l4.76 3.45l-1.76 5.55h-6l-1.76 -5.55z" />
            <path d="M12 7v-4m3 13l2.5 3m-.74 -8.55l3.74 -1.45m-11.44 7.05l-2.56 2.95m.74 -8.55l-3.74 -1.45" />
          </svg>
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
              onClick={item.onClick}
              aria-label={item.label}
            >
              <div className="sidebar-item-icon">
                <a href={item.link}>{item.icon}</a>
                {item.badge && item.badge > 0 && (
                  <span className="sidebar-badge">
                    {item.badge > 99 ? "99+" : item.badge}
                  </span>
                )}
              </div>
              <span className="sidebar-item-label">
                <a href={item.link}>{item.label}</a>
              </span>
            </button>
          ))}
        </nav>

        <nav className="sidebar-nav-bottom">
          {bottomNavItems.map((item) => (
            <button
              key={item.id}
              className="sidebar-button"
              onClick={item.onClick}
              aria-label={item.label}
            >
              <div className="sidebar-item-icon">
                <a href={item.link}>{item.icon}</a>
              </div>
              <span className="sidebar-item-label">
                <a href={item.link}>{item.label}</a>
              </span>
            </button>
          ))}
        </nav>
      </div>
    </aside>
  );
};

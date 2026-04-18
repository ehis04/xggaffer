import { useState } from "react";
import "./css/ProfileTabs.css";

type TabId = "posts" | "clubs" | "acheivements" | "liked";

interface Tab {
  id: TabId;
  label: string;
}

const TABS: Tab[] = [
  { id: "posts", label: "Posts" },
  { id: "clubs", label: "Clubs" },
  { id: "acheivements", label: "Acheivements" },
  { id: "liked", label: "Liked" },
];

interface ProfileTabsProps {
  activeTab?: TabId;
  onTabChange?: (tab: TabId) => void;
}

export const ProfileTabs = ({ activeTab = "posts", onTabChange }: ProfileTabsProps) => {
  const [active, setActive] = useState<TabId>(activeTab);

  const handleClick = (id: TabId) => {
    setActive(id);
    onTabChange?.(id);
  };

  return (
    <div className="ptabs-container">
      {TABS.map((tab) => (
        <button
          key={tab.id}
          className={`ptabs-tab${active === tab.id ? " ptabs-tab--active" : ""}`}
          onClick={() => handleClick(tab.id)}
        >
          {tab.label}
          {active === tab.id && <span className="ptabs-indicator" />}
        </button>
      ))}
    </div>
  );
};
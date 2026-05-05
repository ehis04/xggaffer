import type { ClubsNavItem } from "./types/NavTypes";
import "./css/CoachingNavBar.css";
import { useNavigate } from "react-router-dom";

export const ClubsNavBar = () => {
  const navigate = useNavigate();
  const handleTabClick = (link: string) => {
    navigate(link);
  };

  const TABS: ClubsNavItem[] = [
    {
      id: "tab1",
      label: "My Clubs",
      onClick: () => handleTabClick("http://localhost:5173/clubs"),
      cls: "tab--1",
    },
    {
      id: "tab2",
      label: "Browse",
      onClick: () => handleTabClick("http://localhost:5173/clubs/browse"),
      cls: "tab--2",
    },
    {
      id: "tab3",
      label: "Create",
      onClick: () => handleTabClick("http://localhost:5173/clubs/create"),
      cls: "tab--3",
    },
  ];
  return (
    <div className="coaching-navbar">
      {TABS.map((tab) => (
        <>
          <input
            key={`input-${tab.id}`}
            type="radio"
            name="tab"
            id={tab.id}
            className={`tab ${tab.cls}`}
            onClick={tab.onClick}
          />
          <label
            key={`label-${tab.id}`}
            className="coaching-navbar-lbl"
            htmlFor={tab.id}
          >
            {tab.label}
          </label>
        </>
      ))}
    </div>
  );
};

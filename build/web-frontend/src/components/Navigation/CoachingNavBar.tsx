import "./css/CoachingNavBar.css";

const TABS = [
  { id: "tab1", label: "Dashboard", cls: "tab--1" },
  { id: "tab2", label: "Players", cls: "tab--2" },
  { id: "tab3", label: "Formations", cls: "tab--3" },
  { id: "tab4", label: "Schedule", cls: "tab--4" },
  { id: "tab5", label: "Season", cls: "tab--5" },
];

export const CoachingNavBar = () => {
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
            defaultChecked={tab.id === "tab1"}
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
      <div className="indicator" />
    </div>
  );
};

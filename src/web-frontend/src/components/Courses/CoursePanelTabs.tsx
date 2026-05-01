import "./css/CoursePanelTabs.css";

export type CoursePanelTab = "path" | "results";

interface CoursePanelTabsProps {
  activeTab: CoursePanelTab;
  onChange: (tab: CoursePanelTab) => void;
}

const TABS: { id: CoursePanelTab; label: string }[] = [
  { id: "path",    label: "Course Path" },
  { id: "results", label: "Results" },
];

export const CoursePanelTabs = ({ activeTab, onChange }: CoursePanelTabsProps) => {
  return (
    <div className="cpt-tabs" role="tablist">
      {TABS.map((tab) => (
        <button
          key={tab.id}
          role="tab"
          aria-selected={activeTab === tab.id}
          className={`cpt-tab ${activeTab === tab.id ? "cpt-tab--active" : ""}`}
          onClick={() => onChange(tab.id)}
        >
          {tab.label}
          {activeTab === tab.id && <span className="cpt-tab-indicator" />}
        </button>
      ))}
    </div>
  );
};
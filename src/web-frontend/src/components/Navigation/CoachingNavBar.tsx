import { useSearchParams } from 'react-router-dom';
import "./css/CoachingNavBar.css";

export type ClubTab =
  | 'dashboard'
  | 'players'
  | 'formations'
  | 'schedule'
  | 'training'
  | 'season'
  | 'members'
  | 'tactics';

const TABS: { value: ClubTab; label: string }[] = [
  { value: 'dashboard',  label: 'Dashboard'  },
  { value: 'players',    label: 'Players'    },
  { value: 'formations', label: 'Formations' },
  { value: 'training',   label: 'Training'   },
  { value: 'schedule',   label: 'Schedule'   },
  { value: 'season',     label: 'Season'     },
  { value: 'members',    label: 'Members'    },
  { value: 'tactics',    label: 'Tactics'    },
];

const TAB_WIDTH = 110;

interface CoachingNavBarProps {
  activeTab?: ClubTab;
  onTabChange?: (tab: ClubTab) => void;
}

export const CoachingNavBar = ({ activeTab, onTabChange }: CoachingNavBarProps) => {
  const [searchParams, setSearchParams] = useSearchParams();

  const currentTab: ClubTab = (() => {
    if (activeTab) return activeTab;
    const param = searchParams.get('tab') as ClubTab | null;
    return param && TABS.some((t) => t.value === param) ? param : 'dashboard';
  })();

  const activeIndex = TABS.findIndex((t) => t.value === currentTab);
  const indicatorLeft = activeIndex * TAB_WIDTH + 2;

  const handleTabClick = (tab: ClubTab) => {
    if (onTabChange) {
      onTabChange(tab);
      return;
    }
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      next.set('tab', tab);
      return next;
    });
  };

  return (
    <div className="coaching-navbar" style={{ '--tab-width': `${TAB_WIDTH}px` } as React.CSSProperties}>
      {TABS.map((tab) => (
        <button
          key={tab.value}
          type="button"
          className={`coaching-navbar-lbl${currentTab === tab.value ? ' coaching-navbar-lbl--active' : ''}`}
          onClick={() => handleTabClick(tab.value)}
        >
          {tab.label}
        </button>
      ))}
      <div
        className="indicator"
        style={{ left: `${indicatorLeft}px` }}
      />
    </div>
  );
};

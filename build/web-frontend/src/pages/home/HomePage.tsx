import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Sidebar, type UserData } from "../../components/Navigation/SideBar";
import { SocialUserButtons } from "../../components/Social/SocialUserButtons";
import { getUserProfile } from "../../components/Navigation/functions/getUserProfile";
import styles from "./css/HomePage.module.css";

interface HomeSection {
  id: string;
  icon: string;
  title: string;
  description: string;
  label: string;
  path: string;
}

const CORE_SECTIONS: HomeSection[] = [
  {
    id: "social",
    icon: "💬",
    title: "Social Feed",
    description:
      "Catch up with football discussions, posts, and community updates from across the platform.",
    label: "Open Social Feed",
    path: "/social",
  },
  {
    id: "articles",
    icon: "📰",
    title: "Articles",
    description:
      "Read football articles, manage favourites, and explore recommended analysis content.",
    label: "Read Articles",
    path: "/articles",
  },
  {
    id: "referee",
    icon: "🟨",
    title: "Referee Training",
    description:
      "Study the Laws of the Game, complete learning modules, and build referee knowledge.",
    label: "Start Training",
    path: "/referee",
  },
  {
    id: "coaching",
    icon: "📋",
    title: "Coaching Hub",
    description:
      "Manage coaching workflows, player data, teamsheets, tactics boards, and club resources.",
    label: "Open Coaching",
    path: "/coaching",
  },
  {
    id: "predictions",
    icon: "🔮",
    title: "Predictions",
    description:
      "Use deterministic prediction tools for match outcomes, season projections, and model insights.",
    label: "Open Predictions",
    path: "/predictions/hub",
  },
  {
    id: "live-football",
    icon: "📡",
    title: "Live Football",
    description:
      "Browse live football data, league tables, fixtures, club pages, and player information.",
    label: "View Live Football",
    path: "/livefootball",
  },
  {
    id: "clubs",
    icon: "🏟️",
    title: "My Clubs",
    description:
      "Create clubs, manage memberships, review join requests, and organise squads.",
    label: "Manage Clubs",
    path: "/clubs",
  },
];

const buildHomeSections = (profilePath: string): HomeSection[] => [
  ...CORE_SECTIONS,
  {
    id: "profile",
    icon: "👤",
    title: "Profile",
    description:
      "View your football identity, role information, account details, and public profile page.",
    label: "Open Profile",
    path: profilePath,
  },
];

const HomePage = () => {
  const navigate = useNavigate();
  const [userData, setUserData] = useState<UserData | null>(null);

  useEffect(() => {
    getUserProfile(setUserData);
  }, []);

  const profilePath = userData?.username
    ? `/profile/${encodeURIComponent(userData.username)}`
    : "/social";

  const sections = useMemo(() => buildHomeSections(profilePath), [profilePath]);

  return (
    <div className={styles.homeShell}>
      <div className={styles.sidebarWrap}>
        <Sidebar />
      </div>

      <main className={styles.homePage}>
        <header className={styles.topBar}>
          <div>
            <span className={styles.eyebrow}>Football AI</span>
            <h1 className={styles.pageTitle}>Home</h1>
          </div>
          <SocialUserButtons />
        </header>

        <section className={styles.hero}>
          <div className={styles.heroCopy}>
            <span className={styles.heroKicker}>Your football hub</span>
            <h2 className={styles.heroTitle}>Welcome to xgGaffer</h2>
            <p className={styles.heroSubtitle}>
              Move quickly between coaching tools, prediction intelligence, live football data,
              referee learning, articles, clubs, and community features.
            </p>
          </div>
          <div className={styles.heroPanel} aria-label="Platform summary">
            <span className={styles.heroPanelNumber}>8</span>
            <span className={styles.heroPanelLabel}>different Sections</span>
          </div>
        </section>

        <section className={styles.sectionHeader}>
          <div>
            <h2 className={styles.sectionTitle}>Platform areas</h2>
            <p className={styles.sectionSubtitle}>
              Choose where you want to work next.
            </p>
          </div>
        </section>

        <div className={styles.cardGrid}>
          {sections.map((section) => (
            <button
              key={section.id}
              className={styles.card}
              type="button"
              onClick={() => navigate(section.path)}
              aria-label={section.label}
            >
              <span className={styles.cardIcon}>{section.icon}</span>
              <span className={styles.cardContent}>
                <span className={styles.cardTitle}>{section.title}</span>
                <span className={styles.cardDescription}>{section.description}</span>
              </span>
              <span className={styles.cardAction}>
                {section.label}
                <span aria-hidden="true">→</span>
              </span>
            </button>
          ))}
        </div>
      </main>
    </div>
  );
};

export default HomePage;

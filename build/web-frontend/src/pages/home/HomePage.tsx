import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Sidebar, type UserData } from "../../components/Navigation/SideBar";
import { SocialUserButtons } from "../../components/Social/SocialUserButtons";
import { getUserProfile } from "../../components/Navigation/functions/getUserProfile";
import { articlesApi } from "../../services/api/articlesApi";
import communityApi, { type Post } from "../../services/api/communityApi";
import { clubsApi } from "../../services/api";
import apiClient from "../../services/api/client";
import { REFEREE } from "../../services/api/endpoints";
import type { ArticleListItem } from "../../types/articles";
import type { Club, ClubCalendarFeedItem, ClubSeasonResult } from "../../types/club";
import type { DashboardData } from "../referee/types/RefereeTypes";
import type { LawCourse } from "../../components/RefereeDashboard/types/RefereeDashboardTypes";
import styles from "./css/HomePage.module.css";

interface ClubResultItem extends ClubSeasonResult {
  club_name: string;
}

interface ClubUpdateItem {
  id: string;
  clubName: string;
  title: string;
  meta: string;
  date: string;
}

const quickLinks = [
  { label: "Social Feed", path: "/social", icon: "chat" },
  { label: "My Clubs", path: "/clubs", icon: "home" },
  { label: "Referee Training", path: "/referee", icon: "whistle" },
  { label: "Articles", path: "/articles", icon: "article" },
  { label: "Predictions", path: "/predictions/hub", icon: "predict" },
  { label: "Coaching Hub", path: "/coaching", icon: "clipboard" },
];

const formatDate = (value?: string | null) => {
  if (!value) return "";
  return new Date(value).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
  });
};

const formatHeroDate = () =>
  new Date().toLocaleDateString("en-GB", {
    weekday: "long",
    day: "2-digit",
    month: "short",
    year: "numeric",
  });

const getGreeting = () => {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
};

const initials = (value: string) =>
  value
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();

const iconPath = (icon: string) => {
  switch (icon) {
    case "chat":
      return "M4 5h16v9H8l-4 4V5z";
    case "home":
      return "M3 11l9-7 9 7v9h-5v-6H8v6H3z";
    case "whistle":
      return "M5 12c1.4-2.1 4-2.7 5.5-2.5h2.2c.6.1.8.4 1.3 1.2.4.6 1.9.3 2.5.3.4-.5.2-1.4 1.2-1.4h3c.7 0 1 .5 1 1.1 0 2.7-2.2 4.4-4.5 4.1-1.3-.1-2.5-.1-2.8.5l-.8 2.1c-.6 1.4-2.7 3.2-5.4 2.8-2.9-.4-4.3-2.8-4.5-4.1-.2-.8-.1-2.4 1.3-4.1z";
    case "article":
      return "M5 4h14v16H5zM8 8h8M8 12h8M8 16h5";
    case "predict":
      return "M12 3l2.5 5 5.5.8-4 3.9.9 5.5L12 15.6 7.1 18.2 8 12.7 4 8.8 9.5 8z";
    default:
      return "M6 4h12v16H6zM9 8h6M9 12h6M9 16h3";
  }
};

const calendarToUpdate = (item: ClubCalendarFeedItem): ClubUpdateItem | null => {
  const source = item.event ?? item.fixture;
  if (!source) return null;

  const title =
    item.item_type === "event" && item.event
      ? item.event.title
      : item.fixture?.calendar_label ?? "Club fixture";

  const meta =
    item.item_type === "event" && item.event
      ? item.event.event_type_display
      : item.fixture?.competition || "Fixture";

  return {
    id: `${item.item_type}-${source.id}`,
    clubName: source.club_name,
    title,
    meta,
    date: item.sort_datetime,
  };
};

const HomePage = () => {
  const navigate = useNavigate();
  const [userData, setUserData] = useState<UserData | null>(null);
  const [articles, setArticles] = useState<ArticleListItem[]>([]);
  const [posts, setPosts] = useState<Post[]>([]);
  const [clubs, setClubs] = useState<Club[]>([]);
  const [courses, setCourses] = useState<LawCourse[]>([]);
  const [clubResults, setClubResults] = useState<ClubResultItem[]>([]);
  const [clubUpdates, setClubUpdates] = useState<ClubUpdateItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getUserProfile(setUserData);
  }, []);

  useEffect(() => {
    let mounted = true;

    const loadHome = async () => {
      try {
        setLoading(true);
        const [articleFeed, postFeed, clubList, dashboard] = await Promise.all([
          articlesApi.getFeed({ sort: "relevance" }),
          communityApi.explorePosts({ order_by: "recent", page_size: 3 }),
          clubsApi.myClubs(),
          apiClient.get<DashboardData>(REFEREE.DASHBOARD),
        ]);

        if (!mounted) return;

        setArticles(articleFeed.results.slice(0, 3));
        setPosts(postFeed.results.slice(0, 3));
        setClubs(clubList.filter((club) => !club.is_trashed).slice(0, 3));
        setCourses(dashboard.courses);

        const activeClubs = clubList.filter((club) => !club.is_trashed).slice(0, 4);
        const updates = await Promise.all(
          activeClubs.map(async (club) => {
            const [calendar, results] = await Promise.all([
              clubsApi.listCalendarFeed(club.id, { include_past: true, limit: 4 }).catch(() => []),
              clubsApi.seasonResults.list(club.id).catch(() => []),
            ]);

            return {
              updates: calendar.map(calendarToUpdate).filter(Boolean) as ClubUpdateItem[],
              results: results.map((result) => ({
                ...result,
                club_name: club.name,
              })),
            };
          }),
        );

        if (!mounted) return;

        setClubUpdates(
          updates
            .flatMap((item) => item.updates)
            .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
            .slice(0, 4),
        );
        setClubResults(
          updates
            .flatMap((item) => item.results)
            .sort((a, b) => new Date(b.match_date).getTime() - new Date(a.match_date).getTime())
            .slice(0, 3),
        );
      } catch (error) {
        console.error("Could not load home dashboard:", error);
      } finally {
        if (mounted) setLoading(false);
      }
    };

    void loadHome();

    return () => {
      mounted = false;
    };
  }, []);

  const firstName = useMemo(() => {
    if (userData?.display_name) return userData.display_name.split(" ")[0];
    if (userData?.user.first_name) return userData.user.first_name;
    if (userData?.username) return userData.username;
    return "there";
  }, [userData]);

  const activeCourses = courses.filter((course) => course.status === "active");
  const recentCourses = courses
    .filter((course) => course.status !== "locked")
    .sort((a, b) => {
      if (a.status === b.status) return b.progress_percentage - a.progress_percentage;
      return a.status === "active" ? -1 : 1;
    })
    .slice(0, 3);

  const upcomingMatches = clubUpdates.filter((item) => new Date(item.date).getTime() >= Date.now()).length;
  const unreadPosts = posts.length;

  return (
    <div className={styles.homeShell}>
      <Sidebar />

      <main className={styles.homePage}>
        <header className={styles.topBar}>
          <div>
            <span className={styles.eyebrow}>XGGAFFER</span>
            <h1 className={styles.pageTitle}>Home</h1>
          </div>
          <SocialUserButtons />
        </header>

        <section className={styles.hero}>
          <div>
            <span className={styles.heroDate}>{formatHeroDate()}</span>
            <h2 className={styles.heroTitle}>
              {getGreeting()}, {firstName}
            </h2>
            <p className={styles.heroSubtitle}>
              You have {activeCourses.length} active course{activeCourses.length === 1 ? "" : "s"} and{" "}
              {upcomingMatches} upcoming club update{upcomingMatches === 1 ? "" : "s"}.
            </p>
          </div>
          <div className={styles.heroStats}>
            <div className={styles.statCard}>
              <strong>{activeCourses.length}</strong>
              <span>Active courses</span>
            </div>
            <div className={styles.statCard}>
              <strong>{upcomingMatches}</strong>
              <span>Club updates</span>
            </div>
            <div className={styles.statCard}>
              <strong>{unreadPosts}</strong>
              <span>Recent posts</span>
            </div>
          </div>
        </section>

        <section className={styles.jumpSection}>
          <div className={styles.sectionIntro}>
            <h2>Jump back in</h2>
            <p>Recently accessed sections</p>
          </div>
          <div className={styles.quickLinks}>
            {quickLinks.map((link) => (
              <button key={link.path} type="button" onClick={() => navigate(link.path)}>
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d={iconPath(link.icon)} />
                </svg>
                {link.label}
              </button>
            ))}
          </div>
        </section>

        <div className={styles.contentGrid}>
          <section className={styles.articleSection}>
            <div className={styles.sectionRow}>
              <div className={styles.sectionIntro}>
                <h2>Recommended Articles</h2>
                <p>Curated for your interests</p>
              </div>
              <button type="button" className={styles.linkButton} onClick={() => navigate("/articles")}>
                View all
              </button>
            </div>

            <div className={styles.articleGrid}>
              {articles.map((article) => (
                <article
                  key={article.id}
                  className={styles.articleCard}
                  onClick={() => navigate(`/articles/${article.id}`)}
                >
                  <div className={styles.articleImage}>
                    {article.image_url ? <img src={article.image_url} alt="" /> : <span>article image</span>}
                  </div>
                  <div className={styles.articleMeta}>
                    <span className={styles.topicPill}>{article.topics[0]?.name ?? "Analysis"}</span>
                    <span>{article.site.name}</span>
                    <time>{formatDate(article.publication_date)}</time>
                  </div>
                  <h3>{article.title}</h3>
                  <p>{article.summary}</p>
                  <div className={styles.articleFooter}>
                    <span>{article.read_time_minutes} min read</span>
                    <span>Read</span>
                  </div>
                </article>
              ))}
              {!articles.length &&
                Array.from({ length: 3 }).map((_, index) => (
                  <div key={index} className={styles.articleCardSkeleton} />
                ))}
            </div>
          </section>

          <aside className={styles.postsPanel}>
            <div className={styles.sectionRow}>
              <div className={styles.sectionIntro}>
                <h2>Recent Posts</h2>
                <p>From the social feed</p>
              </div>
              <button type="button" className={styles.linkButton} onClick={() => navigate("/social")}>
                Open feed
              </button>
            </div>
            <div className={styles.postList}>
              {posts.map((post) => (
                <button
                  type="button"
                  key={post.id}
                  className={styles.postCard}
                  onClick={() => navigate(`/social/post/${post.id}`)}
                >
                  <span className={styles.avatar}>{initials(post.author.username || "User")}</span>
                  <span className={styles.postBody}>
                    <span>@{post.author.username}</span>
                    <strong>{post.text_body}</strong>
                    <small>{post.no_of_likes} likes · {post.no_of_comments} comments</small>
                  </span>
                  <time>{formatDate(post.created_at)}</time>
                </button>
              ))}
              {!posts.length && !loading && <p className={styles.emptyText}>No recent posts found.</p>}
            </div>
          </aside>
        </div>

        <section className={styles.lowerGrid}>
          <div>
            <div className={styles.sectionRow}>
              <div className={styles.sectionIntro}>
                <h2>Recent Clubs</h2>
              </div>
              <button type="button" className={styles.linkButton} onClick={() => navigate("/clubs")}>
                All clubs
              </button>
            </div>
            <div className={styles.clubGrid}>
              {clubs.map((club) => (
                <button
                  type="button"
                  className={styles.clubCard}
                  key={club.id}
                  onClick={() => navigate(`/clubs/${club.id}/details`)}
                >
                  <span>{initials(club.name)}</span>
                  <strong>{club.name}</strong>
                  <small>{club.member_count} members</small>
                </button>
              ))}
            </div>
          </div>

          <div>
            <div className={styles.sectionRow}>
              <div className={styles.sectionIntro}>
                <h2>Recent Courses</h2>
              </div>
              <button type="button" className={styles.linkButton} onClick={() => navigate("/referee")}>
                All courses
              </button>
            </div>
            <div className={styles.courseGrid}>
              {recentCourses.map((course) => (
                <button
                  type="button"
                  key={course.law_number}
                  className={styles.courseCard}
                  onClick={() => navigate(`/referee/law/${course.law_number}`)}
                >
                  <span>Law {course.law_number}</span>
                  <strong>{course.title}</strong>
                  <div className={styles.progressTrack}>
                    <span style={{ width: `${course.progress_percentage}%` }} />
                  </div>
                  <small>
                    {course.progress_percentage}% · {course.status === "completed" ? "Done" : "In Progress"}
                  </small>
                </button>
              ))}
            </div>
          </div>
        </section>

        <section className={styles.resultsSection}>
          <div className={styles.sectionRow}>
            <div className={styles.sectionIntro}>
              <h2>Club Updates</h2>
              <p>From clubs you're part of</p>
            </div>
            <button type="button" className={styles.linkButton} onClick={() => navigate("/clubs")}>
              View clubs
            </button>
          </div>

          <div className={styles.updateGrid}>
            <div className={styles.updateList}>
              {clubUpdates.map((update) => (
                <div key={update.id} className={styles.updateRow}>
                  <span>{initials(update.clubName)}</span>
                  <div>
                    <strong>{update.title}</strong>
                    <small>{update.clubName} · {update.meta}</small>
                  </div>
                  <time>{formatDate(update.date)}</time>
                </div>
              ))}
            </div>

            <div className={styles.updateList}>
              {clubResults.map((result) => (
                <div key={result.id} className={styles.updateRow}>
                  <span>{result.outcome}</span>
                  <div>
                    <strong>
                      {result.club_name} {result.goals_for} - {result.goals_against} {result.opponent_name}
                    </strong>
                    <small>{result.competition || "Club result"}</small>
                  </div>
                  <time>{formatDate(result.match_date)}</time>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>
    </div>
  );
};

export default HomePage;

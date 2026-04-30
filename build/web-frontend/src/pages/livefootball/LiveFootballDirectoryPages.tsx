import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import CompetitionSelector from '../../components/livefootball/CompetitionSelector';
import FixturesPanel from '../../components/livefootball/FixturesPanel';
import liveFootballApi from '../../services/api/livefootballApi';
import type {
  CompetitionListItem,
  CompetitionPreviousNextFixturesResponse,
  CompetitionTopScorerItem,
  PlayerLookupItem,
  TeamLookupItem,
} from '../../types/livefootball';
import styles from './css/LiveFootballPage.module.css';

const normalizeError = (error: unknown): string => {
  if (error instanceof Error) return error.message;
  if (typeof error === 'string') return error;
  return 'Something went wrong.';
};

const TREND_TITLES: Record<string, string> = {
  'top-performing-scorers': 'Top Performing Scorers',
  'latest-hat-tricks': 'Latest Hat-Trick Players',
  'strikers-with-a-lull': 'Strikers With A Lull',
};

interface CompetitionPickerState {
  competitions: CompetitionListItem[];
  competitionsLoading: boolean;
  competitionsError: string | null;
  selectedCompetition: CompetitionListItem | null;
  selectedCompetitionId: number | null;
  handleCompetitionChange: (competition: CompetitionListItem | null) => void;
}

const useCompetitionPicker = (): CompetitionPickerState => {
  const [competitions, setCompetitions] = useState<CompetitionListItem[]>([]);
  const [competitionsLoading, setCompetitionsLoading] = useState(true);
  const [competitionsError, setCompetitionsError] = useState<string | null>(null);
  const [selectedCompetitionId, setSelectedCompetitionId] = useState<number | null>(null);

  useEffect(() => {
    let active = true;

    const loadCompetitions = async () => {
      try {
        setCompetitionsLoading(true);
        setCompetitionsError(null);
        const items = await liveFootballApi.getCompetitions();
        if (!active) return;

        setCompetitions(items);
        setSelectedCompetitionId((currentId) => {
          if (currentId && items.some((item) => item.id === currentId)) {
            return currentId;
          }
          return items[0]?.id ?? null;
        });
      } catch (error) {
        if (!active) return;
        setCompetitions([]);
        setSelectedCompetitionId(null);
        setCompetitionsError(normalizeError(error));
      } finally {
        if (active) {
          setCompetitionsLoading(false);
        }
      }
    };

    void loadCompetitions();
    return () => {
      active = false;
    };
  }, []);

  const selectedCompetition = useMemo(
    () => competitions.find((competition) => competition.id === selectedCompetitionId) ?? null,
    [competitions, selectedCompetitionId],
  );

  return {
    competitions,
    competitionsLoading,
    competitionsError,
    selectedCompetition,
    selectedCompetitionId,
    handleCompetitionChange: (competition) => setSelectedCompetitionId(competition?.id ?? null),
  };
};

const playerProfileUrl = (player: PlayerLookupItem, season?: string | null): string | null => {
  const canonicalId = player.canonical_player?.id;
  if (!canonicalId) return null;

  const params = new URLSearchParams({ playerId: String(canonicalId) });
  if (season) params.set('season', season);
  return `/coaching/playerdata/player?${params.toString()}`;
};

const DirectoryShell = ({
  title,
  subtitle,
  picker,
  selectorHelper,
  children,
}: {
  title: string;
  subtitle: string;
  picker: CompetitionPickerState;
  selectorHelper: string;
  children: ReactNode;
}) => (
  <div className={styles.container}>
    <header className={styles.header}>
      <div>
        <h1 className={styles.title}>{title}</h1>
        <p className={styles.subtitle}>{subtitle}</p>
        <nav className={styles.navTabs} aria-label="Live football data views">
          <Link className={styles.navTab} to="/livefootball/browse">Browse</Link>
          <Link className={styles.navTab} to="/livefootball/matches">Matches</Link>
          <Link className={styles.navTab} to="/livefootball/clubs">Clubs</Link>
          <Link className={styles.navTab} to="/livefootball/players">Players</Link>
          <Link className={styles.navTab} to="/livefootball/leagues">League Tools</Link>
        </nav>
      </div>

      <CompetitionSelector
        competitions={picker.competitions}
        value={picker.selectedCompetitionId}
        onChange={picker.handleCompetitionChange}
        loading={picker.competitionsLoading}
        error={picker.competitionsError}
        helperText={selectorHelper}
        emptyStateText="No competitions are available yet."
        className={styles.selectorCard}
      />
    </header>

    {!picker.competitionsLoading && !picker.competitionsError && picker.competitions.length === 0 ? (
      <section className={styles.emptyState}>
        <h2 className={styles.sectionTitle}>No competition data yet</h2>
        <p>Sync football-data into the backend, then refresh this page.</p>
      </section>
    ) : null}

    {children}
  </div>
);

export const LiveFootballMatchesPage = () => {
  const picker = useCompetitionPicker();
  const [fixtures, setFixtures] = useState<CompetitionPreviousNextFixturesResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const competition = picker.selectedCompetition;
    if (!competition) {
      setFixtures(null);
      setError(null);
      return;
    }

    let active = true;
    const loadFixtures = async () => {
      try {
        setLoading(true);
        setError(null);
        const result = await liveFootballApi.getCompetitionPreviousNextFixtures(competition.id, {
          season: competition.current_season_label || undefined,
          previous_limit: 12,
          next_limit: 12,
        });
        if (active) setFixtures(result);
      } catch (loadError) {
        if (active) {
          setFixtures(null);
          setError(normalizeError(loadError));
        }
      } finally {
        if (active) setLoading(false);
      }
    };

    void loadFixtures();
    return () => {
      active = false;
    };
  }, [picker.selectedCompetition]);

  return (
    <DirectoryShell
      title="Live Matches"
      subtitle="Recent results and upcoming fixtures from the livefootball sync pipeline."
      picker={picker}
      selectorHelper="Choose a competition to view the latest synced fixtures."
    >
      <FixturesPanel
        fixtures={fixtures}
        isLoading={loading}
        error={error}
        title="Competition fixtures"
        previousTitle="Recent results"
        nextTitle="Upcoming fixtures"
        className={styles.panel}
      />
    </DirectoryShell>
  );
};

export const LiveFootballClubsPage = () => {
  const picker = useCompetitionPicker();
  const [teams, setTeams] = useState<TeamLookupItem[]>([]);
  const [seasonLabel, setSeasonLabel] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const competition = picker.selectedCompetition;
    if (!competition) {
      setTeams([]);
      setSeasonLabel('');
      setError(null);
      return;
    }

    let active = true;
    const loadTeams = async () => {
      try {
        setLoading(true);
        setError(null);
        const result = await liveFootballApi.getCompetitionTeams(competition.id, {
          season: competition.current_season_label || undefined,
        });
        if (!active) return;
        setTeams(result.items);
        setSeasonLabel(result.season_label);
      } catch (loadError) {
        if (active) {
          setTeams([]);
          setSeasonLabel('');
          setError(normalizeError(loadError));
        }
      } finally {
        if (active) setLoading(false);
      }
    };

    void loadTeams();
    return () => {
      active = false;
    };
  }, [picker.selectedCompetition]);

  return (
    <DirectoryShell
      title="Live Clubs"
      subtitle="Club and squad directory data populated from football-data collection."
      picker={picker}
      selectorHelper="Choose a competition to view its latest synced clubs."
    >
      <section className={styles.panel}>
        <div className={styles.panelHeader}>
          <h2 className={styles.sectionTitle}>Clubs</h2>
          <p className={styles.metaText}>
            {picker.selectedCompetition?.name ?? 'Select a competition'}
            {seasonLabel ? ` · ${seasonLabel}` : ''}
          </p>
        </div>

        {loading ? <div className={styles.stateText}>Loading clubs...</div> : null}
        {!loading && error ? <div className={styles.errorText}>{error}</div> : null}
        {!loading && !error && teams.length === 0 ? (
          <div className={styles.stateText}>No clubs are available for this competition yet.</div>
        ) : null}

        {!loading && !error && teams.length > 0 ? (
          <div className={styles.cardGrid}>
            {teams.map((team) => (
              <article key={team.id} className={styles.directoryCard}>
                <div className={styles.cardHeader}>
                  {team.emblem_url ? (
                    <img className={styles.crest} src={team.emblem_url} alt="" />
                  ) : (
                    <span className={styles.crestPlaceholder}>{team.tla || team.name.slice(0, 2)}</span>
                  )}
                  <div>
                    <h3 className={styles.cardTitle}>{team.name}</h3>
                    <p className={styles.cardMeta}>
                      {[team.area_name, team.venue].filter(Boolean).join(' · ') || 'Club details'}
                    </p>
                  </div>
                </div>
                <div className={styles.cardActions}>
                  <Link className={styles.inlineAction} to={`/squad/${encodeURIComponent(team.name)}`}>
                    Squad intelligence
                  </Link>
                </div>
              </article>
            ))}
          </div>
        ) : null}
      </section>
    </DirectoryShell>
  );
};

export const LiveFootballPlayersPage = () => {
  const picker = useCompetitionPicker();
  const [searchParams] = useSearchParams();
  const [search, setSearch] = useState('');
  const [players, setPlayers] = useState<PlayerLookupItem[]>([]);
  const [scorers, setScorers] = useState<CompetitionTopScorerItem[]>([]);
  const [seasonLabel, setSeasonLabel] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const trend = searchParams.get('trend') ?? '';
  const pageTitle = TREND_TITLES[trend] ?? 'Live Players';

  useEffect(() => {
    const competition = picker.selectedCompetition;
    if (!competition) {
      setPlayers([]);
      setScorers([]);
      setSeasonLabel('');
      setError(null);
      return;
    }

    let active = true;
    const loadPlayers = async () => {
      try {
        setLoading(true);
        setError(null);
        const season = competition.current_season_label || undefined;
        const [playersResult, scorersResult] = await Promise.all([
          search.trim()
            ? liveFootballApi.searchPlayers({
                q: search.trim(),
                competition_id: competition.id,
                season,
                active_only: true,
                limit: 80,
              })
            : liveFootballApi.getCompetitionPlayers(competition.id, {
                season,
                active_only: true,
              }),
          liveFootballApi.getCompetitionScorers(competition.id, {
            season,
            limit: 12,
          }),
        ]);

        if (!active) return;
        setPlayers(playersResult.items);
        setScorers(scorersResult.items);
        setSeasonLabel('season_label' in playersResult ? playersResult.season_label : scorersResult.season_label);
      } catch (loadError) {
        if (active) {
          setPlayers([]);
          setScorers([]);
          setSeasonLabel('');
          setError(normalizeError(loadError));
        }
      } finally {
        if (active) setLoading(false);
      }
    };

    void loadPlayers();
    return () => {
      active = false;
    };
  }, [picker.selectedCompetition, search]);

  return (
    <DirectoryShell
      title={pageTitle}
      subtitle="Player directory, scorer leaders, and links into the internal playerdata profile view."
      picker={picker}
      selectorHelper="Choose a competition to view synced player and scorer data."
    >
      <section className={styles.panel}>
        <div className={styles.panelHeader}>
          <div>
            <h2 className={styles.sectionTitle}>Player Directory</h2>
            <p className={styles.metaText}>
              {picker.selectedCompetition?.name ?? 'Select a competition'}
              {seasonLabel ? ` · ${seasonLabel}` : ''}
            </p>
          </div>
          <input
            className={styles.searchInput}
            type="search"
            placeholder="Search players or teams"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>

        {scorers.length > 0 ? (
          <div className={styles.scorerStrip}>
            {scorers.map((scorer) => (
              <div key={`${scorer.external_player_id}-${scorer.rank}`} className={styles.scorerPill}>
                <strong>{scorer.rank}. {scorer.player_name}</strong>
                <span>{scorer.goals} goals · {scorer.team.short_name || scorer.team.name}</span>
              </div>
            ))}
          </div>
        ) : null}

        {loading ? <div className={styles.stateText}>Loading players...</div> : null}
        {!loading && error ? <div className={styles.errorText}>{error}</div> : null}
        {!loading && !error && players.length === 0 ? (
          <div className={styles.stateText}>No players are available for this selection yet.</div>
        ) : null}

        {!loading && !error && players.length > 0 ? (
          <div className={styles.cardGrid}>
            {players.map((player) => {
              const profileUrl = playerProfileUrl(player, seasonLabel);
              return (
                <article key={player.id} className={styles.directoryCard}>
                  <div>
                    <h3 className={styles.cardTitle}>{player.player_name}</h3>
                    <p className={styles.cardMeta}>
                      {[
                        player.primary_position || player.raw_position,
                        player.nationality,
                        player.team?.name,
                      ].filter(Boolean).join(' · ') || 'Player details'}
                    </p>
                  </div>
                  <div className={styles.cardFooter}>
                    {player.squad_number ? (
                      <span className={styles.badge}>#{player.squad_number}</span>
                    ) : null}
                    {profileUrl ? (
                      <Link className={styles.inlineAction} to={profileUrl}>
                        Player profile
                      </Link>
                    ) : (
                      <span className={styles.mutedText}>No canonical profile yet</span>
                    )}
                  </div>
                </article>
              );
            })}
          </div>
        ) : null}
      </section>
    </DirectoryShell>
  );
};

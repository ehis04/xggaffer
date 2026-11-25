import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { FreshnessBadge } from '../../common/components/FreshnessBadge';
import { SectionSkeleton } from '../../common/components/SectionSkeleton';
import { InlineRetry } from '../../common/components/InlineRetry';
import DegradedBanner from '../../components/widgets/DegradedBanner';
import NullStatePlaceholder from '../../components/widgets/NullStatePlaceholder';
import CalibrationFactorsPlot from '../../components/widgets/CalibrationFactorsPlot';
import BiggestMissesPanel from '../../components/widgets/BiggestMissesPanel';
import ConfidenceAccuracyChart from '../../components/widgets/ConfidenceAccuracyChart';
import { fetchModelTrustWidget } from '../../services/api/widgetApi';
import type { ModelTrustWidgetPayload } from '../../services/api/widgetApi';
import {
  formatSeasonDisplay,
  getCurrentFootballSeason,
  PREDICTION_LEAGUE_OPTIONS,
} from '../../utils/footballSeason';
import styles from './css/ModelTrustCentre.module.css';
import { Sidebar } from '../../components/Navigation/SideBar';
import { SocialUserButtons } from '../../components/Social/SocialUserButtons';
import { PredictionsNavbar } from '../../components/Navigation/predictionsNavbar';

const DEFAULT_LEAGUE_FILTER = '';

const LEAGUE_OPTIONS = [
  { value: '', label: 'All leagues' },
  ...PREDICTION_LEAGUE_OPTIONS.map((option) => ({
    value: option.value,
    label: option.label,
  })),
] as const;

function resolveLeagueFilterFromUrl(searchParams: URLSearchParams): string {
  const rawLeague = searchParams.get('league') ?? DEFAULT_LEAGUE_FILTER;
  const isValidLeague = LEAGUE_OPTIONS.some(option => option.value === rawLeague);
  return isValidLeague ? rawLeague : DEFAULT_LEAGUE_FILTER;
}

export default function ModelTrustCentre() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [leagueFilter, setLeagueFilter] = useState(() => resolveLeagueFilterFromUrl(searchParams));
  const [payload, setPayload] = useState<ModelTrustWidgetPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [retrying, setRetrying] = useState(false);

  useEffect(() => {
    const nextLeague = resolveLeagueFilterFromUrl(searchParams);
    setLeagueFilter(current => (current === nextLeague ? current : nextLeague));
  }, [searchParams]);

  async function loadData(league: string, isRetry = false) {
    if (isRetry) setRetrying(true);
    else setLoading(true);
    setError(false);
    try {
      const response = await fetchModelTrustWidget(league || undefined);
      setPayload(response);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
      setRetrying(false);
    }
  }

  useEffect(() => {
    loadData(leagueFilter);
  }, [leagueFilter]);

  const handleLeagueChange = (nextLeague: string) => {
    setLeagueFilter(nextLeague);

    const nextParams = new URLSearchParams(searchParams);
    if (nextLeague) {
      nextParams.set('league', nextLeague);
    } else {
      nextParams.delete('league');
    }
    setSearchParams(nextParams, { replace: true });
  };

  const trustData = payload?.data ?? null;
  const freshness = payload?.freshness ?? null;
  const selectedLeagueLabel = LEAGUE_OPTIONS.find(option => option.value === leagueFilter)?.label;
  const seasonLabel = formatSeasonDisplay(
    (payload?.summary?.season as string | undefined) ?? getCurrentFootballSeason(),
  );
  const coldStartNote = (payload?.summary?.cold_start_note as string | undefined)
    ?? 'Prediction review data will appear once match results are logged.';

  return (
    <div className={styles.page}>
      <div className={styles.Sidebar}>
        <Sidebar />
      </div>

      <div className={styles.base}>
        <header className={styles.Header}>
          <div className={styles.Left}>Model Trust Centre</div>
          <div className={styles.Middle}><PredictionsNavbar /></div>
          <div className={styles.Right}>
            <SocialUserButtons />
          </div>
        </header>

      <header className={styles.header}>
        <div className={styles.headerCopy}>
          <p className={styles.kicker}>Prediction Intelligence</p>
          <h1 className={styles.title}>Model Trust Centre</h1>
          <p className={styles.subtitle}>How accurately xgGaffer predicts match outcomes</p>
        </div>
        {freshness && <FreshnessBadge freshness={freshness} />}
      </header>

      <div className={styles.filterBar}>
        <label className={styles.filterLabel} htmlFor="league-filter">
          League
        </label>
        <select
          id="league-filter"
          className={styles.select}
          value={leagueFilter}
          onChange={e => handleLeagueChange(e.target.value)}
        >
          {LEAGUE_OPTIONS.map(opt => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      </div>

      {loading && (
        <div className={styles.stateBlock}>
          <SectionSkeleton rows={5} />
        </div>
      )}

      {!loading && error && (
        <div className={styles.stateBlock}>
          <InlineRetry
            message="Failed to load model trust data."
            onRetry={() => loadData(leagueFilter, true)}
            retrying={retrying}
          />
        </div>
      )}

      {!loading && !error && !trustData && (
        <div className={styles.stateBlock}>
          <NullStatePlaceholder
            icon="chart"
            message={coldStartNote}
          />
        </div>
      )}

      {!loading && !error && trustData && (
        <div className={styles.content}>
          {freshness?.cascade_degraded && freshness.cascade_reason && (
            <DegradedBanner reason={freshness.cascade_reason} cascade />
          )}

          <div className={styles.topRow}>
            <section className={styles.accuracyBlock}>
              <div className={styles.sectionHeader}>
                <p className={styles.sectionLabel}>Overall Accuracy</p>
              </div>
              <span className={styles.accuracyNumber}>
                {(trustData.overall_accuracy * 100).toFixed(1)}%
              </span>
              <span className={styles.accuracySubLabel}>
                across {trustData.total_resolved} resolved predictions
              </span>
            </section>

            <div className={styles.recentFormChip}>
              <p className={styles.sectionLabel}>Recent Form</p>
              <p className={styles.recentFormValue}>
                Last {trustData.recent_form.count} predictions:{' '}
                <strong>{(trustData.recent_form.accuracy * 100).toFixed(1)}% accuracy</strong>
              </p>
            </div>
          </div>

          <section className={styles.section}>
            <div className={styles.sectionHeader}>
              <h2 className={styles.sectionTitle}>Calibration factors plot</h2>
              <p className={styles.sectionMeta}>Accuracy, confidence, brier score, and log loss across random, market, and model</p>
            </div>
            <CalibrationFactorsPlot plot={trustData.calibration_factor_plot} />
          </section>

          <section className={styles.section}>
            <div className={styles.sectionHeader}>
              <h2 className={styles.sectionTitle}>
                {leagueFilter && selectedLeagueLabel
                  ? `${selectedLeagueLabel} Accuracy`
                  : 'Accuracy by league'}
              </h2>
              <p className={styles.sectionMeta}>Sorted highest to lowest</p>
            </div>
            <div className={styles.tableWrapper}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th className={styles.th}>{seasonLabel} Season</th>
                    <th className={styles.th}>Predictions</th>
                    <th className={styles.th}>Accuracy</th>
                  </tr>
                </thead>
                <tbody>
                  {[...trustData.accuracy_by_league]
                    .sort((a, b) => b.accuracy - a.accuracy)
                    .map(row => (
                      <tr key={row.league_code} className={styles.tr}>
                        <td className={styles.td}>{row.league_code}</td>
                        <td className={styles.td}>{row.total}</td>
                        <td className={styles.td}>{(row.accuracy * 100).toFixed(1)}%</td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className={styles.section}>
            <div className={styles.sectionHeader}>
              <h2 className={styles.sectionTitle}>High-confidence hits</h2>
              <p className={styles.sectionMeta}>Matches where the model called it correctly with high confidence</p>
            </div>
            <BiggestMissesPanel items={trustData.biggest_hits} variant="hit" />
          </section>

          <section className={styles.section}>
            <div className={styles.sectionHeader}>
              <h2 className={styles.sectionTitle}>High-confidence misses</h2>
              <p className={styles.sectionMeta}>Matches where confidence and outcome diverged</p>
            </div>
            <BiggestMissesPanel items={trustData.biggest_misses} variant="miss" />
          </section>

          <section className={styles.section}>
            <div className={styles.sectionHeader}>
              <h2 className={styles.sectionTitle}>Does confidence predict accuracy?</h2>
              <p className={styles.sectionMeta}>Higher model confidence should correlate with higher accuracy</p>
              <p className={styles.sectionMeta}>n = number of resolved predictions in each confidence bucket (how many finished predictions fall into each confidence range).</p>
              <p className={styles.sectionMeta}>Interpretation guide: random is the neutral baseline; market and model lines show how each profile changes across factors.</p>
              <p className={styles.sectionMeta}>For error metrics (brier score and log loss), lower values indicate better calibration quality.</p>
            </div>
            <ConfidenceAccuracyChart
              buckets={trustData.confidence_distribution}
              overallAccuracy={trustData.overall_accuracy}
              marketAccuracy={trustData.market_comparison.market_accuracy}
            />
          </section>
        </div>
      )}
      </div>
    </div>
  );
}

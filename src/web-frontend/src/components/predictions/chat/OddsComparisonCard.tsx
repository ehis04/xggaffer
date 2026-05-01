import type { OddsComparisonEngineData } from '../../../types/prediction';
import styles from './css/OddsComparisonCard.module.css';
import ProbabilityBar from '../../../common/ProbabilityBar';

interface OddsComparisonCardProps {
  engineData: OddsComparisonEngineData;
  partial: boolean;
  error: string | null;
}

const formatBenchmarkSampleSize = (value: number): string => `${value} rows`;

const formatPercentage = (value: number): string => `${Math.round(value * 100)}%`;

const formatEdgePoints = (value: number): string => `${value.toFixed(1)} pts`;

const formatOverround = (value: number): string => {
  if (value > 1) {
    return `${((value - 1) * 100).toFixed(1)}% margin`;
  }
  return `${(value * 100).toFixed(1)}%`;
};

const formatKickoff = (value: string | null): string | null => {
  if (!value) return null;

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return parsed.toLocaleString('en-IE', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  });
};

const formatLastSeen = (value: string | null): string | null => {
  if (!value) return null;

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return parsed.toLocaleString('en-IE', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  });
};

export default function OddsComparisonCard({
  engineData,
  partial,
  error,
}: OddsComparisonCardProps) {
  const kickoffLabel = formatKickoff(engineData.kickoff);
  const benchmark = engineData.benchmark;

  return (
    <div className={styles.card}>
      {partial && (
        <div className={styles.partialNote}>
          Odds data is partially available, so some sections may still be pending.
        </div>
      )}

      {error && (
        <div className={styles.errorNote}>
          {error}
        </div>
      )}

      <div className={styles.header}>
        <h3 className={styles.fixtureTitle}>
          {engineData.home_team} vs {engineData.away_team}
        </h3>
        <div className={styles.meta}>
          <span className={styles.metaItem}>
            {engineData.league} · {engineData.season}
          </span>
          {kickoffLabel && (
            <span className={styles.metaItem}>
              Kick-off: {kickoffLabel}
            </span>
          )}
        </div>
      </div>
  
      <section className={styles.section}>
        <h4 className={styles.sectionTitle}>Market consensus</h4>
        <ProbabilityBar
            label="Market consensus"
            probabilities={{
            home: engineData.market.devig_home,
            draw: engineData.market.devig_draw,
            away: engineData.market.devig_away,
            }}
        />
        <p className={styles.sectionMeta}>
            Favourite: <strong>{engineData.market.favourite}</strong> · Overround: <strong>{formatOverround(engineData.market.overround)}</strong> · {engineData.market.source_label}
        </p>
      </section>
      <section className={styles.section}>
        <h4 className={styles.sectionTitle}>xgGaffer model</h4>
        <ProbabilityBar
          label="Model probabilities"
          probabilities={{
            home: engineData.model.probabilities.home,
            draw: engineData.model.probabilities.draw,
            away: engineData.model.probabilities.away,
          }}
        />
        <p className={styles.sectionMeta}>
          Prediction: <strong>{engineData.model.prediction}</strong> · Model:{' '}
          <strong>{engineData.model.model_type}</strong> · Version:{' '}
          <strong>{engineData.model.version}</strong>
        </p>
      </section>


      <section className={styles.section}>
        <h4 className={styles.sectionTitle}>Comparison summary</h4>
        <div className={styles.summaryBox}>
          <span
            className={`${styles.statusBadge} ${
              engineData.comparison.agreement ? styles.statusAgree : styles.statusDisagree
            }`}
          >
            {engineData.comparison.agreement ? 'Agreement' : 'Disagreement'}
          </span>
          <p className={styles.summaryText}>{engineData.comparison.summary}</p>
          <div className={styles.comparisonGrid}>
            <div className={styles.comparisonItem}>
              <span className={styles.comparisonLabel}>Model favourite</span>
              <span className={styles.comparisonValue}>{engineData.comparison.model_favourite}</span>
            </div>
            <div className={styles.comparisonItem}>
              <span className={styles.comparisonLabel}>Market favourite</span>
              <span className={styles.comparisonValue}>{engineData.comparison.market_favourite}</span>
            </div>
            <div className={styles.comparisonItem}>
              <span className={styles.comparisonLabel}>Largest model-market gap</span>
              <span className={styles.comparisonValue}>{engineData.comparison.biggest_edge_side}</span>
            </div>
            <div className={styles.comparisonItem}>
              <span className={styles.comparisonLabel}>Gap size</span>
              <span className={styles.comparisonValue}>
                {formatEdgePoints(engineData.comparison.biggest_edge_points)}
              </span>
            </div>
          </div>
        </div>
      </section>

      <section className={styles.section}>
        <h4 className={styles.sectionTitle}>Bookmaker odds</h4>
        {engineData.bookmakers.length === 0 ? (
          <p className={styles.fallbackText}>No bookmaker rows available yet.</p>
        ) : (
          <div className={styles.bookmakerTable}>
            <div className={`${styles.bookmakerRow} ${styles.bookmakerHeader}`}>
              <span>Bookmaker</span>
              <span>Home</span>
              <span>Draw</span>
              <span>Away</span>
            </div>

            {engineData.bookmakers.map((quote) => {
              const lastSeen = formatLastSeen(quote.last_seen_at);

              return (
                <div key={`${quote.bookmaker}-${quote.last_seen_at ?? 'latest'}`} className={styles.bookmakerCard}>
                  <div className={styles.bookmakerRow}>
                    <span className={styles.bookmakerName}>{quote.bookmaker}</span>
                    <span className={styles.bookmakerOdds}>{quote.home_odds.toFixed(2)}</span>
                    <span className={styles.bookmakerOdds}>{quote.draw_odds.toFixed(2)}</span>
                    <span className={styles.bookmakerOdds}>{quote.away_odds.toFixed(2)}</span>
                  </div>
                  {lastSeen && (
                    <p className={styles.bookmakerMeta}>Last seen: {lastSeen}</p>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </section>

      <section className={`${styles.section} ${styles.benchmarkSection}`}>
        <div className={styles.benchmarkHeader}>
          <h4 className={styles.sectionTitle}>Historical benchmark</h4>
          <p className={styles.benchmarkCaption}>
            Model context from the engine 4 evaluation set
          </p>
        </div>

        {!benchmark ? (
          <div className={styles.benchmarkFallback}>
            <p className={styles.fallbackText}>
              Benchmark unavailable for this response.
            </p>
          </div>
        ) : (
          <>
            {(benchmark.source_label || benchmark.evaluation_scope) && (
              <p className={styles.benchmarkMeta}>
                {benchmark.source_label ? `Source: ${benchmark.source_label}` : ''}
                {benchmark.source_label && benchmark.evaluation_scope ? ' • ' : ''}
                {benchmark.evaluation_scope ? benchmark.evaluation_scope : ''}
              </p>
            )}

            <div className={styles.benchmarkSurface}>
              <div className={styles.benchmarkStrip}>
                <div className={styles.benchmarkItem}>
                  <span className={styles.benchmarkLabel}>Sample size</span>
                  <span className={styles.benchmarkValue}>
                    {formatBenchmarkSampleSize(benchmark.sample_size)}
                  </span>
                </div>

                <div className={styles.benchmarkItem}>
                  <span className={styles.benchmarkLabel}>
                    Model accuracy on benchmark sample
                  </span>
                  <span className={styles.benchmarkValue}>
                    {formatPercentage(benchmark.model_accuracy)}
                  </span>
                </div>

                <div className={styles.benchmarkItem}>
                  <span className={styles.benchmarkLabel}>
                    Market favourite accuracy on benchmark sample
                  </span>
                  <span
                    className={`${styles.benchmarkValue} ${
                      benchmark.market_favourite_accuracy === null ? styles.benchmarkPending : ''
                    }`}
                  >
                    {benchmark.market_favourite_accuracy === null
                      ? 'Data pending'
                      : formatPercentage(benchmark.market_favourite_accuracy)}
                  </span>
                </div>

                <div className={styles.benchmarkItem}>
                  <span className={styles.benchmarkLabel}>Source</span>
                  <span className={styles.benchmarkValue}>{benchmark.source_label}</span>
                </div>
              </div>
            </div>
          </>
        )}
      </section>

      <section className={styles.wellbeingBlock}>
        <div className={styles.wellbeingHeader}>
          <h4 className={styles.wellbeingTitle}>Support and wellbeing</h4>
          <p className={styles.wellbeingWarning}>{engineData.support.warning}</p>
        </div>

        <div className={styles.wellbeingResources}>
          <span className={styles.wellbeingResourcesLabel}>Support services</span>

          <div className={styles.wellbeingList}>
            {engineData.support.resources.map((resource) => (
              <div
                key={`${resource.label}-${resource.region}-${resource.support_type}`}
                className={styles.wellbeingResource}
              >
                <span className={styles.resourceLabel}>{resource.label}</span>
                <span className={styles.resourceMeta}>
                  {resource.region} · {resource.support_type}
                </span>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
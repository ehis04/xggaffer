import React, { useMemo, useState } from 'react';
import type {
  PlayerDataFilters,
  PlayerDataMetric,
  PlayerSeasonSummary,
} from '../../types/playerdata';
import InsightResponseBlock, {
  type InsightResponseBlockData,
} from './InsightResponseBlock';
import SupportedInsightChips from './SupportedInsightChips';
import {
  DEFAULT_SUPPORTED_INSIGHT_OPTIONS,
  type SupportedInsightIntent,
} from './SupportedInsightChips.types';

interface CompareNavigationContext {
  fromClubId?: number | null;
  clubPlayerId?: number | null;
  returnToPlayerId?: number | null;
}

interface PlayerInsightQueryPanelProps {
  playerId: number | null;
  summary: PlayerSeasonSummary | null;
  filters?: PlayerDataFilters;
  isLoading?: boolean;
  error?: string | null;
  compareBasePath?: string;
  compareNavigationContext?: CompareNavigationContext;
  className?: string;
}

const panelStyle: React.CSSProperties = {
  border: '1px solid rgba(255,255,255,0.12)',
  borderRadius: '16px',
  padding: '1rem',
  background: 'rgba(255,255,255,0.02)',
};

const headerRowStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'flex-start',
  gap: '1rem',
  flexWrap: 'wrap',
};

const badgeStyle: React.CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  borderRadius: '999px',
  padding: '0.28rem 0.65rem',
  fontSize: '0.78rem',
  border: '1px solid rgba(255,255,255,0.14)',
  background: 'rgba(255,255,255,0.04)',
};

const inputRowStyle: React.CSSProperties = {
  display: 'flex',
  gap: '0.75rem',
  flexWrap: 'wrap',
  alignItems: 'flex-end',
  marginTop: '0.9rem',
};

const inputStyle: React.CSSProperties = {
  minWidth: '220px',
  padding: '0.65rem 0.8rem',
  borderRadius: '10px',
  border: '1px solid rgba(255,255,255,0.14)',
  background: 'rgba(255,255,255,0.03)',
  color: 'inherit',
};

const parsePositiveInt = (value: string): number | null => {
  const trimmed = value.trim();

  if (!trimmed) {
    return null;
  }

  const parsed = Number(trimmed);

  if (!Number.isInteger(parsed) || parsed <= 0) {
    return null;
  }

  return parsed;
};

const compactSpaces = (value: string): string => value.replace(/\s+/g, ' ').trim();

const normalise = (value: string | null | undefined): string =>
  compactSpaces((value ?? '').toLowerCase().replace(/[_-]/g, ' '));

const formatMetricValue = (metric?: PlayerDataMetric | null): string | null => {
  if (!metric) {
    return null;
  }

  if (metric.formatted_value) {
    return metric.formatted_value;
  }

  if (metric.value === null || metric.value === undefined) {
    return null;
  }

  if (metric.unit) {
    return `${metric.value}${metric.unit}`;
  }

  return String(metric.value);
};

const findMetric = (
  metrics: PlayerDataMetric[] | undefined,
  aliases: string[]
): PlayerDataMetric | undefined => {
  if (!metrics?.length) {
    return undefined;
  }

  const aliasSet = new Set(aliases.map(normalise));

  return metrics.find((metric) => {
    const key = normalise(metric.key);
    const label = normalise(metric.label);
    return aliasSet.has(key) || aliasSet.has(label);
  });
};

const findAnyMetric = (
  metrics: PlayerDataMetric[] | undefined,
  aliasGroups: string[][]
): PlayerDataMetric | undefined => {
  for (const aliases of aliasGroups) {
    const found = findMetric(metrics, aliases);
    if (found) {
      return found;
    }
  }

  return undefined;
};

const metricLine = (
  metrics: PlayerDataMetric[] | undefined,
  aliases: string[][],
  fallbackLabel: string
): string | null => {
  const metric = findAnyMetric(metrics, aliases);
  const value = formatMetricValue(metric);

  if (!metric || !value) {
    return null;
  }

  return `${metric.label || fallbackLabel}: ${value}`;
};

const buildCompareUrl = (
  playerId: number,
  compareTargetId: number,
  filters: PlayerDataFilters | undefined,
  compareBasePath: string,
  navigationContext?: CompareNavigationContext
): string => {
  const params = new URLSearchParams({
    player_a_id: String(playerId),
    player_b_id: String(compareTargetId),
  });

  if (filters?.season) {
    params.set('season', filters.season);
  }

  if (filters?.provider) {
    params.set('provider', filters.provider);
  }

  if (filters?.competition_code) {
    params.set('competition_code', filters.competition_code);
  }

  if (filters?.competition_name) {
    params.set('competition_name', filters.competition_name);
  }

  if (
    navigationContext?.fromClubId &&
    Number.isInteger(navigationContext.fromClubId) &&
    navigationContext.fromClubId > 0
  ) {
    params.set('fromClubId', String(navigationContext.fromClubId));
  }

  if (
    navigationContext?.clubPlayerId &&
    Number.isInteger(navigationContext.clubPlayerId) &&
    navigationContext.clubPlayerId > 0
  ) {
    params.set('clubPlayerId', String(navigationContext.clubPlayerId));
  }

  if (
    navigationContext?.returnToPlayerId &&
    Number.isInteger(navigationContext.returnToPlayerId) &&
    navigationContext.returnToPlayerId > 0
  ) {
    params.set('returnToPlayerId', String(navigationContext.returnToPlayerId));
  }

  return `${compareBasePath}?${params.toString()}`;
};

const buildContextMeta = (summary: PlayerSeasonSummary | null): string[] => {
  if (!summary) {
    return [];
  }

  const meta: string[] = [];

  if (summary.context?.season) {
    meta.push(`Season: ${summary.context.season}`);
  }

  if (summary.context?.competition_name) {
    meta.push(`Competition: ${summary.context.competition_name}`);
  } else if (summary.context?.competition_code) {
    meta.push(`Competition: ${summary.context.competition_code}`);
  }

  if (summary.provider_coverage?.provider || summary.context?.provider) {
    meta.push(
      `Provider: ${summary.provider_coverage?.provider || summary.context?.provider}`
    );
  }

  return meta;
};

const buildUnavailableResponse = (message: string): InsightResponseBlockData => ({
  title: 'Insight unavailable',
  body: message,
  bullets: [],
  meta: [],
  isUnavailable: true,
});

const buildSeasonSummaryResponse = (
  summary: PlayerSeasonSummary
): InsightResponseBlockData => {
  const bullets: string[] = [];

  if (summary.explanation?.headline) {
    bullets.push(summary.explanation.headline);
  }

  if (summary.explanation?.strengths?.length) {
    bullets.push(...summary.explanation.strengths.slice(0, 3));
  }

  if (!bullets.length && summary.metrics?.length) {
    summary.metrics
      .filter((metric) => metric.is_available !== false)
      .slice(0, 3)
      .forEach((metric) => {
        const value = formatMetricValue(metric);
        if (value) {
          bullets.push(`${metric.label}: ${value}`);
        }
      });
  }

  return {
    title: 'Season summary',
    body:
      summary.explanation?.summary ||
      'This player has a deterministic season summary based on stored playerdata metrics.',
    bullets,
    meta: buildContextMeta(summary),
  };
};

const buildAttackingOutputResponse = (
  summary: PlayerSeasonSummary
): InsightResponseBlockData => {
  const bullets = [
    metricLine(summary.metrics, [['goals', 'goal']], 'Goals'),
    metricLine(
      summary.metrics,
      [['expected goals', 'xg', 'non penalty xg', 'npxg']],
      'Expected goals'
    ),
    metricLine(summary.metrics, [['assists', 'assist']], 'Assists'),
    metricLine(summary.metrics, [['expected assists', 'xa', 'xA']], 'Expected assists'),
    metricLine(summary.metrics, [['shots', 'shots total', 'total shots']], 'Shots'),
    metricLine(summary.metrics, [['shots on target', 'sot']], 'Shots on target'),
  ].filter((line): line is string => Boolean(line));

  return {
    title: 'Attacking output',
    body:
      bullets.length > 0
        ? 'This attacking snapshot is derived directly from the stored season metrics available for this player.'
        : 'Attacking output is not available for this player with the current deterministic summary filters.',
    bullets,
    meta: buildContextMeta(summary),
    isUnavailable: bullets.length === 0,
  };
};

const buildMinutesUsageResponse = (
  summary: PlayerSeasonSummary
): InsightResponseBlockData => {
  const bullets = [
    metricLine(summary.metrics, [['minutes', 'minutes played']], 'Minutes'),
    metricLine(summary.metrics, [['appearances', 'matches played', 'games played']], 'Appearances'),
    metricLine(summary.metrics, [['starts', 'matches started', 'games started']], 'Starts'),
    metricLine(summary.metrics, [['sub appearances', 'substitute appearances']], 'Substitute appearances'),
  ].filter((line): line is string => Boolean(line));

  if (!bullets.length && summary.provider_coverage?.minutes_sampled) {
    bullets.push(`Minutes sampled: ${summary.provider_coverage.minutes_sampled}`);
  }

  return {
    title: 'Minutes / usage',
    body:
      bullets.length > 0
        ? 'This usage snapshot shows the workload and availability context exposed by the stored playerdata summary.'
        : 'Minutes and usage information is not available for this player with the current deterministic summary filters.',
    bullets,
    meta: buildContextMeta(summary),
    isUnavailable: bullets.length === 0,
  };
};

const buildCoverageResponse = (
  summary: PlayerSeasonSummary
): InsightResponseBlockData => {
  const coverage = summary.provider_coverage;

  if (!coverage) {
    return buildUnavailableResponse(
      'Provider coverage information is not available for this player summary yet.'
    );
  }

  const bullets = [
    coverage.coverage_status ? `Coverage status: ${coverage.coverage_status}` : null,
    coverage.matches_sampled !== null && coverage.matches_sampled !== undefined
      ? `Matches sampled: ${coverage.matches_sampled}`
      : null,
    coverage.minutes_sampled !== null && coverage.minutes_sampled !== undefined
      ? `Minutes sampled: ${coverage.minutes_sampled}`
      : null,
    ...(coverage.coverage_notes ?? []).slice(0, 3),
  ].filter((line): line is string => Boolean(line));

  return {
    title: 'Provider coverage',
    body:
      coverage.has_data === false
        ? 'The current provider coverage block says there is no usable data for this player under the selected filters.'
        : 'This coverage response describes what the stored provider-backed summary currently includes.',
    bullets,
    meta: buildContextMeta(summary),
  };
};

const buildFreshnessResponse = (
  summary: PlayerSeasonSummary
): InsightResponseBlockData => {
  const coverage = summary.provider_coverage;

  if (!coverage) {
    return buildUnavailableResponse(
      'Freshness cannot be explained because provider coverage metadata is missing.'
    );
  }

  const bullets = [
    coverage.freshness_label ? `Freshness: ${coverage.freshness_label}` : null,
    coverage.source_updated_at ? `Source updated at: ${coverage.source_updated_at}` : null,
    coverage.last_synced_at ? `Last synced at: ${coverage.last_synced_at}` : null,
  ].filter((line): line is string => Boolean(line));

  return {
    title: 'Freshness',
    body:
      bullets.length > 0
        ? 'This freshness response is based on the stored coverage timestamps attached to the player summary.'
        : 'Freshness metadata is not available for this player summary yet.',
    bullets,
    meta: buildContextMeta(summary),
    isUnavailable: bullets.length === 0,
  };
};

const buildComparisonResponse = (
  summary: PlayerSeasonSummary,
  playerId: number,
  compareTargetId: number | null,
  compareInput: string,
  filters: PlayerDataFilters | undefined,
  compareBasePath: string,
  compareNavigationContext?: CompareNavigationContext
): InsightResponseBlockData => {
  if (!compareInput.trim()) {
    return {
      title: 'Comparison hand-off',
      body: 'Enter another canonical player ID to launch a deterministic comparison from this player context.',
      bullets: [],
      meta: buildContextMeta(summary),
      isUnavailable: true,
    };
  }

  if (!compareTargetId) {
    return {
      title: 'Comparison hand-off',
      body: 'Enter a valid numeric player ID to open the comparison surface.',
      bullets: [],
      meta: buildContextMeta(summary),
      isUnavailable: true,
    };
  }

  if (compareTargetId === playerId) {
    return {
      title: 'Comparison hand-off',
      body: 'Choose a different player ID. Deterministic comparison requires two different players.',
      bullets: [],
      meta: buildContextMeta(summary),
      isUnavailable: true,
    };
  }

  return {
    title: 'Comparison hand-off',
    body: 'Open the internal comparison surface with the current season/provider context preserved.',
    bullets: [
      `Current player ID: ${playerId}`,
      `Comparison target ID: ${compareTargetId}`,
    ],
    meta: buildContextMeta(summary),
    action: {
      label: 'Open comparison page',
      to: buildCompareUrl(
        playerId,
        compareTargetId,
        filters,
        compareBasePath,
        compareNavigationContext
      ),
    },
  };
};

const buildInsightResponse = ({
  intent,
  playerId,
  summary,
  filters,
  compareInput,
  compareBasePath,
  compareNavigationContext,
  isLoading,
  error,
}: {
  intent: SupportedInsightIntent;
  playerId: number | null;
  summary: PlayerSeasonSummary | null;
  filters?: PlayerDataFilters;
  compareInput: string;
  compareBasePath: string;
  compareNavigationContext?: CompareNavigationContext;
  isLoading?: boolean;
  error?: string | null;
}): InsightResponseBlockData => {
  if (isLoading) {
    return buildUnavailableResponse(
      'The insight panel is waiting for the deterministic player summary to finish loading.'
    );
  }

  if (error) {
    return buildUnavailableResponse(
      `Insights are unavailable because the player summary could not be loaded: ${error}`
    );
  }

  if (!playerId) {
    return buildUnavailableResponse(
      'A valid canonical player ID is required before this insight panel can answer supported questions.'
    );
  }

  if (!summary) {
    return buildUnavailableResponse(
      'No deterministic player summary is available for the current player and filters.'
    );
  }

  switch (intent) {
    case 'season_summary':
      return buildSeasonSummaryResponse(summary);
    case 'attacking_output':
      return buildAttackingOutputResponse(summary);
    case 'minutes_usage':
      return buildMinutesUsageResponse(summary);
    case 'provider_coverage':
      return buildCoverageResponse(summary);
    case 'freshness':
      return buildFreshnessResponse(summary);
    case 'comparison_handoff':
      return buildComparisonResponse(
        summary,
        playerId,
        parsePositiveInt(compareInput),
        compareInput,
        filters,
        compareBasePath,
        compareNavigationContext
      );
    default:
      return buildUnavailableResponse('This insight intent is not supported yet.');
  }
};

const PlayerInsightQueryPanel: React.FC<PlayerInsightQueryPanelProps> = ({
  playerId,
  summary,
  filters,
  isLoading = false,
  error = null,
  compareBasePath = '/coaching/playerdata/compare',
  compareNavigationContext,
  className,
}) => {
  const [selectedIntent, setSelectedIntent] =
    useState<SupportedInsightIntent>('season_summary');
  const [compareInput, setCompareInput] = useState('');

  const response = useMemo(
    () =>
      buildInsightResponse({
        intent: selectedIntent,
        playerId,
        summary,
        filters,
        compareInput,
        compareBasePath,
        compareNavigationContext,
        isLoading,
        error,
      }),
    [
      selectedIntent,
      playerId,
      summary,
      filters,
      compareInput,
      compareBasePath,
      compareNavigationContext,
      isLoading,
      error,
    ]
  );

  const playerLabel =
    summary?.player?.display_name ||
    summary?.player?.full_name ||
    summary?.player?.short_name ||
    (playerId ? `Player ${playerId}` : 'Player');

  return (
    <section
      className={className}
      style={panelStyle}
      aria-labelledby="player-insight-query-panel-title"
    >
      <div style={headerRowStyle}>
        <div>
          <p style={{ margin: 0, opacity: 0.75, fontSize: '0.82rem' }}>
            Deterministic insight surface
          </p>
          <h2
            id="player-insight-query-panel-title"
            style={{ margin: '0.2rem 0 0 0', fontSize: '1.1rem' }}
          >
            Ask about this player
          </h2>
          <p style={{ margin: '0.45rem 0 0 0', opacity: 0.82 }}>
            Choose one of the supported questions for {playerLabel}. This panel only
            answers fixed intents backed by stored playerdata.
          </p>
        </div>

        <span style={badgeStyle}>No freeform chat</span>
      </div>

      <div style={{ marginTop: '0.9rem' }}>
        <SupportedInsightChips
          options={DEFAULT_SUPPORTED_INSIGHT_OPTIONS}
          selectedIntent={selectedIntent}
          onSelect={setSelectedIntent}
        />
      </div>

      {selectedIntent === 'comparison_handoff' && (
        <div style={inputRowStyle}>
          <label style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
            <span style={{ fontSize: '0.9rem', opacity: 0.88 }}>
              Compare to player ID
            </span>
            <input
              type="text"
              inputMode="numeric"
              value={compareInput}
              onChange={(event) => setCompareInput(event.target.value)}
              placeholder="Enter another canonical player ID"
              style={inputStyle}
            />
          </label>
        </div>
      )}

      <InsightResponseBlock
        response={response}
        emptyMessage="No deterministic insight response is available yet."
      />
    </section>
  );
};

export default PlayerInsightQueryPanel;
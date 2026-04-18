export type SupportedInsightIntent =
  | 'season_summary'
  | 'attacking_output'
  | 'minutes_usage'
  | 'provider_coverage'
  | 'freshness'
  | 'comparison_handoff';

export interface SupportedInsightOption {
  intent: SupportedInsightIntent;
  label: string;
  helperText?: string;
  disabled?: boolean;
}

export const DEFAULT_SUPPORTED_INSIGHT_OPTIONS: SupportedInsightOption[] = [
  {
    intent: 'season_summary',
    label: 'Season summary',
    helperText: 'Deterministic season overview from stored playerdata.',
  },
  {
    intent: 'attacking_output',
    label: 'Attacking output',
    helperText: 'Goals, xG, assists, shots and similar attacking metrics.',
  },
  {
    intent: 'minutes_usage',
    label: 'Minutes / usage',
    helperText: 'Minutes, appearances, starts and workload context.',
  },
  {
    intent: 'provider_coverage',
    label: 'Data coverage',
    helperText: 'What provider-backed summary data is currently available.',
  },
  {
    intent: 'freshness',
    label: 'Freshness',
    helperText: 'How recent the synced/stored summary data is.',
  },
  {
    intent: 'comparison_handoff',
    label: 'Compare player',
    helperText: 'Launch a deterministic player comparison hand-off.',
  },
];

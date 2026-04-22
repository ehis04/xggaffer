import type { FreshnessPayload } from './freshness';

export interface ApiEnvelope<T> {
  data: T | null;
  freshness: FreshnessPayload;
  version: string;
  warnings: string[];
  generated_at: string;
}

export interface DegradedEnvelope extends ApiEnvelope<null> {
  degraded: true;
}

export function isEnvelope<T>(value: unknown): value is ApiEnvelope<T> {
  return (
    typeof value === 'object' &&
    value !== null &&
    'data' in value &&
    'freshness' in value &&
    'version' in value
  );
}
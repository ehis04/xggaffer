export interface FreshnessPayload {
  source_fetched_at: string | null;
  snapshot_published_at: string | null;
  is_stale: boolean;
  is_degraded: boolean;
  stale_reason: string | null;
  sla_seconds: number;
}
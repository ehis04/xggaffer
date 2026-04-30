import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { FreshnessBadge } from '../../common/components/FreshnessBadge';
import { SectionSkeleton } from '../../common/components/SectionSkeleton';
import { InlineRetry } from '../../common/components/InlineRetry';
import NullStatePlaceholder from '../../components/widgets/NullStatePlaceholder';
import ZoneHeatmap from '../../components/widgets/ZoneHeatmap';
import StyleProfileCard from '../../components/widgets/StyleProfileCard';
import { fetchTacticalWidget } from '../../services/api/widgetApi';
import type { TacticalWidgetPayload } from '../../services/api/widgetApi';
import styles from './css/TacticalScoutingDashboard.module.css';

export default function TacticalScoutingDashboard() {
  const { teamSlug = '' } = useParams<{ teamSlug: string }>();
  const teamName = decodeURIComponent(teamSlug);

  const [payload, setPayload] = useState<TacticalWidgetPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [retrying, setRetrying] = useState(false);

  const loadData = async (team: string, isRetry = false) => {
    if (isRetry) setRetrying(true);
    else setLoading(true);
    setError(false);

    try {
      const envelope = await fetchTacticalWidget(team);
      setPayload(envelope.data);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
      setRetrying(false);
    }
  };

  useEffect(() => {
    void loadData(teamName);
  }, [teamName]);

  const tacticalData = payload?.data ?? null;
  const freshness = payload?.freshness ?? null;

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>{teamName}</h1>
        {freshness && <FreshnessBadge freshness={freshness} />}
      </header>

      {loading && <SectionSkeleton rows={4} />}

      {!loading && error && (
        <InlineRetry
          message="Failed to load tactical profile."
          onRetry={() => loadData(teamName, true)}
          retrying={retrying}
        />
      )}

      {!loading && !error && !tacticalData && (
        <NullStatePlaceholder
          icon="chart"
          message="No tactical profile available for this team."
        />
      )}

      {!loading && !error && tacticalData && (
        <div className={styles.content}>
          <StyleProfileCard styleCluster={tacticalData.style_cluster} />
          <ZoneHeatmap zoneProfiles={tacticalData.zone_profiles} team={teamName} />
        </div>
      )}
    </div>
  );
}
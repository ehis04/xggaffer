import { useState } from 'react';
import NullStatePlaceholder from './NullStatePlaceholder';
import type { TeamProjection, WhatIfAdjustment } from '../../services/api/widgetApi';
import styles from './css/WhatIfPanel.module.css';

const WHATIF_MAX_FIXTURES = 5;
const WHATIF_WIN_POINTS = 3;
const WHATIF_DRAW_POINTS = 1;
const WHATIF_LOSS_POINTS = 0;

type Outcome = 'home' | 'draw' | 'away';

interface Fixture {
  home_team: string;
  away_team: string;
  fixture_id: string;
}

interface WhatIfPanelProps {
  teams: TeamProjection[];
  fixtures: Fixture[];
  onAdjustment: (adjustments: WhatIfAdjustment[]) => void;
}

export default function WhatIfPanel({ fixtures, onAdjustment }: WhatIfPanelProps) {
  const [selections, setSelections] = useState<Record<string, Outcome | null>>({});

  const visibleFixtures = fixtures.slice(0, WHATIF_MAX_FIXTURES);

  if (visibleFixtures.length === 0) {
    return (
      <div className={styles.panel}>
        <p className={styles.scopeLabel}>Estimated impact — not a full re-simulation</p>
        <NullStatePlaceholder icon="chart" message="No upcoming fixtures available for what-if analysis" />
      </div>
    );
  }

  function handleSelect(fixtureId: string, outcome: Outcome) {
    const current = selections[fixtureId];
    const next = current === outcome ? null : outcome;
    const updated = { ...selections, [fixtureId]: next };
    setSelections(updated);

    const adjustments: WhatIfAdjustment[] = visibleFixtures.map(f => ({
      fixture_id: f.fixture_id,
      home_team: f.home_team,
      away_team: f.away_team,
      selected_outcome: updated[f.fixture_id] ?? null,
    }));
    onAdjustment(adjustments);
  }

  function handleReset() {
    setSelections({});
    const adjustments: WhatIfAdjustment[] = visibleFixtures.map(f => ({
      fixture_id: f.fixture_id,
      home_team: f.home_team,
      away_team: f.away_team,
      selected_outcome: null,
    }));
    onAdjustment(adjustments);
  }

  const OUTCOMES: { key: Outcome; label: string }[] = [
    { key: 'home', label: 'Home Win' },
    { key: 'draw', label: 'Draw' },
    { key: 'away', label: 'Away Win' },
  ];

  return (
    <div className={styles.panel}>
      <div className={styles.panelHeader}>
        <p className={styles.scopeLabel}>Estimated impact — not a full re-simulation</p>
        <button className={styles.resetBtn} onClick={handleReset}>
          Reset
        </button>
      </div>
      {visibleFixtures.map(f => {
        const selected = selections[f.fixture_id] ?? null;
        return (
          <div key={f.fixture_id} className={styles.fixtureRow}>
            <span className={styles.teamLabel}>{f.home_team}</span>
            <div className={styles.outcomeButtons}>
              {OUTCOMES.map(({ key, label }) => (
                <button
                  key={key}
                  className={`${styles.outcomeBtn} ${selected === key ? styles.outcomeBtnActive : ''}`}
                  onClick={() => handleSelect(f.fixture_id, key)}
                >
                  {label}
                </button>
              ))}
            </div>
            <span className={styles.teamLabel}>{f.away_team}</span>
          </div>
        );
      })}
    </div>
  );
}

export { WHATIF_WIN_POINTS, WHATIF_DRAW_POINTS, WHATIF_LOSS_POINTS };
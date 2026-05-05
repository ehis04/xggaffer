import '@testing-library/jest-dom/vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import ModelTrustCentre from '../../../pages/predictions/ModelTrustCentre';

vi.mock('../../../services/api/widgetApi', () => ({
  fetchModelTrustWidget: vi.fn(),
}));

vi.mock('../../../common/components/SectionSkeleton', () => ({
  SectionSkeleton: () => <div data-testid="section-skeleton" />,
}));

vi.mock('../../../common/components/InlineRetry', () => ({
  InlineRetry: ({ onRetry }: { onRetry: () => void }) => (
    <button onClick={onRetry}>Retry</button>
  ),
}));

vi.mock('../../../common/components/FreshnessBadge', () => ({
  FreshnessBadge: () => <span data-testid="freshness-badge" />,
}));

vi.mock('../../../components/widgets/DegradedBanner', () => ({
  default: ({ reason }: { reason: string }) => (
    <div data-testid="degraded-banner">{reason}</div>
  ),
}));

vi.mock('../../../components/widgets/NullStatePlaceholder', () => ({
  default: ({ message }: { message: string }) => (
    <div data-testid="null-placeholder">{message}</div>
  ),
}));

vi.mock('../../../components/widgets/CalibrationChart', () => ({
  default: () => <div data-testid="calibration-chart" />,
}));

vi.mock('../../../components/widgets/ConfidenceAccuracyChart', () => ({
  default: () => <div data-testid="confidence-accuracy-chart" />,
}));

vi.mock('../../../components/widgets/BiggestMissesPanel', () => ({
  default: () => <div data-testid="biggest-misses-panel" />,
}));

import {
  fetchModelTrustWidget,
  type ModelTrustData,
  type ModelTrustWidgetPayload,
  type WidgetFreshness,
} from '../../../services/api/widgetApi';

const FRESH: WidgetFreshness = {
  source_fetched_at: null, snapshot_published_at: null,
  is_stale: false, is_degraded: false, stale_reason: null,
  sla_seconds: 21600, cascade_degraded: false, cascade_reason: null,
};

const MOCK_DATA: ModelTrustData = {
  overall_accuracy: 0.543,
  total_resolved: 120,
  accuracy_by_band: [
    { band: 'high', total: 50, correct_count: 30, accuracy: 0.60 },
    { band: 'medium', total: 40, correct_count: 20, accuracy: 0.50 },
    { band: 'low', total: 30, correct_count: 12, accuracy: 0.40 },
  ],
  accuracy_by_league: [
    { league_code: 'EPL', total: 60, correct_count: 33, accuracy: 0.55 },
    { league_code: 'La_Liga', total: 60, correct_count: 32, accuracy: 0.53 },
  ],
  recent_form: { count: 20, accuracy: 0.60 },
  biggest_misses: [],
  market_comparison: {
    market_accuracy: 0.512,
    model_accuracy_vs_market: 0.031,
    total_evaluated: 100,
  },
  confidence_distribution: [],
};

function makePayload(
  data: ModelTrustData | null,
  freshOverrides: Partial<WidgetFreshness> = {},
): ModelTrustWidgetPayload {
  const freshness: WidgetFreshness = { ...FRESH, ...freshOverrides };
  return {
    widget_type: 'model_trust',
    data,
    explanation: {},
    confidence: { score: 0.5, band: 'medium' },
    freshness,
    summary: data === null ? { cold_start_note: 'No data yet.' } : {},
  };
}

function renderPage(initialEntry = '/trust') {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes>
        <Route path="/trust" element={<ModelTrustCentre />} />
      </Routes>
    </MemoryRouter>
  );
}

describe('ModelTrustCentre', () => {
  beforeEach(() => vi.clearAllMocks());

  it('renders SectionSkeleton during load', () => {
    vi.mocked(fetchModelTrustWidget).mockReturnValueOnce(new Promise(() => {}));
    renderPage();
    expect(screen.getByTestId('section-skeleton')).toBeInTheDocument();
  });

  it('renders NullStatePlaceholder for cold start (data null)', async () => {
    vi.mocked(fetchModelTrustWidget).mockResolvedValueOnce(makePayload(null));
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('null-placeholder')).toBeInTheDocument();
    });
  });

  it('cold start NullStatePlaceholder shows cold_start_note from summary', async () => {
    vi.mocked(fetchModelTrustWidget).mockResolvedValueOnce(makePayload(null));
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('No data yet.')).toBeInTheDocument();
    });
  });

  it('renders overall accuracy when data present', async () => {
    vi.mocked(fetchModelTrustWidget).mockResolvedValueOnce(makePayload(MOCK_DATA));
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('54.3%')).toBeInTheDocument();
    });
  });

  it('renders CalibrationChart when data present', async () => {
    vi.mocked(fetchModelTrustWidget).mockResolvedValueOnce(makePayload(MOCK_DATA));
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('confidence-accuracy-chart')).toBeInTheDocument();
    });
  });

  it('renders BiggestMissesPanel when data present', async () => {
    vi.mocked(fetchModelTrustWidget).mockResolvedValueOnce(makePayload(MOCK_DATA));
    renderPage();
    await waitFor(() => {
      expect(screen.getAllByTestId('biggest-misses-panel')).toHaveLength(2);
    });
  });

  it('renders DegradedBanner when cascade_degraded true', async () => {
    vi.mocked(fetchModelTrustWidget).mockResolvedValueOnce(
      makePayload(MOCK_DATA, { cascade_degraded: true, cascade_reason: 'outcome' })
    );
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('degraded-banner')).toBeInTheDocument();
    });
  });

  it('league filter select renders all LEAGUE_OPTIONS', () => {
    vi.mocked(fetchModelTrustWidget).mockReturnValueOnce(new Promise(() => {}));
    renderPage();
    const select = screen.getByRole('combobox');
    const options = Array.from(select.querySelectorAll('option'));
    expect(options.length).toBe(6);
    expect(options[0].textContent).toBe('All leagues');
  });

  it('changing league filter triggers re-fetch', async () => {
    vi.mocked(fetchModelTrustWidget).mockResolvedValue(makePayload(null));
    renderPage();
    await waitFor(() => screen.getByTestId('null-placeholder'));
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'EPL' } });
    await waitFor(() => {
      expect(fetchModelTrustWidget).toHaveBeenCalledTimes(2);
      expect(fetchModelTrustWidget).toHaveBeenLastCalledWith('EPL');
    });
  });

  it('prefills league filter from url query', async () => {
    vi.mocked(fetchModelTrustWidget).mockResolvedValue(makePayload(null));
    renderPage('/trust?league=EPL&example=1');
    await waitFor(() => {
      expect(fetchModelTrustWidget).toHaveBeenCalledWith('EPL');
    });
    expect(screen.getByRole('combobox')).toHaveValue('EPL');
  });
});
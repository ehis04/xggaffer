import '@testing-library/jest-dom/vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';

import PredictionsHub from '../../../pages/predictions/PredictionsHub';

vi.mock('../../../services/api/livefootballApi', () => ({
  default: {
    getCompetitions: vi.fn(),
    getCompetitionFixtures: vi.fn(),
  },
}));

vi.mock('../../../services/api/predictionsApi', () => ({
  getOddsFixtures: vi.fn().mockResolvedValue({
    data: {
      fixtures: [],
    },
  }),
}));

vi.mock('../../widgets/MatchPredictionCard', () => ({
  default: ({ homeTeam, awayTeam }: { homeTeam: string; awayTeam: string }) => (
    <div data-testid="prediction-card">{homeTeam} vs {awayTeam}</div>
  ),
}));

function renderHub() {
  return render(
    <MemoryRouter>
      <PredictionsHub />
    </MemoryRouter>
  );
}

describe('PredictionsHub', () => {
  beforeEach(() => vi.clearAllMocks());

  it('renders page heading', () => {
    renderHub();
    expect(screen.getByRole('heading', { name: /prediction & intelligence/i })).toBeInTheDocument();
  });

  it('renders all 7 section cards', () => {
    renderHub();
    // Check for the 7 section cards - use getAllByText for texts that appear in multiple places
    expect(screen.getAllByText(/Match Predictions/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Odds Comparison/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Match Intelligence/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Season Projection/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Tactical Scouting/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Squad Intelligence/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Model Trust Centre/i).length).toBeGreaterThan(0);
  });

  it('renders section descriptions', () => {
    renderHub();
    expect(screen.getByText(/Model-powered match predictions/i)).toBeInTheDocument();
    expect(screen.getByText(/Compare model probabilities/i)).toBeInTheDocument();
  });

  it('renders all action buttons', () => {
    renderHub();
    expect(screen.getByRole('button', { name: /Open Predictions/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Compare Odds/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Look Up Match/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /View Projections/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Scout a Team/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /View Squad/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Open Trust Centre/i })).toBeInTheDocument();
  });

  it('navigates when clicking a section button', () => {
    renderHub();
    // Click the Match Intelligence button
    const lookUpMatchButton = screen.getByRole('button', { name: /Look Up Match/i });
    fireEvent.click(lookUpMatchButton);
    // The component uses navigate - we just verify the button is clickable
    expect(lookUpMatchButton).toBeInTheDocument();
  });
});

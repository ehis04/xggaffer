import '@testing-library/jest-dom/vitest';

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import PredictionPage from './PredictionPage';
import {
  mockModelInfoResponse,
  mockPredictionResponse,
  mockTeamsResponse,
} from './__mocks__/predictionFixtures';

vi.mock('../../services/api/predictionsApi', () => ({
  getTeams: vi.fn(),
  getModelInfo: vi.fn(),
  predictMatch: vi.fn(),
  PredictionsApiError: class PredictionsApiError extends Error {
    status: number;

    constructor(message: string, status: number) {
      super(message);
      this.name = 'PredictionsApiError';
      this.status = status;
    }
  },
}));

import {
  getModelInfo,
  getTeams,
  predictMatch,
} from '../../services/api/predictionsApi';

describe('PredictionPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getTeams).mockResolvedValue(mockTeamsResponse);
    vi.mocked(getModelInfo).mockResolvedValue(mockModelInfoResponse);
    vi.mocked(predictMatch).mockResolvedValue(mockPredictionResponse);
  });

  it('loads model metadata and team selectors', async () => {
    render(<PredictionPage />);

    expect(await screen.findByText('Match Prediction')).toBeInTheDocument();
    expect(await screen.findByText('logistic_regression')).toBeInTheDocument();
    expect(await screen.findByDisplayValue('Arsenal')).toBeInTheDocument();
    expect(await screen.findByDisplayValue('Chelsea')).toBeInTheDocument();
  });

  it('submits a prediction and renders probabilities plus factors', async () => {
    render(<PredictionPage />);

    await screen.findByText('Try a matchup');

    fireEvent.click(screen.getByRole('button', { name: 'Predict match' }));

    await waitFor(() => {
      expect(predictMatch).toHaveBeenCalledWith({
        home_team: 'Arsenal',
        away_team: 'Chelsea',
        league: 'EPL',
        season: '2024',
        top_factors: 5,
      });
    });

    expect(await screen.findByText('Arsenal vs Chelsea: Home')).toBeInTheDocument();
    expect(screen.getByText('61.0%')).toBeInTheDocument();
    expect(screen.getByText('Top factors')).toBeInTheDocument();
    expect(screen.getByText('npxgd_diff')).toBeInTheDocument();
  });

  it('shows an inline validation message for the same team selected twice', async () => {
    render(<PredictionPage />);

    await screen.findByText('Try a matchup');

    fireEvent.change(screen.getByLabelText('Away team'), {
      target: { value: 'Arsenal' },
    });

    expect(await screen.findByRole('alert')).toHaveTextContent('Please choose two different teams.');
    expect(predictMatch).not.toHaveBeenCalled();
  });

  it('shows an API error when prediction fails', async () => {
    vi.mocked(predictMatch).mockRejectedValueOnce(new Error('Prediction model is not available.'));

    render(<PredictionPage />);

    await screen.findByText('Try a matchup');
    fireEvent.click(screen.getByRole('button', { name: 'Predict match' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Prediction model is not available.');
  });
});

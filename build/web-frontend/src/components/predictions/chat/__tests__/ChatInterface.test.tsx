import '@testing-library/jest-dom/vitest';

import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { ApiEnvelope } from '../../../../common/types/response';
import type { ChatResponse } from '../../../../types/prediction';

import ChatInterface from '../ChatInterface';

vi.mock('../../../../services/api/predictionsApi', () => ({
  chatQuery: vi.fn(),
}));

import { chatQuery } from '../../../../services/api/predictionsApi';

const minimalChatResponse: ChatResponse = {
  prose: 'xG is expected goals.',
  structured_data: {
    intent: 'GLOSSARY',
    entities: { home_team: null, away_team: null, team: null, player_name: null, league: null, season: null },
    engine_data: {},
    partial: false,
    error: null,
    timestamp: '2026-01-01T00:00:00Z',
  },
  intent: 'GLOSSARY',
  entities: { home_team: null, away_team: null, team: null, player_name: null, league: null, season: null },
  used_fallback: false,
  query_type: 'GLOSSARY',
};

function makeEnvelope(overrides: Partial<ChatResponse> = {}): ApiEnvelope<ChatResponse> {
  return {
    data: {
      ...minimalChatResponse,
      ...overrides,
      structured_data: {
        ...minimalChatResponse.structured_data,
        ...overrides.structured_data,
      },
    },
    freshness: {
      source_fetched_at: null,
      snapshot_published_at: null,
      is_stale: false,
      is_degraded: false,
      stale_reason: null,
      sla_seconds: 21600,
    },
    version: '1',
    warnings: [],
    generated_at: '2026-01-01T00:00:00Z',
  };
}

describe('ChatInterface', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders all 4 starter chips initially', () => {
    render(<ChatInterface />);
    expect(screen.getByText('Compare Arsenal vs Chelsea with bookmaker odds')).toBeInTheDocument();
    expect(screen.getByText('What is xG?')).toBeInTheDocument();
    expect(screen.getByText('Show me the market view for Liverpool vs Man City')).toBeInTheDocument();
    expect(screen.getByText('What lineup will Arsenal use?')).toBeInTheDocument();
  });

  it('removes starter chips after a starter query is used', async () => {
    vi.mocked(chatQuery).mockResolvedValueOnce(makeEnvelope());
    render(<ChatInterface />);

    fireEvent.click(
      screen.getByRole('button', {
        name: 'Compare Arsenal vs Chelsea with bookmaker odds',
      }),
    );

    await waitFor(() => {
      expect(
        screen.queryByRole('button', {
          name: 'Compare Arsenal vs Chelsea with bookmaker odds',
        }),
      ).not.toBeInTheDocument();
    });
  });

  it('user message appears in list', async () => {
    vi.mocked(chatQuery).mockResolvedValueOnce(makeEnvelope());
    render(<ChatInterface />);
    const input = screen.getByLabelText('Query input');
    fireEvent.change(input, { target: { value: 'what is xG' } });
    fireEvent.click(screen.getByLabelText('Send query'));
    expect(await screen.findByText('what is xG')).toBeInTheDocument();
  });

  it('assistant prose appears after response', async () => {
    vi.mocked(chatQuery).mockResolvedValueOnce(makeEnvelope());
    render(<ChatInterface />);
    const input = screen.getByLabelText('Query input');
    fireEvent.change(input, { target: { value: 'what is xG' } });
    fireEvent.click(screen.getByLabelText('Send query'));
    expect(await screen.findByText('xG is expected goals.')).toBeInTheDocument();
  });

  it('shows fallback badge when used_fallback is true', async () => {
    vi.mocked(chatQuery).mockResolvedValueOnce(makeEnvelope({ used_fallback: true }));
    render(<ChatInterface />);
    fireEvent.change(screen.getByLabelText('Query input'), { target: { value: 'test' } });
    fireEvent.click(screen.getByLabelText('Send query'));
    expect(await screen.findByText('(AI narration unavailable)')).toBeInTheDocument();
  });

  it('does not show fallback badge when used_fallback is false', async () => {
    vi.mocked(chatQuery).mockResolvedValueOnce(makeEnvelope({ used_fallback: false }));
    render(<ChatInterface />);
    fireEvent.change(screen.getByLabelText('Query input'), { target: { value: 'test' } });
    fireEvent.click(screen.getByLabelText('Send query'));
    await screen.findByText('xG is expected goals.');
    expect(screen.queryByText('(AI narration unavailable)')).not.toBeInTheDocument();
  });

  it('shows error message on API failure', async () => {
    vi.mocked(chatQuery).mockRejectedValueOnce(new Error('Network error'));
    render(<ChatInterface />);
    fireEvent.change(screen.getByLabelText('Query input'), { target: { value: 'test' } });
    fireEvent.click(screen.getByLabelText('Send query'));
    expect(await screen.findByText('Something went wrong. Please try again.')).toBeInTheDocument();
  });

  it('shows loading state during request', async () => {
    let resolve: ((v: ApiEnvelope<ChatResponse>) => void) | undefined;
    vi.mocked(chatQuery).mockReturnValueOnce(new Promise((r) => { resolve = r; }));
    render(<ChatInterface />);
    fireEvent.change(screen.getByLabelText('Query input'), { target: { value: 'test' } });
    fireEvent.click(screen.getByLabelText('Send query'));
    expect(await screen.findByText('xgGaffer is thinking...')).toBeInTheDocument();
    expect(screen.getByLabelText('Send query')).toBeDisabled();
    await act(async () => {
      resolve?.(makeEnvelope());
    });
    expect(await screen.findByText('xG is expected goals.')).toBeInTheDocument();
  });
});
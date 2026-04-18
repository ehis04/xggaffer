import '@testing-library/jest-dom/vitest';

import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import PredictionPage from '../PredictionPage';

vi.mock('../../../components/predictions/chat/ChatInterface', () => ({
  default: () => <div data-testid="chat-interface" />,
}));

describe('PredictionPage', () => {
  it('renders the page heading', () => {
    render(<PredictionPage />);
    expect(screen.getByRole('heading', { name: 'xgGaffer' })).toBeInTheDocument();
  });

  it('renders the subtitle', () => {
    render(<PredictionPage />);
    expect(screen.getByText(/Ask anything about match predictions/)).toBeInTheDocument();
  });

  it('renders the chat interface', () => {
    render(<PredictionPage />);
    expect(screen.getByTestId('chat-interface')).toBeInTheDocument();
  });
});
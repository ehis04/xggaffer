import '@testing-library/jest-dom/vitest';

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import PredictionPage from '../PredictionPage';

vi.mock('../../../components/predictions/chat/ChatInterface', () => ({
  default: ({ starterQueries }: { starterQueries?: readonly string[] }) => (
    <div data-testid="chat-interface" data-starter-count={starterQueries?.length ?? 0} />
  ),
}));

vi.mock('react-router-dom', () => ({
  useLocation: () => ({ pathname: '/coaching/predictions' }),
  useNavigate: () => vi.fn(),
}));

const MOBILE_WIDTH = 500;
const DESKTOP_WIDTH = 1024;

describe('PredictionPage', () => {
  it('renders SessionToolbar with Export and Clear buttons', () => {
    render(<PredictionPage />);
    expect(screen.getByRole('button', { name: /export/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /clear session/i })).toBeInTheDocument();
  });

  it('Export button is disabled on initial render', () => {
    render(<PredictionPage />);
    expect(screen.getByRole('button', { name: /export/i })).toBeDisabled();
  });

  it('renders pinned panel with empty placeholder message', () => {
    render(<PredictionPage />);
    expect(screen.getByText('Pin a response to keep it visible here')).toBeInTheDocument();
  });

  it('renders chat panel containing ChatInterface', () => {
    render(<PredictionPage />);
    expect(screen.getByTestId('chat-interface')).toBeInTheDocument();
  });

  it('passes PREDICTION_STARTER_QUERIES to ChatInterface starterQueries prop', () => {
    render(<PredictionPage />);
    const chatInterface = screen.getByTestId('chat-interface');
    expect(Number(chatInterface.getAttribute('data-starter-count'))).toBeGreaterThan(0);
  });

  it('renders Pinned button in toolbar', () => {
    render(<PredictionPage />);
    expect(screen.getByRole('button', { name: /pinned/i })).toBeInTheDocument();
  });

  it('toggles pinned panel visibility when Pinned button is clicked', () => {
    Object.defineProperty(window, 'innerWidth', { writable: true, configurable: true, value: MOBILE_WIDTH });
    render(<PredictionPage />);
    const pinnedBtn = screen.getByRole('button', { name: /pinned/i });
    fireEvent.click(pinnedBtn);
    expect(screen.getByRole('button', { name: /back to chat/i })).toBeInTheDocument();
    Object.defineProperty(window, 'innerWidth', { writable: true, configurable: true, value: DESKTOP_WIDTH });
  });

  it('Back to chat button hides pinned panel', () => {
    Object.defineProperty(window, 'innerWidth', { writable: true, configurable: true, value: MOBILE_WIDTH });
    render(<PredictionPage />);
    fireEvent.click(screen.getByRole('button', { name: /pinned/i }));
    fireEvent.click(screen.getByRole('button', { name: /back to chat/i }));
    expect(screen.queryByRole('button', { name: /back to chat/i })).not.toBeInTheDocument();
    Object.defineProperty(window, 'innerWidth', { writable: true, configurable: true, value: DESKTOP_WIDTH });
  });
});


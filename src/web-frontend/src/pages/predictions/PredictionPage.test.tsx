import '@testing-library/jest-dom/vitest';

import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';

import PredictionPage from './PredictionPage';

vi.mock('../../components/predictions/chat/ChatInterface', () => ({
  default: () => <div data-testid="chat-interface" />,
}));

vi.mock('../../components/Navigation/SideBar', () => ({
  Sidebar: () => null,
}));

vi.mock('../../components/Social/SocialUserButtons', () => ({
  SocialUserButtons: () => null,
}));

describe('PredictionPage', () => {
  const renderPage = () => render(<MemoryRouter><PredictionPage /></MemoryRouter>);

  it('renders the analytics session toolbar', () => {
    renderPage();
    expect(screen.getByText('xgGaffer Analytics')).toBeInTheDocument();
  });

  it('renders session actions', () => {
    renderPage();
    expect(screen.getByRole('button', { name: /clear session/i })).toBeInTheDocument();
  });

  it('renders the chat interface', () => {
    renderPage();
    expect(screen.getByTestId('chat-interface')).toBeInTheDocument();
  });
});

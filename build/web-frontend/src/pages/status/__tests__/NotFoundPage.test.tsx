import '@testing-library/jest-dom/vitest';

import { act, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { NotFoundPage } from '../NotFoundPage';

const renderPage = () =>
  render(
    <MemoryRouter>
      <NotFoundPage />
    </MemoryRouter>
  );

describe('NotFoundPage', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders the not-found heading', () => {
    renderPage();
    expect(screen.getByRole('heading', { name: 'Not Found' })).toBeInTheDocument();
  });

  it('renders the Go Home button', () => {
    renderPage();
    expect(screen.getByRole('button', { name: 'Go Home' })).toBeInTheDocument();
  });

  it('renders the countdown display', () => {
    renderPage();
    expect(screen.getByText(/Redirecting in \d+s/)).toBeInTheDocument();
  });

  it('countdown starts at 5', () => {
    renderPage();
    expect(screen.getByText('Redirecting in 5s')).toBeInTheDocument();
  });

  it('countdown decrements after 1 second', () => {
    renderPage();
    act(() => { vi.advanceTimersByTime(1000); });
    expect(screen.getByText('Redirecting in 4s')).toBeInTheDocument();
  });
});
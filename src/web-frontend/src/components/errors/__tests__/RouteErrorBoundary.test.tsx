import '@testing-library/jest-dom/vitest';

import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { RouteErrorBoundary } from '../../../pages/status/RouteErrorBoundary';

const ThrowingComponent = ({ shouldThrow }: { shouldThrow: boolean }) => {
  if (shouldThrow) throw new Error('Test render error');
  return <div>Healthy content</div>;
};

const renderWithBoundary = (shouldThrow: boolean) =>
  render(
    <MemoryRouter>
      <RouteErrorBoundary>
        <ThrowingComponent shouldThrow={shouldThrow} />
      </RouteErrorBoundary>
    </MemoryRouter>
  );

describe('RouteErrorBoundary', () => {
  beforeEach(() => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  it('renders children when no error is thrown', () => {
    renderWithBoundary(false);
    expect(screen.getByText('Healthy content')).toBeInTheDocument();
  });

  it('renders AppErrorPage when a child throws', () => {
    renderWithBoundary(true);
    expect(screen.getByRole('heading', { name: 'Something went wrong' })).toBeInTheDocument();
  });

  it('does not render children content when an error is caught', () => {
    renderWithBoundary(true);
    expect(screen.queryByText('Healthy content')).not.toBeInTheDocument();
  });

  it('renders a Try Again button when error is caught', () => {
    renderWithBoundary(true);
    expect(screen.getByRole('button', { name: 'Try Again' })).toBeInTheDocument();
  });

  it('resets error state when Try Again is clicked', () => {
    const { rerender } = render(
      <MemoryRouter>
        <RouteErrorBoundary>
          <ThrowingComponent shouldThrow={true} />
        </RouteErrorBoundary>
      </MemoryRouter>
    );

    expect(screen.getByRole('heading', { name: 'Something went wrong' })).toBeInTheDocument();

    rerender(
      <MemoryRouter>
        <RouteErrorBoundary>
          <ThrowingComponent shouldThrow={false} />
        </RouteErrorBoundary>
      </MemoryRouter>
    );

    fireEvent.click(screen.getByRole('button', { name: 'Try Again' }));
    expect(screen.getByText('Healthy content')).toBeInTheDocument();
  });

  it('renders Go Home button when error is caught', () => {
    renderWithBoundary(true);
    expect(screen.getByRole('button', { name: 'Go Home' })).toBeInTheDocument();
  });
});
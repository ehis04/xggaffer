import '@testing-library/jest-dom/vitest';

import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { InlineRetry } from '../InlineRetry';

describe('InlineRetry', () => {
  const mockOnRetry = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders default message when no message prop provided', () => {
    render(<InlineRetry onRetry={mockOnRetry} />);
    expect(screen.getByText('Failed to load')).toBeInTheDocument();
  });

  it('renders custom message', () => {
    render(<InlineRetry message="Failed to load players" onRetry={mockOnRetry} />);
    expect(screen.getByText('Failed to load players')).toBeInTheDocument();
  });

  it('renders retry button', () => {
    render(<InlineRetry onRetry={mockOnRetry} />);
    expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument();
  });

  it('calls onRetry when retry button is clicked', () => {
    render(<InlineRetry onRetry={mockOnRetry} />);
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }));
    expect(mockOnRetry).toHaveBeenCalledTimes(1);
  });

  it('shows Retrying... and disables button when retrying is true', () => {
    render(<InlineRetry onRetry={mockOnRetry} retrying={true} />);
    const button = screen.getByRole('button', { name: 'Retrying...' });
    expect(button).toBeInTheDocument();
    expect(button).toBeDisabled();
  });

  it('does not call onRetry when button is disabled', () => {
    render(<InlineRetry onRetry={mockOnRetry} retrying={true} />);
    fireEvent.click(screen.getByRole('button', { name: 'Retrying...' }));
    expect(mockOnRetry).not.toHaveBeenCalled();
  });

  it('button is enabled and shows Retry when retrying is false', () => {
    render(<InlineRetry onRetry={mockOnRetry} retrying={false} />);
    const button = screen.getByRole('button', { name: 'Retry' });
    expect(button).not.toBeDisabled();
  });

  it('has role alert for screen readers', () => {
    render(<InlineRetry onRetry={mockOnRetry} />);
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });
});
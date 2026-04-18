import '@testing-library/jest-dom/vitest';

import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import ChatInput from '../ChatInput';

describe('ChatInput', () => {
  const mockOnSubmit = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders input and button', () => {
    render(<ChatInput onSubmit={mockOnSubmit} isLoading={false} />);
    expect(screen.getByLabelText('Query input')).toBeInTheDocument();
    expect(screen.getByLabelText('Send query')).toBeInTheDocument();
  });

  it('submits on button click and clears input', () => {
    render(<ChatInput onSubmit={mockOnSubmit} isLoading={false} />);
    const input = screen.getByLabelText('Query input');
    fireEvent.change(input, { target: { value: 'what is xG' } });
    fireEvent.click(screen.getByLabelText('Send query'));
    expect(mockOnSubmit).toHaveBeenCalledWith('what is xG');
    expect(input).toHaveValue('');
  });

  it('submits on Enter key', () => {
    render(<ChatInput onSubmit={mockOnSubmit} isLoading={false} />);
    const input = screen.getByLabelText('Query input');
    fireEvent.change(input, { target: { value: 'Arsenal vs Chelsea' } });
    fireEvent.keyDown(input, { key: 'Enter' });
    expect(mockOnSubmit).toHaveBeenCalledWith('Arsenal vs Chelsea');
  });

  it('does not submit on empty input', () => {
    render(<ChatInput onSubmit={mockOnSubmit} isLoading={false} />);
    fireEvent.click(screen.getByLabelText('Send query'));
    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  it('button is disabled when loading', () => {
    render(<ChatInput onSubmit={mockOnSubmit} isLoading={true} />);
    expect(screen.getByLabelText('Send query')).toBeDisabled();
  });

  it('input is disabled when loading', () => {
    render(<ChatInput onSubmit={mockOnSubmit} isLoading={true} />);
    expect(screen.getByLabelText('Query input')).toBeDisabled();
  });

  it('shows character count when typing', () => {
    render(<ChatInput onSubmit={mockOnSubmit} isLoading={false} />);
    fireEvent.change(screen.getByLabelText('Query input'), { target: { value: 'hello' } });
    expect(screen.getByText('5 / 500')).toBeInTheDocument();
  });

  it('does not submit when over character limit', () => {
    render(<ChatInput onSubmit={mockOnSubmit} isLoading={false} />);
    fireEvent.change(screen.getByLabelText('Query input'), {
      target: { value: 'a'.repeat(501) },
    });
    fireEvent.click(screen.getByLabelText('Send query'));
    expect(mockOnSubmit).not.toHaveBeenCalled();
  });
});
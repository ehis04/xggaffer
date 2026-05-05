import '@testing-library/jest-dom/vitest';

import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { StatusBlock } from '../StatusBlock';

describe('StatusBlock', () => {
  describe('default titles per variant', () => {
    it('renders default title for not-found', () => {
      render(<StatusBlock variant="not-found" />);
      expect(screen.getByRole('heading', { name: 'Not Found' })).toBeInTheDocument();
    });

    it('renders default title for forbidden', () => {
      render(<StatusBlock variant="forbidden" />);
      expect(screen.getByRole('heading', { name: 'Access Denied' })).toBeInTheDocument();
    });

    it('renders default title for unauthenticated', () => {
      render(<StatusBlock variant="unauthenticated" />);
      expect(screen.getByRole('heading', { name: 'Sign In Required' })).toBeInTheDocument();
    });

    it('renders default title for error', () => {
      render(<StatusBlock variant="error" />);
      expect(screen.getByRole('heading', { name: 'Something went wrong' })).toBeInTheDocument();
    });

    it('renders default title for empty', () => {
      render(<StatusBlock variant="empty" />);
      expect(screen.getByRole('heading', { name: 'Nothing here yet' })).toBeInTheDocument();
    });
  });

  describe('default messages per variant', () => {
    it('renders default message for not-found', () => {
      render(<StatusBlock variant="not-found" />);
      expect(screen.getByText("The resource you're looking for doesn't exist.")).toBeInTheDocument();
    });

    it('renders default message for error', () => {
      render(<StatusBlock variant="error" />);
      expect(screen.getByText('An unexpected error occurred. Please try again.')).toBeInTheDocument();
    });
  });

  describe('custom overrides', () => {
    it('renders custom title instead of default', () => {
      render(<StatusBlock variant="not-found" title="Custom Title" />);
      expect(screen.getByRole('heading', { name: 'Custom Title' })).toBeInTheDocument();
      expect(screen.queryByText('Not Found')).not.toBeInTheDocument();
    });

    it('renders custom message instead of default', () => {
      render(<StatusBlock variant="error" message="Custom error message" />);
      expect(screen.getByText('Custom error message')).toBeInTheDocument();
      expect(screen.queryByText('An unexpected error occurred. Please try again.')).not.toBeInTheDocument();
    });
  });

  describe('actions slot', () => {
    it('renders provided actions', () => {
      render(
        <StatusBlock
          variant="error"
          actions={<button type="button">Retry</button>}
        />
      );
      expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument();
    });

    it('does not render actions container when actions prop is absent', () => {
      const { container } = render(<StatusBlock variant="empty" />);
      expect(container.querySelector('button')).not.toBeInTheDocument();
    });

    it('calls action handler when action button is clicked', () => {
      const handleClick = vi.fn();
      render(
        <StatusBlock
          variant="error"
          actions={<button type="button" onClick={handleClick}>Retry</button>}
        />
      );
      screen.getByRole('button', { name: 'Retry' }).click();
      expect(handleClick).toHaveBeenCalledTimes(1);
    });
  });
});
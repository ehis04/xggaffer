import '@testing-library/jest-dom/vitest';

import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { FullPageLoader } from '../FullPageLoader';

describe('FullPageLoader', () => {
  it('renders a status region', () => {
    render(<FullPageLoader />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('renders the default label as screen-reader text', () => {
    render(<FullPageLoader />);
    expect(screen.getByText('Loading')).toBeInTheDocument();
  });

  it('renders a custom label as screen-reader text', () => {
    render(<FullPageLoader label="Loading teamsheet" />);
    expect(screen.getByText('Loading teamsheet')).toBeInTheDocument();
  });

  it('spinner element is present and aria-hidden', () => {
    const { container } = render(<FullPageLoader />);
    const spinner = container.querySelector('[aria-hidden="true"]');
    expect(spinner).toBeInTheDocument();
  });
});
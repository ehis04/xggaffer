import { fireEvent, render } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { SocialUserButtons } from '../SocialUserButtons';

const mockNavigate = vi.fn();
const mockLogout = vi.fn();

vi.mock('react-router-dom', () => ({
  useNavigate: () => mockNavigate,
}));

vi.mock('../../../context/useAuth', () => ({
  useAuth: () => ({
    logout: mockLogout,
  }),
}));

describe('SocialUserButtons', () => {
  beforeEach(() => {
    mockNavigate.mockReset();
    mockLogout.mockReset();
    mockLogout.mockResolvedValue(undefined);
  });

  it('logs out and navigates home when logout button is clicked', async () => {
    const { container } = render(<SocialUserButtons />);

    const logoutButton = container.querySelector('.logout-button button');
    expect(logoutButton).not.toBeNull();

    fireEvent.click(logoutButton as HTMLButtonElement);

    expect(mockLogout).toHaveBeenCalledTimes(1);
    await Promise.resolve();
    expect(mockNavigate).toHaveBeenCalledWith('/', { replace: true });
  });
});

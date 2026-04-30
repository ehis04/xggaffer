import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Sidebar } from '../SideBar';

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

vi.mock('../functions/getUserProfile', () => ({
  getUserProfile: vi.fn(),
}));

vi.mock('../../Buttons/ProfileButton', () => ({
  ProfileButton: () => <div data-testid="profile-button" />,
}));

describe('Sidebar', () => {
  beforeEach(() => {
    mockNavigate.mockReset();
    mockLogout.mockReset();
    mockLogout.mockResolvedValue(undefined);
  });

  it('logs out and navigates home when logout is clicked', async () => {
    render(<Sidebar />);

    fireEvent.click(screen.getByRole('button', { name: /logout/i }));

    expect(mockLogout).toHaveBeenCalledTimes(1);
    await Promise.resolve();
    expect(mockNavigate).toHaveBeenCalledWith('/', { replace: true });
  });
});

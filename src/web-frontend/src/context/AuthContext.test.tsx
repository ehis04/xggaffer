import { useEffect, useState } from 'react';
import { act, fireEvent, render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { AuthProvider } from './AuthContext';
import { useAuth } from './useAuth';
import { authApi, type User } from '../services/api/auth';
import apiClient from '../services/api/client';
import type { UserData } from '../components/Navigation/SideBar';
import { getUserProfile, resetUserProfileCache } from '../components/Navigation/functions/getUserProfile';

const makeUser = (id: number, username: string): User => ({
  id, username, email: `${username}@example.com`, first_name: username, last_name: '', email_verified: true,
});

function ProfileLabel() {
  const [profile, setProfile] = useState<UserData | null>(null);
  useEffect(() => { void getUserProfile(setProfile); }, []);
  return <p>{profile?.username ?? 'Loading profile'}</p>;
}

function SessionControls() {
  const { user, isLoading, login, logout } = useAuth();
  if (isLoading) return <p>Checking session</p>;
  return user ? (
    <>
      <ProfileLabel />
      <button onClick={() => void logout()}>Sign out</button>
    </>
  ) : (
    <button onClick={() => void login({ email: 'second@example.com', password: 'example' })}>Sign in</button>
  );
}

it('discards a pending profile response from the previous account', async () => {
  resetUserProfileCache();
  const first = makeUser(1, 'first');
  const second = makeUser(2, 'second');
  const me = vi.spyOn(authApi, 'getCurrentUser').mockResolvedValue(first);
  const logout = vi.spyOn(authApi, 'logout').mockResolvedValue({ message: 'Signed out' });
  const login = vi.spyOn(authApi, 'login').mockResolvedValue({ user: second, message: 'Signed in' });
  let finishOldRequest!: (profile: unknown) => void;
  const getProfile = vi.spyOn(apiClient, 'get')
    .mockReturnValueOnce(new Promise(resolve => { finishOldRequest = resolve; }))
    .mockResolvedValue({ user: second });

  try {
    render(<AuthProvider><SessionControls /></AuthProvider>);
    fireEvent.click(await screen.findByRole('button', { name: 'Sign out' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Sign in' }));
    await screen.findByText('second');

    await act(async () => { finishOldRequest({ user: first }); });
    expect(screen.queryByText('first')).toBeNull();
    const consumer = vi.fn();
    await getUserProfile(consumer);
    expect(consumer).toHaveBeenCalledWith(expect.objectContaining({ username: 'second' }));
  } finally {
    resetUserProfileCache();
    for (const spy of [me, logout, login, getProfile]) spy.mockRestore();
  }
});

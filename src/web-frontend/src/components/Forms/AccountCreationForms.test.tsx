import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { expect, it, vi } from 'vitest';
import { AccountCreationForms } from './AccountCreationForms';
import apiClient from '../../services/api/client';

vi.mock('../../context/useAuth', () => ({
  useAuth: () => ({ isEmailVerified: true }),
}));

it('takes verified users home after saving their role', async () => {
  const saveRole = vi.spyOn(apiClient, 'post').mockResolvedValue({});
  try {
    render(
      <MemoryRouter initialEntries={['/create/profile/role']}>
        <Routes>
          <Route path="/create/profile/role" element={<AccountCreationForms />} />
          <Route path="/verify-email" element={<h1>Redundant verification</h1>} />
          <Route path="/home" element={<h1>Home</h1>} />
        </Routes>
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByRole('button', { name: /^Fan\b/ }));
    fireEvent.click(screen.getByRole('button', { name: 'Continue' }));
    fireEvent.click(screen.getByRole('button', { name: 'Continue' }));
    await screen.findByRole('heading', { name: 'Home' });
    expect(saveRole).toHaveBeenCalledExactlyOnceWith('/users/profile/role/', { role: 'F' });
  } finally {
    saveRole.mockRestore();
  }
});

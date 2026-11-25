import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { expect, it, vi } from 'vitest';
import { authApi } from '../../services/api/auth';
import VerifyEmailCallbackPage from './VerifyEmailCallbackPage';

it('shows the verification result without requiring a login session', async () => {
  const verify = vi.spyOn(authApi, 'verifyEmail').mockResolvedValue({
    message: 'Email verified successfully', already_verified: false,
  });
  try {
    render(
      <MemoryRouter initialEntries={['/verify-email/confirm?token=test-token']}>
        <Routes>
          <Route path="/verify-email/confirm" element={<VerifyEmailCallbackPage />} />
        </Routes>
      </MemoryRouter>,
    );
    await screen.findByRole('heading', { name: 'Email Verified!' });
    expect(verify).toHaveBeenCalledWith('test-token');
    expect(screen.getByRole('link', { name: 'Return to xgGaffer' }).getAttribute('href')).toBe('/');
  } finally {
    verify.mockRestore();
  }
});

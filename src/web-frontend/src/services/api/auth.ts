import apiClient from './client';

export interface User {
  id: number;
  email: string;
  username: string | null;
  first_name: string;
  last_name: string;
  email_verified: boolean;
}

export interface LoginCredentials {
  email: string;
  password: string;
  remember_me?: boolean;
}

export interface RegisterData {
  email: string;
  password: string;
  username?: string;
  first_name?: string;
  last_name?: string;
}

export interface AuthResponse {
  user: User;
  message: string;
  verification_email_sent?: boolean;
}

export interface VerificationStatus {
  email_verified: boolean;
  email: string;
}

export const authApi = {
  login: (credentials: LoginCredentials) =>
    apiClient.post<AuthResponse>('/users/auth/login/', credentials),

  register: (data: RegisterData) =>
    apiClient.post<AuthResponse>('/users/register/', data),

  logout: () =>
    apiClient.post<{ message: string }>('/users/auth/logout/'),

  getCurrentUser: async (): Promise<User> => {
    const response = await apiClient.get<{ user: User }>('/users/auth/me/');
    return response.user;
  },

  refresh: () =>
    apiClient.post<{ message: string }>('/users/auth/refresh/'),

  sendVerificationEmail: () =>
    apiClient.post<{ message: string }>('/users/auth/send-verification/'),

  resendVerificationEmail: () =>
    apiClient.post<{ message: string }>('/users/auth/resend-verification/'),

  verifyEmail: (token: string): Promise<{ message: string; already_verified: boolean }> =>
    apiClient.post<{ message: string; already_verified: boolean }>('/users/auth/verify-email/', { token }),

  getVerificationStatus: () =>
    apiClient.get<VerificationStatus>('/users/auth/verification-status/'),

  requestPasswordReset: (email: string) =>
    apiClient.post<{ message: string }>('/users/auth/password-reset/request/', { email }),

  resetPassword: (token: string, newPassword: string, confirmPassword: string) =>
    apiClient.post<{ message: string }>('/users/auth/password-reset/', { token, new_password: newPassword, confirm_password: confirmPassword }),
};

export default authApi;

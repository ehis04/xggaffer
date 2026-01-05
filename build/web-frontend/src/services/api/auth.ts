import apiClient from './client';

export interface User {
  id: number;
  email: string;
  username: string | null;
  first_name: string;
  last_name: string;
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
};

export default authApi;
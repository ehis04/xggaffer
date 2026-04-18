// src/services/api/usersApi.ts

import apiClient from './client';

export interface UserProfileResponse {
  id: number;
  user: {
    id: number;
    username: string;
    email: string;
    first_name: string;
    last_name: string;
  };
  display_name: string;
  user_display_name: string;
  bio: string;
  gender: string;
  date_of_birth: string | null;
  visibility: string;
  followers_count: number;
  following_count: number;
  created_at: string;
  updated_at: string;
  roles: Array<{
    id: number;
    role: string;
    role_display: string;
    created_at: string;
  }>;
  is_following: boolean;
  followed_by: boolean;
}

export const usersApi = {
  getMyProfile: () =>
    apiClient.get<UserProfileResponse>('/users/profile/'),

  getProfileByUsername: (username: string) =>
    apiClient.get<UserProfileResponse>(`/users/profile/${username}/`),

  createProfile: (data: {
    display_name?: string;
    gender?: string;
    date_of_birth?: string | null;
    bio?: string;
  }) =>
    apiClient.post<UserProfileResponse>('/users/profile/create/', data),

  updateProfile: (data: {
    display_name?: string;
    gender?: string;
    date_of_birth?: string | null;
    bio?: string;
    visibility?: string;
  }) =>
    apiClient.patch<UserProfileResponse>('/users/profile/', data),

  assignRole: (role: string) =>
    apiClient.post<{ id: number; role: string; role_display: string }>('/users/profile/role/', { role }),

  getRoles: () =>
    apiClient.get<Array<{ id: number; role: string; role_display: string; created_at: string }>>('/users/profile/role/'),

  followUser: (username: string) =>
    apiClient.post<{ message: string; following: boolean }>(`/users/profile/${username}/follow/`),

  unfollowUser: (username: string) =>
    apiClient.delete<{ message: string; following: boolean }>(`/users/profile/${username}/follow/`),

  getFollowStatus: (username: string) =>
    apiClient.get<{ is_following: boolean; followed_by: boolean; username: string }>(`/users/profile/${username}/follow-status/`),

  getFollowers: (username: string) =>
    apiClient.get<UserProfileResponse[]>(`/users/profile/${username}/followers/`),

  getFollowing: (username: string) =>
    apiClient.get<UserProfileResponse[]>(`/users/profile/${username}/following/`),
};

export default usersApi;
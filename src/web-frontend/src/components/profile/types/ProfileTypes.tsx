export interface FollowStatus {
  is_following: boolean;
  followed_by: boolean;
  follow_request_pending?: boolean;
}

export interface ProfileRole {
  id: number;
  role: string;
  role_display: string;
}

export interface ProfileData {
  username: string;
  display_name?: string;
  bio?: string;
  followers_count: number;
  following_count: number;
  gender?: string;
  date_of_birth?: string | null;
  visibility?: string;
  created_at?: string;
  profile_image?: string | null;
  roles?: ProfileRole[];
}

import axios from 'axios';

const base_url = 'http://localhost:8000/api';

const apiClient = axios.create({
    baseUrl: base_url,
    headers: {
        'Content-Type': 'application/json',
    },
});

apiClient.interceptors.request.use((config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

export interface Author {
    id: number;
    username: string;
    profile_image?: string;
    display_name?: string;
}

export interface Hashtag {
  id: number;
  body: string;
  usage_count: number;
}

export interface ExplorePost {
  id: number;
  author: Author;
  text_body: string;
  created_at: string;
  no_of_likes: number;
  no_of_comments: number;
  visibility: 'PB' | 'F' | 'PR';
  post_tags?: { hashtag: Hashtag }[];
  is_liked: boolean;
  hashtags?: string[];
  time_since_posted?: string;
  ranked_score?: number;
  popularity?: number;
  recency_scaled?: number;
}

export interface CreatePostData {
  text_body: string;
  visibility?: 'PB' | 'F' | 'PR';
}

export interface CreateCommentData {
  text_body: string;
  parent?: number;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
  filters_applied?: {
    hashtag?: string;
    search?: string;
    order_by?: string;
    min_likes?: string;
    author?: string;
  };
  suggestion?: string;
}

export interface ExploreParams {
  page?: number;
  page_size?: number;
  order_by?: 'likes' | 'recent' | 'ranked' | 'oldest' | 'comments' | 'comments_asc' | 'likes_asc' | 'trending';
  hashtag?: string;
  hashtags?: string[];
  min_likes?: number;
  max_likes?: number;
  min_comments?: number;
  max_comments?: number;
  search?: string;
  author?: string;
  date_from?: string;
  date_to?: string;
  has_attachments?: boolean;
}

export interface Comment {
  id: number;
  author: Author;
  post: number;
  parent?: number;
  text_body: string;
  no_of_likes: number;
  no_of_replies: number;
  created_at: string;
  moderation_status: 'OK' | 'UR' | 'R';
  children?: Comment[];
}
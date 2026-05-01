import apiClient from './client';
import { COMMUNITY } from './endpoints';

export interface Author {
  id: number;
  username: string;
  profile_image?: string | null;
  display_name?: string;
}

export interface Hashtag {
  id: number;
  body: string;
  usage_count: number;
}

export interface Post {
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
  is_liked?: boolean;
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

export interface NotificationItem {
  id: number;
  notification_type: 'FR' | 'FA' | 'NF' | 'M' | 'L' | 'C' | 'RY' | 'R';
  is_read: boolean;
  created_at: string;
  triggered_by: Author;
  target_kind: 'post' | 'comment' | 'followrequest' | null;
  target_id: number | null;
  post_id: number | null;
  comment_id: number | null;
  follow_request_status: 'P' | 'A' | 'D' | null;
}

export interface NotificationsParams {
  page?: number;
  pageSize?: number;
  unread_only?: boolean;
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

function buildExploreParams(params: ExploreParams): Record<string, string> {
  const result: Record<string, string> = {};

  if (params.page) result.page = String(params.page);
  if (params.page_size) result.page_size = String(params.page_size);
  if (params.order_by) result.order_by = params.order_by;
  if (params.hashtag) result.hashtag = params.hashtag;
  if (params.hashtags?.length) result.hashtags = params.hashtags.join(',');
  if (params.min_likes) result.min_likes = String(params.min_likes);
  if (params.max_likes) result.max_likes = String(params.max_likes);
  if (params.min_comments) result.min_comments = String(params.min_comments);
  if (params.max_comments) result.max_comments = String(params.max_comments);
  if (params.search) result.search = params.search;
  if (params.author) result.author = params.author;
  if (params.date_from) result.date_from = params.date_from;
  if (params.date_to) result.date_to = params.date_to;
  if (params.has_attachments !== undefined) result.has_attachments = String(params.has_attachments);

  return result;
}

export const communityApi = {
  explorePosts: (params: ExploreParams = {}) =>
    apiClient.get<PaginatedResponse<Post>>(
      '/community/explore/',
      buildExploreParams(params)
    ),

  getPost: (postId: number) =>
    apiClient.get<Post>(`/community/post/${postId}/`),

  createPost: (data: CreatePostData) =>
    apiClient.post<Post>('/community/create/post/', data),

  deletePost: (postId: number) =>
    apiClient.delete<void>(COMMUNITY.DELETE_POST(postId)),

  deleteComment: (commentId: number) =>
    apiClient.delete<void>(COMMUNITY.DELETE_COMMENT(commentId)),

  likePost: (postId: number) =>
    apiClient.post<{ liked: boolean; no_of_likes: number }>(
      `/community/posts/${postId}/like/`
    ),

  reportPost: (postId: number, reason = '') =>
    apiClient.post<{
      detail: string;
      created: boolean;
      report_count: number;
      moderation_status: 'OK' | 'UR' | 'R';
    }>(COMMUNITY.REPORT_POST(postId), { reason }),

  getPostComments: (postId: number) =>
    apiClient.get<Comment[]>(`/community/posts/${postId}/comments/`),

  createComment: (postId: number, data: CreateCommentData) =>
    apiClient.post<Comment>(`/community/post/${postId}/create/comment/`, data),

  likeComment: (commentId: number) =>
    apiClient.post<{ liked: boolean; no_of_likes: number }>(
      `/community/comment/${commentId}/like/`
    ),

  getTrendingHashtags: (limit = 10) =>
    apiClient.get<Hashtag[]>('/community/hashtags/trending/', { limit: String(limit) }),

  getNotifications: (params: NotificationsParams = {}) =>
    apiClient.get<PaginatedResponse<NotificationItem>>('/community/notifications/', {
      ...(params.page ? { page: params.page } : {}),
      ...(params.pageSize ? { "page-size": params.pageSize } : {}),
      ...(typeof params.unread_only === 'boolean'
        ? { unread_only: params.unread_only }
        : {}),
    }),

  markNotificationAsRead: (notificationId: number) =>
    apiClient.patch<{ id: number; is_read: boolean }>(
      `/community/notifications/${notificationId}/mark-read/`,
      {}
    ),
};

export default communityApi;

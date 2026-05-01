import type { PostAuthor } from "../Post";

export interface CommentResponse {
  id: number;
  author: string;
  text_body: string;
  created_at: string;
  no_of_likes: number;
  no_of_replies: number;
  post: number;
  parent: number | null;
  moderation_status: string;
  children?: CommentResponse[];
  is_liked: boolean;
}

export interface PostResponse {
  id: number;
  author: PostAuthor;
  post_id?: number;
  parent_id?: number;
  text_body: string;
  created_at: string;
  no_of_likes: number;
  no_of_comments: number;
  no_of_replies?: number;
  visibility: "PB" | "F" | "PR";
  moderation_status: "OK" | "UR" | "R";
  hashtags?: string[];
  mentions?: string[];
  type: "post" | "comment";
  is_liked?: boolean;
  is_reposted?: boolean;
}
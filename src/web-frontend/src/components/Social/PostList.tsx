import "./css/PostList.css";
import { Post } from "./Post";
import type { PostData } from "./Post";
import apiClient from "../../services/api/client";
import { useState, useEffect, useCallback } from "react";
import { COMMUNITY } from "../../services/api/endpoints";
import communityApi, { type PaginatedResponse } from "../../services/api/communityApi";
import { getPostsUrl, type PostListType } from "./functions/getPosts";

export interface PostListProps {
  postList?: PostData[];
  username?: string;
  refreshTrigger?: number;
  postListType?: PostListType;
  onLike?: (postId: number) => void;
  onComment?: (postId: number) => void;
  onProfileClick?: (username: string) => void;
  onPostClick?: (postId: number) => void;
}

export const PostList: React.FC<PostListProps> = ({
  refreshTrigger = 0,
  username,
  onComment,
  onProfileClick,
  onPostClick,
  postListType = "EXPLORE_POSTS",
}) => {
  const [posts, setPosts] = useState<PostData[]>([]);

  const getPosts = useCallback(async () => {
    try {
      const url = getPostsUrl(postListType, username);
      const data = await apiClient.get<PaginatedResponse<PostData>>(url);
      setPosts(data.results);
      return data;
    } catch (error) {
      console.error("Couldn't get posts: ", error);
      throw error;
    }
  }, [postListType, username]);

  useEffect(() => {
    getPosts();
  }, [getPosts, refreshTrigger]);

  const postsPB = posts.filter((item) => item.type === "post");

  if (!posts || posts.length === 0) {
    return (
      <div className="post-list-container-empty">
        <p> No posts available </p>
      </div>
    );
  }

  const handleLike = async (postId: number) => {
    await apiClient.post(COMMUNITY.LIKE_POST(postId));
  };

  const handleDelete = async (post: PostData) => {
    try {
      if (post.type === "comment") {
        await communityApi.deleteComment(post.id);
      } else {
        await communityApi.deletePost(post.id);
      }

      setPosts((currentPosts) =>
        currentPosts.filter((currentPost) => currentPost.id !== post.id)
      );
    } catch (error) {
      console.error("Couldn't delete post: ", error);
    }
  };

  const handleReport = async (post: PostData) => {
    try {
      const result = await communityApi.reportPost(post.id);
      if (result.moderation_status === "UR") {
        setPosts((currentPosts) =>
          currentPosts.filter((currentPost) => currentPost.id !== post.id)
        );
      }
    } catch (error) {
      console.error("Couldn't report post: ", error);
    }
  };

  return (
    <div className="post-list-container">
      {postsPB.map((post) => (
        <Post
          key={post.id}
          post={post}
          onLike={handleLike}
          onComment={onComment}
          onProfileClick={onProfileClick}
          onPostClick={onPostClick}
          onDelete={handleDelete}
          onReport={handleReport}
        />
      ))}
    </div>
  );
};

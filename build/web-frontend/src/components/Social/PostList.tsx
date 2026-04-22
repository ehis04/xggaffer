import "./css/PostList.css";
import { Post } from "./Post";
import type { PostData } from "./Post";
import apiClient from "../../services/api/client";
import { useState, useEffect } from "react";
import { COMMUNITY } from "../../services/api/endpoints";
import type { PaginatedResponse } from "../../services/api/communityApi";

type PostListType = "EXPLORE_POSTS" | "FOLLOWING_POSTS";

interface PostListProps {
  postList?: PostData[];
  refreshTrigger?: number;
  postListType?: PostListType;
  onLike?: (postId: number) => void;
  onComment?: (postId: number) => void;
  onProfileClick?: (username: string) => void;
  onPostClick?: (postId: number) => void;
}

export const PostList: React.FC<PostListProps> = ({
  refreshTrigger = 0,
  onComment,
  onProfileClick,
  onPostClick,
  postListType = "EXPLORE_POSTS",
}) => {
  const [posts, setPosts] = useState<PostData[]>([]);

  const getPosts = async () => {
    try {
      const data = await apiClient.get<PaginatedResponse<PostData>>(COMMUNITY[postListType]);
      setPosts(data.results);
      return data;
    } catch (error) {
      console.error("Couldn't get posts: ", error);
      throw error;
    }
  };

  useEffect(() => {
    getPosts();
  }, [postListType, refreshTrigger]);

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
        />
      ))}
    </div>
  );
};

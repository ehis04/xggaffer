import "./css/PostList.css";
import { Post } from "./Post";
import type { PostData } from "./Post";
import {
  Api_Endpoints,
  authenticatedFetch,
} from "../../services/api/AuthenticateUserApi";
import { useState, useEffect } from "react";

interface PostListProps {
  postList?: PostData[];
  refreshTrigger?: number;
  onLike?: (postId: number) => void;
  onComment?: (postId: number) => void;
  onProfileClick?: (username: string) => void;
  onPostClick?: (postId: number) => void;
}

export interface Post {
  id: number;
  author: number;
  text_body: string;
  created_at: string;
  no_of_likes: number;
  no_of_comments: number;
  visibility: string;
  post_tags: Array<{
    hashtag: { id: number; body: string; usage_count: number };
  }>;
  is_liked: boolean;
  hashtags: string[];
  time_since_posted: string;
}

export const PostList: React.FC<PostListProps> = ({
  refreshTrigger = 0,
  onComment,
  onProfileClick,
  onPostClick,
  postListType = "EXPLORE_POSTS",
}) => {
  const [posts, setPosts] = useState<Post[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [nextPage, setNextPage] = useState<string | null>(null);
  const [previousPage, setPreviousPage] = useState<string | null>(null);

  const getPosts = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await authenticatedFetch(Api_Endpoints[postListType], {
        method: "GET",
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch posts: ${response.status}`);
      }

      const data = await response.json();
      setPosts(data.results);
      setNextPage(data.next);
      setPreviousPage(data.previous);
      console.log(data);
      return data;
    } catch (error) {
      console.error("Couldn't get posts: ", error);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    getPosts();
  }, [postListType, refreshTrigger]);

  const postsPB = posts.filter((item: any) => {
    if ("type" in item) {
      return item.type === "post";
    }

    return true;
  });

  if (!posts || posts.length === 0) {
    return (
      <div className="post-list-container-empty">
        <p> No posts available </p>
      </div>
    );
  }

  const handleLike = async (postId: number) => {
    const response = await authenticatedFetch(Api_Endpoints.LIKE_POST(postId), {
      method: "POST",
    });
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

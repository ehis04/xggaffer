import './css/PostList.css';
import { Post } from './Post';
import type { PostData } from './Post';
import { communityApi, type Post as ApiPost } from '../../services/api/communityApi';
import { useState, useEffect } from 'react';

interface PostListProps {
  onComment?: (postId: number) => void;
  onProfileClick?: (username: string) => void;
  onPostClick?: (postId: number) => void;
}

// Transform API Post to component PostData
const apiPostToPostData = (apiPost: ApiPost): PostData => ({
  id: apiPost.id,
  author: {
    id: apiPost.author.id,
    username: apiPost.author.username,
  },
  text_body: apiPost.text_body,
  created_at: apiPost.created_at,
  no_of_likes: apiPost.no_of_likes,
  no_of_comments: apiPost.no_of_comments,
  visibility: apiPost.visibility,
  moderation_status: 'OK',
  type: 'post',
  hashtags: apiPost.hashtags,
  is_liked: apiPost.is_liked,
});

export const PostList: React.FC<PostListProps> = ({
  onComment,
  onProfileClick,
  onPostClick,
}) => {
  const [posts, setPosts] = useState<PostData[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const getPosts = async () => {
    setLoading(true);
    setError(null);

    try {
      const data = await communityApi.explorePosts({ order_by: 'ranked' });
      // Transform API posts to component format
      setPosts(data.results.map(apiPostToPostData));
    } catch (err) {
      console.error("Couldn't get posts:", err);
      setError(err instanceof Error ? err.message : 'Failed to load posts');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    getPosts();
  }, []);

  const handleLike = async (postId: number) => {
    try {
      const result = await communityApi.likePost(postId);
      setPosts((prev) =>
        prev.map((post) =>
          post.id === postId
            ? {
                ...post,
                is_liked: result.liked,
                no_of_likes: result.no_of_likes,
              }
            : post
        )
      );
    } catch (err) {
      console.error('Error liking post:', err);
    }
  };

  if (loading) {
    return (
      <div className="post-list-container-empty">
        <p>Loading posts...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="post-list-container-empty">
        <p>{error}</p>
        <button onClick={getPosts}>Try Again</button>
      </div>
    );
  }

  if (posts.length === 0) {
    return (
      <div className="post-list-container-empty">
        <p>No posts available</p>
      </div>
    );
  }

  return (
    <div className="post-list-container">
      {posts.map((post) => (
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
import "./css/PostList.css";
import { Post } from "./Post";
import type { PostData } from "./Post";

interface PostListProps {
  postList: PostData[];
  onLike?: (postId: number) => void;
  onComment?: (postId: number) => void;
  onProfileClick?: (username: string) => void;
  onPostClick?: (postId: number) => void;
}

export const PostList: React.FC<PostListProps> = ({ postList,
  onLike,
  onComment,
  onProfileClick,
  onPostClick,
 }) => {

    const posts = postList.filter((item: any) => {
        if ('type' in item) {
            return item.type === 'post';
        }

        return true
    })

  if (!posts || posts.length === 0) {
    return (
      <div className="post-list-container-empty">
        <p> No posts available </p>
      </div>
    );
  }

  return (
    <div className="post-list-container">
        {posts.map((post) => (
            <Post key={post.id}
          post={post}
          onLike={onLike}
          onComment={onComment}
          onProfileClick={onProfileClick}
          onPostClick={onPostClick} />
        ))}
    </div>
  )
};

import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Post } from './Post';
import { communityApi, type Comment } from '../../services/api/communityApi';
import type { PostData } from './Post';
import './css/PostDetail.css';

export const PostDetail = () => {
  const { postId } = useParams<{ postId: string }>();
  const navigate = useNavigate();

  const [post, setPost] = useState<PostData | null>(null);
  const [comments, setComments] = useState<PostData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchPostAndComments = async () => {
      if (!postId) return;

      try {
        setLoading(true);
        setError(null);

        const postData = await communityApi.getPost(parseInt(postId));

        const transformedPost: PostData = {
          id: postData.id,
          author: {
            id: postData.author.id,
            username: postData.author.username,
          },
          text_body: postData.text_body,
          created_at: postData.created_at,
          no_of_likes: postData.no_of_likes,
          no_of_comments: postData.no_of_comments,
          visibility: postData.visibility,
          moderation_status: 'OK',
          type: 'post',
          is_liked: postData.is_liked,
        };

        setPost(transformedPost);

        const commentsData = await communityApi.getPostComments(parseInt(postId));
        const transformedComments = commentsToPostData(commentsData);
        setComments(transformedComments);
      } catch (err) {
        console.error("Couldn't get post details:", err);
        setError(err instanceof Error ? err.message : 'Failed to load post');
      } finally {
        setLoading(false);
      }
    };

    fetchPostAndComments();
  }, [postId]);

  // Transform API Comment[] to component PostData[]
  const commentsToPostData = (comments: Comment[]): PostData[] => {
    const result: PostData[] = [];

    comments.forEach((comment) => {
      result.push({
        id: comment.id,
        author: {
          id: comment.author.id,
          username: comment.author.username,
        },
        post_id: comment.post,
        parent_id: comment.parent || undefined,
        text_body: comment.text_body,
        created_at: comment.created_at,
        no_of_likes: comment.no_of_likes,
        no_of_comments: 0,
        no_of_replies: comment.no_of_replies,
        visibility: 'PB',
        moderation_status: 'OK',
        type: 'comment',
        is_liked: false,
      });

      if (comment.children && comment.children.length > 0) {
        comment.children.forEach((reply) => {
          result.push({
            id: reply.id,
            author: {
              id: reply.author.id,
              username: reply.author.username,
            },
            post_id: reply.post,
            parent_id: reply.parent || undefined,
            text_body: reply.text_body,
            created_at: reply.created_at,
            no_of_likes: reply.no_of_likes,
            no_of_comments: 0,
            no_of_replies: reply.no_of_replies,
            visibility: 'PB',
            moderation_status: 'OK',
            type: 'comment',
            is_liked: false,
          });
        });
      }
    });

    return result;
  };

  const handleLike = async (id: number) => {
    try {
      if (id === post?.id) {
        const result = await communityApi.likePost(id);
        setPost((prev) =>
          prev
            ? {
                ...prev,
                is_liked: result.liked,
                no_of_likes: result.no_of_likes,
              }
            : null
        );
      } else {
        const result = await communityApi.likeComment(id);
        setComments((prev) =>
          prev.map((comment) =>
            comment.id === id
              ? {
                  ...comment,
                  is_liked: result.liked,
                  no_of_likes: result.no_of_likes,
                }
              : comment
          )
        );
      }
    } catch (err) {
      console.error('Error liking:', err);
    }
  };

  const handleComment = () => {
    console.log('comment clicked');
  };

  const handleProfileClick = () => {
    console.log('profile clicked');
  };

  const handlePostClick = () => {
    console.log('post clicked');
  };

  const topLevelComments = comments.filter((c) => !c.parent_id);
  const repliesMap = new Map<number, PostData[]>();

  comments.forEach((comment) => {
    if (comment.parent_id) {
      const replies = repliesMap.get(comment.parent_id) || [];
      replies.push(comment);
      repliesMap.set(comment.parent_id, replies);
    }
  });

  if (loading) {
    return (
      <div className="post-detail-container">
        <div className="loading">Loading...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="post-detail-container">
        <div className="error-message">{error}</div>
      </div>
    );
  }

  return (
    <div className="post-detail-container">
      <div className="post-detail-header">
        <button className="back-button" onClick={() => navigate(-1)}>
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="16"
            height="16"
            fill="currentColor"
            viewBox="0 0 16 16"
          >
            <path
              fillRule="evenodd"
              d="M15 8a.5.5 0 0 0-.5-.5H2.707l3.147-3.146a.5.5 0 1 0-.708-.708l-4 4a.5.5 0 0 0 0 .708l4 4a.5.5 0 0 0 .708-.708L2.707 8.5H14.5A.5.5 0 0 0 15 8"
            />
          </svg>
        </button>
        <h2>Post</h2>
      </div>

      <div className="post-detail-main">
        {post && (
          <Post
            post={post}
            onLike={handleLike}
            onComment={handleComment}
            onProfileClick={handleProfileClick}
            onPostClick={handlePostClick}
          />
        )}
      </div>

      <div className="comment-section">
        {topLevelComments.length === 0 ? (
          <div className="empty-comments">
            <p>No comments! Be the first to comment!</p>
          </div>
        ) : (
          <div className="comment-list">
            {topLevelComments.map((comment) => {
              const replies = repliesMap.get(comment.id) || [];
              return (
                <div key={comment.id} className="comment-thread">
                  <Post
                    post={comment}
                    onLike={handleLike}
                    onComment={handleComment}
                    onProfileClick={handleProfileClick}
                    onPostClick={handlePostClick}
                  />
                  {replies.length > 0 && (
                    <div className="replies-container">
                      {replies.map((reply) => (
                        <Post
                          key={reply.id}
                          post={reply}
                          onLike={handleLike}
                          onComment={handleComment}
                          onProfileClick={handleProfileClick}
                          onPostClick={handlePostClick}
                          showReplyLine={true}
                          depth={1}
                        />
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
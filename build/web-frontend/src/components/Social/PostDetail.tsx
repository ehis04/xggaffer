import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Post } from "./Post";
import {
  Api_Endpoints,
  authenticatedFetch,
} from "../../services/api/AuthenticateUserApi";
import type { PostData } from "./Post";
import './css/PostDetail.css';

interface CommentResponse {
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
}

interface PostResponse {
  id: number;
  author: {
    id: number;
    username: string;
    email: string;
  };
  text_body: string;
  created_at: string;
  no_of_likes: number;
  no_of_comments: number;
  visibility: "PB" | "F" | "PR";
  attachments_count: number;
}

export const PostDetail = () => {
  const { postId } = useParams<{ postId: string }>();
  const navigate = useNavigate();

  const [post, setPost] = useState<PostData | null>(null);
  const [comments, setComments] = useState<PostData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [commentText, setCommentText] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    const fetchPostAndComments = async () => {
    if (!postId) return;

    try {
      setLoading(true);
      setError(null);

      const postResponse = await authenticatedFetch(
        Api_Endpoints.POST_ID(parseInt(postId)),
        {
          method: "GET",
        }
      );

      if (!postResponse.ok) {
        throw new Error("Failed to get post");
      }

      const postData: PostResponse = await postResponse.json();

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
        moderation_status: "OK",
        type: "post",
        is_liked: false, // TODO: fetch actual like status
      };

      setPost(transformedPost);

      const commentResponse = await authenticatedFetch(
        Api_Endpoints.POST_COMMENTS(parseInt(postId)),
        {
          method: "GET",
        }
      );

      if (!commentResponse.ok) {
        throw new Error(`Couldn't get comments: ${commentResponse.status}`);
      }

      const commentsData = await commentResponse.json();
      console.log(commentsData);
      const transformedComments = commentsToPost(commentsData.results || []);
      setComments(transformedComments);
    } catch (error) {
      console.error("Couldn't get post details: ", error);
    } finally {
      setLoading(false);
    }
  };
  fetchPostAndComments();
  }, [postId]);

  const commentsToPost = (comments: CommentResponse[]): PostData[] => {
    const result: PostData[] = [];

    comments.forEach((comment) => {
      result.push({
        id: comment.id,
        author: {
          id: 0,
          username: comment.author,
        },
        post_id: comment.post,
        parent_id: comment.parent || undefined,
        text_body: comment.text_body,
        created_at: comment.created_at,
        no_of_likes: comment.no_of_likes,
        no_of_comments: 0,
        no_of_replies: comment.no_of_replies,
        visibility: "PB",
        moderation_status: "OK",
        type: "comment",
        is_liked: false, // TODO: fetch actual like status
      });

      if (comment.children && comment.children.length > 0) {
        comment.children.forEach((reply) => {
          result.push({
            id: reply.id,
            author: {
              id: 0,
              username: reply.author,
            },
            post_id: reply.post,
            parent_id: reply.parent || undefined,
            text_body: reply.text_body,
            created_at: reply.created_at,
            no_of_likes: reply.no_of_likes,
            no_of_comments: 0,
            no_of_replies: reply.no_of_replies,
            visibility: "PB",
            moderation_status: "OK",
            type: "comment",
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
        await authenticatedFetch(
          Api_Endpoints.LIKE_POST(id),
          {
            method: "POST",
          }
        );
      } else {
        await authenticatedFetch(
          Api_Endpoints.LIKE_COMMENT(id),
          { method: "POST" }
        );
      }
    //   await fetchPostAndComments();
    } catch (error) {
      console.error("Error liking: ", error);
    }
  };

  const handleComment = () => {
    console.log("comment clicked");
  }

  const handleProfileClick = () => {
    console.log("profile clicked");
  }

  const handlePostClick = () => {
    console.log("post clicked");
  }

  const topLevelComments = comments.filter((c) => !c.parent_id);
  const repliesMap = new Map<number, PostData[]>();

  comments.forEach((comment) => {
    if (comment.parent_id) {
      const replies = repliesMap.get(comment.parent_id) || [];
      replies.push(comment);
      repliesMap.set(comment.parent_id, replies);
    }
  });

  console.log("Rendering - loading:", loading, "error:", error, "post:", post);

  return (
    <div className="post-detail-container">
      <div className="post-detail-header">
        <button className="back-button" onClick={() => navigate(-1)}>
          <svg></svg>
        </button>
        <h2> Post </h2>
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
            <p> No comments! Be the first to comment! </p>
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

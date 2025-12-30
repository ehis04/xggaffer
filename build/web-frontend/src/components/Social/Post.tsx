import { useState } from "react";
import "./css/Post.css";

// This component is for comments, posts, replies. It is using the general name post to refer to everything

export interface PostAuthor {
  id: number;
  username?: string;
  profile_image?: string;
  display_name?: string;
}

export interface PostData {
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

export interface PostProps {
  post: PostData;
  onLike?: (postId: number) => void;
  onComment?: (postId: number) => void;
  onReply?: (id: number) => void;
  onProfileClick?: (username: string) => void;
  onPostClick?: (postId: number) => void;
  showReplyLine?: boolean;
  depth?: number;
}

export const Post: React.FC<PostProps> = ({
  post,
  onLike,
  onComment,
  onProfileClick,
  onPostClick,
  showReplyLine = false,
  depth = 0,
}) => {
  const [isLiked, setIsLiked] = useState(post.is_liked || false);
  const [likeCount, setLikeCount] = useState(post.no_of_likes);

  const isComment = post.type === "comment";
  const commentCount = isComment ? post.no_of_replies : post.no_of_comments;

  const formatTime = (dateString: string): string => {
    const now = new Date();
    const postDate = new Date(dateString);
    const diffInSec = Math.floor((now.getTime() - postDate.getTime()) / 1000);

    if (diffInSec < 60) return `${diffInSec}s`;
    if (diffInSec < 3600) return `${Math.floor(diffInSec / 60)}m`;
    if (diffInSec < 86400) return `${Math.floor(diffInSec / 3600)}h`;
    if (diffInSec < 604800) return `${Math.floor(diffInSec / 86400)}d`;

    return postDate.toLocaleDateString("en-UK", {
      month: "short",
      day: "numeric",
    });
  };

  //TODO maybe add number formatting for numbers over 1m or 1000

  const handleLike = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsLiked(!isLiked);
    setLikeCount(isLiked ? likeCount - 1 : likeCount + 1);
    if (onLike) onLike(post.id);
  };

  const handleComment = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (onComment) onComment(post.id);
  };

  const handleProfileClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (onProfileClick) onProfileClick(post.author.username);
  };

  const handlePostClick = () => {
    if (onPostClick) onPostClick(post.id);
  };

  const renderTextWithLinks = (text: string) => {
    const parts = text.split(/(\s+|#\w+|@\w+)/g);

    return parts.map((part, index) => {
      if (part.startsWith("#")) {
        return (
          <span key={index} className="post-hashtag">
            {part}
          </span>
        );
      }
      if (part.startsWith("@")) {
        return (
          <span key={index} className="post-mention">
            {part}
          </span>
        );
      }
      return <span key={index}>{part}</span>;
    });
  };
  return (
    <article
      className={`post-container ${isComment ? "comment" : "post"} ${
        showReplyLine ? "has-reply-line" : ""
      }`}
      onClick={handlePostClick}
      style={{ paddingLeft: `${depth * 40}px` }}
    >
      {showReplyLine && <div className="reply-line" />}
      <div className="profile-picture" onClick={handleProfileClick}>
        {post.author.profile_image ? (
          <img src={post.author.profile_image} alt={post.author.username || "User"} />
        ) : (
          <div className="profile-picture-placeholder">
            {post.author.username ? post.author.username[0].toUpperCase() : "?"}
          </div>
        )}
      </div>

      <div className="post-content">
        <div className="post-header">
          <div className="post-author-details" onClick={handleProfileClick}>
            <span className="post-author-name">@{post.author.username || "User"}</span>
            <span className="post-separator">.</span>
            <span className="post-timestamp">
              {formatTime(post.created_at)}
            </span>
          </div>

          <button className="post-more-btn" aria-label="More options">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
              <circle cx="12" cy="5" r="2" />
              <circle cx="12" cy="12" r="2" />
              <circle cx="12" cy="19" r="2" />
            </svg>
          </button>
        </div>

        <div className="post-text">{renderTextWithLinks(post.text_body)}</div>
        <div className="post-actions">
          <button
            className="post-action-btn"
            onClick={handleComment}
            aria-label={isComment ? "Reply" : "Comment"}
          >
            <div className="post-action-icon">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="16"
                height="16"
                fill="currentColor"
                className="bi bi-chat-left"
                viewBox="0 0 16 16"
              >
                <path d="M14 1a1 1 0 0 1 1 1v8a1 1 0 0 1-1 1H4.414A2 2 0 0 0 3 11.586l-2 2V2a1 1 0 0 1 1-1zM2 0a2 2 0 0 0-2 2v12.793a.5.5 0 0 0 .854.353l2.853-2.853A1 1 0 0 1 4.414 12H14a2 2 0 0 0 2-2V2a2 2 0 0 0-2-2z" />
              </svg>
            </div>
            {commentCount && commentCount > 0 && (
              <span className="post-action-count">{commentCount}</span>
            )}
          </button>

          <button
            className={`post-action-btn ${isLiked ? "liked" : ""}`}
            onClick={handleLike}
          >
            <div className="post-action-icon">
              {isLiked ? (
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="16"
                  height="16"
                  fill="currentColor"
                  className="bi bi-heart-fill"
                  viewBox="0 0 16 16"
                >
                  <path
                    fill-rule="evenodd"
                    d="M8 1.314C12.438-3.248 23.534 4.735 8 15-7.534 4.736 3.562-3.248 8 1.314"
                  />
                </svg>
              ) : (
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="16"
                  height="16"
                  fill="currentColor"
                  className="bi bi-heart"
                  viewBox="0 0 16 16"
                >
                  <path d="m8 2.748-.717-.737C5.6.281 2.514.878 1.4 3.053c-.523 1.023-.641 2.5.314 4.385.92 1.815 2.834 3.989 6.286 6.357 3.452-2.368 5.365-4.542 6.286-6.357.955-1.886.838-3.362.314-4.385C13.486.878 10.4.28 8.717 2.01zM8 15C-7.333 4.868 3.279-3.04 7.824 1.143q.09.083.176.171a3 3 0 0 1 .176-.17C12.72-3.042 23.333 4.867 8 15" />
                </svg>
              )}
            </div>
            {likeCount > 0 && (
              <span className="post-action-count">{likeCount}</span>
            )}
          </button>
        </div>
      </div>
    </article>
  );
};

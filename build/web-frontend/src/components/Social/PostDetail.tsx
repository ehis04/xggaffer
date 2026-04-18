import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Post } from "./Post";
import apiClient from "../../services/api/client";
import type { PostData } from "./Post";
import "./css/PostDetail.css";
import type { PostResponse, CommentResponse } from "./types/SocialTypes";
import { commentToPostData, flattenComments } from "./functions/SocialHelpers";
import { ProfileButton } from "../Buttons/ProfileButton";
import type { UserData } from "../Navigation/SideBar";
import { getUserProfile } from "../Navigation/functions/getUserProfile";
import { COMMUNITY } from "../../services/api/endpoints";
import type { PaginatedResponse } from "../../services/api/communityApi";

const BackArrow = () => (
  <svg
    width="20"
    height="20"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2.5"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M19 12H5M12 5l-7 7 7 7" />
  </svg>
);

export const PostDetail = () => {
  const { postId } = useParams<{ postId: string }>();
  const navigate = useNavigate();

  const [post, setPost] = useState<PostData | null>(null);
  const [comments, setComments] = useState<PostData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [userData, setUserData] = useState<UserData | null>(null);

  const [replyText, setReplyText] = useState("");
  const [replyingToId, setReplyingToId] = useState<number | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    getUserProfile(setUserData);
  }, []);

  useEffect(() => {
    if (!postId) return;

    const load = async () => {
      try {
        setLoading(true);
        setError(null);

        const [postData, commentData] = await Promise.all([
          apiClient.get<PostResponse>(COMMUNITY.POST(parseInt(postId))),
          apiClient.get<PaginatedResponse<CommentResponse>>(COMMUNITY.POST_COMMENTS(parseInt(postId))),
        ]);

        setPost({
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
          is_liked: postData.is_liked ?? false,
        });

        setComments(flattenComments(commentData.results ?? []));
      } catch (err) {
        console.error(err);
        setError("Couldn't load this post. Please try again.");
      } finally {
        setLoading(false);
      }
    };

    load();
  }, [postId]);

  const handleReplyChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setReplyText(e.target.value);
    const ta = e.target;
    ta.style.height = "auto";
    ta.style.height = `${ta.scrollHeight}px`;
  };

  const handleSubmitReply = async () => {
    if (!postId || !replyText.trim() || isSubmitting) return;
    setIsSubmitting(true);
    try {
      const body: Record<string, unknown> = { text_body: replyText.trim() };
      if (replyingToId) body.parent = replyingToId;

      const newComment = await apiClient.post<CommentResponse>(
        COMMUNITY.CREATE_COMMENT(parseInt(postId)),
        body,
      );
      setComments((prev) => [commentToPostData(newComment), ...prev]);
      setReplyText("");
      setReplyingToId(null);
      if (textareaRef.current) textareaRef.current.style.height = "auto";

      setPost((p) => (p ? { ...p, no_of_comments: p.no_of_comments + 1 } : p));
    } catch (err) {
      console.error(err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleLike = async (id: number, type: "post" | "comment") => {
    try {
      const endpoint =
        type === "post"
          ? COMMUNITY.LIKE_POST(id)
          : COMMUNITY.LIKE_COMMENT(id);
      await apiClient.post(endpoint);
    } catch (err) {
      console.error("Like error:", err);
    }
  };

  const handleComment = (id: number) => {
    setReplyingToId(id === post?.id ? null : id);
    setTimeout(() => textareaRef.current?.focus(), 50);
  };

  const handleProfileClick = (username: string) =>
    navigate(`/profile/${username}`);
  const handlePostClick = () => {};

  const topLevel = comments.filter((c) => !c.parent_id);
  const repliesMap = new Map<number, PostData[]>();
  comments.forEach((c) => {
    if (c.parent_id) {
      const arr = repliesMap.get(c.parent_id) ?? [];
      arr.push(c);
      repliesMap.set(c.parent_id, arr);
    }
  });

  const replyingToUsername = replyingToId
    ? comments.find((c) => c.id === replyingToId)?.author.username
    : post?.author.username;

  return (
    <div className="post-detail-root">
      <header className="pd-header">
        <button
          className="ptb-back-btn"
          onClick={() => navigate(-1)}
          aria-label="Go back"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="15 18 9 12 15 6" />
          </svg>
        </button>
        <span className="pd-header-title">Post</span>
      </header>

      <main className="pd-main">
        {loading && (
          <div className="pd-loading">
            <div className="pd-spinner" />
          </div>
        )}

        {error && !loading && (
          <div className="pd-error">
            <p>{error}</p>
            <button
              className="pd-retry-btn"
              onClick={() => window.location.reload()}
            >
              Try again
            </button>
          </div>
        )}

        {!loading && !error && post && (
          <>
            <Post
              post={post}
              onLike={(id) => handleLike(id, "post")}
              onComment={handleComment}
              onProfileClick={handleProfileClick}
              onPostClick={handlePostClick}
            />

            <div className="pd-composer">
              <div className="pd-composer-inner">
                <div className="pd-composer-avatar">
                  {userData && (
                    <ProfileButton
                      username={userData.username}
                      size="medium"
                      onClick={handleProfileClick}
                    />
                  )}
                </div>
                <div className="pd-composer-field">
                  {replyingToId && replyingToUsername && (
                    <div className="pd-replying-to">
                      Replying to{" "}
                      <span className="pd-replying-name">
                        @{replyingToUsername}
                      </span>
                      <button
                        className="pd-cancel-reply"
                        onClick={() => setReplyingToId(null)}
                        aria-label="Cancel reply"
                      >
                        ×
                      </button>
                    </div>
                  )}
                  <textarea
                    ref={textareaRef}
                    className="pd-textarea"
                    placeholder={
                      replyingToId ? "Write your reply…" : "Post your reply…"
                    }
                    value={replyText}
                    onChange={handleReplyChange}
                    rows={1}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && (e.metaKey || e.ctrlKey))
                        handleSubmitReply();
                    }}
                  />
                  <div className="pd-composer-footer">
                    <span
                      className={`pd-char-count ${replyText.length > 260 ? "warn" : ""}`}
                    >
                      {replyText.length > 0 ? `${280 - replyText.length}` : ""}
                    </span>
                    <button
                      className="pd-submit-btn"
                      onClick={handleSubmitReply}
                      disabled={
                        !replyText.trim() ||
                        isSubmitting ||
                        replyText.length > 280
                      }
                    >
                      {isSubmitting ? "Posting…" : "Reply"}
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <section className="pd-comments-section">
              {topLevel.length === 0 ? (
                <div className="pd-empty-state">
                  <p className="pd-empty-title">No replies yet</p>
                </div>
              ) : (
                topLevel.map((comment) => {
                  const replies = repliesMap.get(comment.id) ?? [];
                  return (
                    <div key={comment.id} className="pd-thread">
                      <Post
                        post={comment}
                        onLike={(id) => handleLike(id, "comment")}
                        onComment={handleComment}
                        onProfileClick={handleProfileClick}
                        showReplyLine={replies.length > 0}
                      />
                      {replies.map((reply) => (
                        <Post
                          key={reply.id}
                          post={reply}
                          onLike={(id) => handleLike(id, "comment")}
                          onComment={handleComment}
                          onProfileClick={handleProfileClick}
                          depth={1}
                        />
                      ))}
                    </div>
                  );
                })
              )}
            </section>
          </>
        )}
      </main>
    </div>
  );
};

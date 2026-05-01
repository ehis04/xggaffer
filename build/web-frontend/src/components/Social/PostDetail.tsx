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
import communityApi, { type PaginatedResponse } from "../../services/api/communityApi";

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
            profile_image: postData.author.profile_image,
          },
          text_body: postData.text_body,
          created_at: postData.created_at,
          no_of_likes: postData.no_of_likes,
          no_of_comments: postData.no_of_comments,
          visibility: postData.visibility,
          moderation_status: postData.moderation_status,
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

  const handleDelete = async (postToDelete: PostData) => {
    try {
      if (postToDelete.type === "post") {
        await communityApi.deletePost(postToDelete.id);
        navigate("/social");
        return;
      }

      await communityApi.deleteComment(postToDelete.id);
      const removedIds = new Set<number>([postToDelete.id]);
      comments.forEach((comment) => {
        if (comment.parent_id === postToDelete.id) {
          removedIds.add(comment.id);
        }
      });

      setComments((currentComments) =>
        currentComments.filter((comment) => !removedIds.has(comment.id))
      );
      setPost((currentPost) =>
        currentPost
          ? {
              ...currentPost,
              no_of_comments: Math.max(0, currentPost.no_of_comments - removedIds.size),
            }
          : currentPost
      );
      if (replyingToId && removedIds.has(replyingToId)) {
        setReplyingToId(null);
      }
    } catch (err) {
      console.error("Delete error:", err);
    }
  };

  const handleReport = async (postToReport: PostData) => {
    try {
      const result = await communityApi.reportPost(postToReport.id);
      if (result.moderation_status === "UR") {
        navigate("/social");
      }
    } catch (err) {
      console.error("Report error:", err);
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
              onDelete={handleDelete}
              onReport={handleReport}
            />

            <div className="pd-composer">
              <div className="pd-composer-inner">
                <div className="pd-composer-avatar">
                  {userData && (
                    <ProfileButton
                      username={userData.username}
                      profileImage={userData.profile_image ?? undefined}
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
                        onDelete={handleDelete}
                      />
                      {replies.map((reply) => (
                        <Post
                          key={reply.id}
                          post={reply}
                          onLike={(id) => handleLike(id, "comment")}
                          onComment={handleComment}
                          onProfileClick={handleProfileClick}
                          depth={1}
                          onDelete={handleDelete}
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

import type { CommentResponse } from "../types/SocialTypes";
import type { PostData } from "../Post";

export const commentToPostData = (c: CommentResponse): PostData => ({
  id: c.id,
  author: { id: 0, username: c.author },
  post_id: c.post,
  parent_id: c.parent ?? undefined,
  text_body: c.text_body,
  created_at: c.created_at,
  no_of_likes: c.no_of_likes,
  no_of_comments: 0,
  no_of_replies: c.no_of_replies,
  visibility: "PB",
  moderation_status: "OK",
  type: "comment",
  is_liked: c.is_liked ?? false,
});

export const flattenComments = (list: CommentResponse[]): PostData[] => {
  const result: PostData[] = [];
  list.forEach(c => {
    result.push(commentToPostData(c));
    c.children?.forEach(r => result.push(commentToPostData(r)));
  });
  return result;
};

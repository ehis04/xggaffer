import { COMMUNITY } from "../../../services/api/endpoints";

type CommunityPostTypes = "EXPLORE_POSTS" | "FOLLOWING_POSTS";
type UserPostTypes = "GET_USERS_POSTS";

export type PostListType = CommunityPostTypes | UserPostTypes;

export const getPostsUrl = (type: PostListType, username?: string): string => {
  switch (type) {
    case "GET_USERS_POSTS":
      if (!username) throw new Error("PostList: username is required for GET_USERS_POSTS");
      return COMMUNITY.GET_USERS_POSTS(username);
    case "FOLLOWING_POSTS":
      return COMMUNITY.FOLLOWING_POSTS;
    case "EXPLORE_POSTS":
    default:
      return COMMUNITY.EXPLORE_POSTS;
  }
};
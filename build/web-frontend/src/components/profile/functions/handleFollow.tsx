import apiClient from "../../../services/api/client";
import { USERS } from "../../../services/api/endpoints";
import type { ProfileData, FollowStatus } from "../types/ProfileTypes";
import type { Dispatch, SetStateAction } from "react";

const handleFollow = async (
  username: string,
  followStatus: FollowStatus | null,
  setFollowStatus: Dispatch<SetStateAction<FollowStatus | null>>,
  setUserData: Dispatch<SetStateAction<ProfileData | null>>,
): Promise<void> => {
  if (!username) return;

  try {
    const shouldRemove = followStatus?.is_following || followStatus?.follow_request_pending;
    const response = shouldRemove
      ? await apiClient.delete<{
          following: boolean;
          follow_request_pending?: boolean;
        }>(USERS.FOLLOW(username))
      : await apiClient.post<{
          following: boolean;
          follow_request_pending?: boolean;
        }>(USERS.FOLLOW(username));

    setUserData((prev) => {
      if (!prev) return prev;
      const wasFollowing = Boolean(followStatus?.is_following);
      const nowFollowing = Boolean(response.following);
      if (wasFollowing === nowFollowing) return prev;
      return {
        ...prev,
        followers_count: prev.followers_count + (nowFollowing ? 1 : -1),
      };
    });

    setFollowStatus((prev) =>
      prev
        ? {
            ...prev,
            is_following: Boolean(response.following),
            follow_request_pending: Boolean(response.follow_request_pending),
          }
        : {
            is_following: Boolean(response.following),
            followed_by: false,
            follow_request_pending: Boolean(response.follow_request_pending),
          },
    );
  } catch (error) {
    console.error("Failed to follow/unfollow user:", error);
  }
};

export default handleFollow;

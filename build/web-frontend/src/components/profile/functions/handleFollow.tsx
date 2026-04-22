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
    await apiClient.post(USERS.FOLLOW(username));

    setUserData((prev) => {
      if (!prev) return prev;
      const nowFollowing = !followStatus?.is_following;
      return {
        ...prev,
        followers_count: prev.followers_count + (nowFollowing ? 1 : -1),
      };
    });

    setFollowStatus((prev) =>
      prev
        ? { ...prev, is_following: !prev.is_following }
        : { is_following: true, followed_by: false, follow_request_pending: false },
    );
  } catch (error) {
    console.error("Failed to follow/unfollow user:", error);
  }
};

export default handleFollow;
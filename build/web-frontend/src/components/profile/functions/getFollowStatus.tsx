import apiClient from "../../../services/api/client";
import { USERS } from "../../../services/api/endpoints";
import type { FollowStatus } from "../types/ProfileTypes";
import type { Dispatch, SetStateAction } from "react";

export const getFollowStatus = async (
  setFollowStatus: Dispatch<SetStateAction<FollowStatus | null>>,
  username: string,
): Promise<void> => {
  try {
    const data = await apiClient.get<FollowStatus>(
      USERS.FOLLOW_STATUS(username),
    );
    setFollowStatus({
      is_following: data.is_following,
      followed_by: data.followed_by,
    });
  } catch (error) {
    console.error("Couldn't get follow status:", error);
  }
};

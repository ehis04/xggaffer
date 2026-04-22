import apiClient from "../../../services/api/client";
import { USERS } from "../../../services/api/endpoints";
import type { UserData } from "../SideBar";

export const getUserProfile = async (
  setUserData: (userData: UserData) => void,
) => {
  try {
    const data = await apiClient.get<UserData>(USERS.PROFILE);
    setUserData({
      user: data.user,
      username: data.user.username,
      display_name: data.display_name,
      bio: data.bio,
      followers_count: data.followers_count,
      following_count: data.following_count,
      gender: data.gender,
      // profile_image: data.profile_image,
      roles: data.roles ?? [],
      visibility: data.visibility,
      created_at: data.created_at,
    });
  } catch (error) {
    console.error("Counldn't get user's profile", error);
  }
};

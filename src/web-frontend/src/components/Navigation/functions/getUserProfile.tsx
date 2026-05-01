import apiClient from "../../../services/api/client";
import { USERS } from "../../../services/api/endpoints";
import type { UserData } from "../SideBar";

const PROFILE_RETRY_COOLDOWN_MS = 5000;

let cachedUserData: UserData | null = null;
let pendingUserProfileRequest: Promise<UserData | null> | null = null;
let lastProfileFetchFailureAt = 0;

const mapUserData = (data: UserData): UserData => ({
  user: data.user,
  username: data.user.username,
  display_name: data.display_name,
  bio: data.bio,
  followers_count: data.followers_count,
  following_count: data.following_count,
  gender: data.gender,
  date_of_birth: data.date_of_birth,
  profile_image: data.profile_image,
  roles: data.roles ?? [],
  visibility: data.visibility,
  created_at: data.created_at,
});

export const getUserProfile = async (
  setUserData: (userData: UserData) => void,
) => {
  if (cachedUserData) {
    setUserData(cachedUserData);
    return;
  }

  if (Date.now() - lastProfileFetchFailureAt < PROFILE_RETRY_COOLDOWN_MS) {
    return;
  }

  try {
    if (!pendingUserProfileRequest) {
      pendingUserProfileRequest = apiClient
        .get<UserData>(USERS.PROFILE)
        .then((data) => {
          cachedUserData = mapUserData(data);
          lastProfileFetchFailureAt = 0;
          return cachedUserData;
        })
        .catch((error) => {
          lastProfileFetchFailureAt = Date.now();
          console.error("Couldn't get user's profile", error);
          return null;
        })
        .finally(() => {
          pendingUserProfileRequest = null;
        });
    }

    const userData = await pendingUserProfileRequest;
    if (userData) {
      setUserData(userData);
    }
  } catch (error) {
    lastProfileFetchFailureAt = Date.now();
    console.error("Couldn't get user's profile", error);
  }
};

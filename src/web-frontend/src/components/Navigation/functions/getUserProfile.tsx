import apiClient from "../../../services/api/client";
import { USERS } from "../../../services/api/endpoints";
import type { UserData } from "../SideBar";

const PROFILE_RETRY_COOLDOWN_MS = 5000;

let cachedUserData: UserData | null = null;
let pendingUserProfileRequest: Promise<UserData | null> | null = null;
let lastProfileFetchFailureAt = 0;
let profileSession = 0;
let profileOwner: number | null | undefined;

export function resetUserProfileCache(userId?: number | null) {
  profileSession += 1;
  profileOwner = userId;
  cachedUserData = null;
  pendingUserProfileRequest = null;
  lastProfileFetchFailureAt = 0;
}

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
  const session = profileSession;
  if (profileOwner === null) return;
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
          if (session !== profileSession || (profileOwner !== undefined && data.user.id !== profileOwner)) {
            return null;
          }
          cachedUserData = mapUserData(data);
          lastProfileFetchFailureAt = 0;
          return cachedUserData;
        })
        .catch((error) => {
          if (session !== profileSession) return null;
          lastProfileFetchFailureAt = Date.now();
          console.error("Couldn't get user's profile", error);
          return null;
        })
        .finally(() => {
          if (session === profileSession) pendingUserProfileRequest = null;
        });
    }

    const userData = await pendingUserProfileRequest;
    if (userData && session === profileSession) {
      setUserData(userData);
    }
  } catch (error) {
    if (session !== profileSession) return;
    lastProfileFetchFailureAt = Date.now();
    console.error("Couldn't get user's profile", error);
  }
};

import apiClient from "../../../services/api/client";
import { USERS } from "../../../services/api/endpoints";
import type { ProfileData } from "../types/ProfileTypes";
import type { Dispatch, SetStateAction } from "react";

export interface UpdateProfilePayload {
  display_name?: string;
  bio?: string;
  gender?: string;
  date_of_birth?: string | null;
  visibility?: "PB" | "PR";
  profile_picture?: File | null;
}

export const updateProfile = async (
  payload: UpdateProfilePayload,
  setUserData: Dispatch<SetStateAction<ProfileData | null>>,
): Promise<void> => {
  const hasProfilePicture = payload.profile_picture instanceof File;
  const body = hasProfilePicture
    ? new FormData()
    : ({} as Record<string, string | null>);

  const appendValue = (key: string, value: string | null) => {
    if (body instanceof FormData) {
      body.append(key, value ?? "");
      return;
    }

    body[key] = value;
  };

  if (payload.display_name !== undefined) appendValue("display_name", payload.display_name);
  if (payload.bio          !== undefined) appendValue("bio", payload.bio);
  if (payload.gender       !== undefined) appendValue("gender", payload.gender);
  if (payload.visibility   !== undefined) appendValue("visibility", payload.visibility);
  if (payload.date_of_birth !== undefined) appendValue("date_of_birth", payload.date_of_birth || null);
  if (body instanceof FormData && payload.profile_picture) {
    body.append("profile_picture", payload.profile_picture);
  }

  try {
    const data = await apiClient.patch<ProfileData>(USERS.PROFILE, body);

    setUserData((prev) =>
      prev
        ? {
            ...prev,
            display_name: data.display_name,
            bio:          data.bio,
            gender:       data.gender,
            date_of_birth: data.date_of_birth,
            visibility:   data.visibility,
            profile_image: data.profile_image,
          }
        : prev,
    );
  } catch (error) {
    console.error("Couldn't update profile:", error);
    throw error;
  }
};

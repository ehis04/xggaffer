import apiClient from "../../../services/api/client";
import { USERS } from "../../../services/api/endpoints";
import type { ProfileData } from "../types/ProfileTypes";
import type { Dispatch, SetStateAction } from "react";

export interface UpdateProfilePayload {
  display_name?: string;
  bio?: string;
  gender?: string;
  date_of_birth?: string;
  visibility?: "PUBLIC" | "FOLLOWERS" | "PRIVATE";
}

export const updateProfile = async (
  payload: UpdateProfilePayload,
  setUserData: Dispatch<SetStateAction<ProfileData | null>>,
): Promise<void> => {
  const body: Record<string, string> = {};

  if (payload.display_name !== undefined) body.display_name = payload.display_name;
  if (payload.bio          !== undefined) body.bio          = payload.bio;
  if (payload.gender       !== undefined) body.gender       = payload.gender;
  if (payload.visibility   !== undefined) body.visibility   = payload.visibility;
  if (payload.date_of_birth)             body.date_of_birth = payload.date_of_birth;

  try {
    const data = await apiClient.patch<ProfileData>(USERS.PROFILE, body);

    setUserData((prev) =>
      prev
        ? {
            ...prev,
            display_name: data.display_name,
            bio:          data.bio,
            gender:       data.gender,
            visibility:   data.visibility,
          }
        : prev,
    );
  } catch (error) {
    console.error("Couldn't update profile:", error);
    throw error;
  }
};
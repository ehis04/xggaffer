import apiClient from "../../../services/api/client";
import { USERS } from "../../../services/api/endpoints";
import type { ProfileData, ProfileRole } from "../types/ProfileTypes";
import type { Dispatch, SetStateAction } from "react";

type RoleKey = "C" | "P" | "R" | "F";

const ROLE_DISPLAY: Record<RoleKey, string> = {
  C: "Coach",
  P: "Player",
  R: "Referee",
  F: "Fan",
};

const ROLE_CODE_BY_KEY: Record<string, RoleKey> = {
  C: "C",
  COACH: "C",
  P: "P",
  PLAYER: "P",
  R: "R",
  REFEREE: "R",
  F: "F",
  FAN: "F",
};

const roleAlreadyPresent = (roles: ProfileRole[], key: RoleKey): boolean =>
  roles.some(
    (r) =>
      r.role.toUpperCase() === key ||
      r.role_display.toLowerCase() === ROLE_DISPLAY[key].toLowerCase(),
  );

const unwrapRoleResponse = (
  response: ProfileRole | { role: ProfileRole },
): ProfileRole => {
  if ("role_display" in response) {
    return response;
  }

  return response.role;
};

export const toggleRole = async (
  roleKey: string,
  isCurrentlyActive: boolean,
  setUserData: Dispatch<SetStateAction<ProfileData | null>>,
): Promise<void> => {
  const key = ROLE_CODE_BY_KEY[roleKey.toUpperCase()];

  if (!key) {
    throw new Error(`Unknown role: ${roleKey}`);
  }

  try {
    if (isCurrentlyActive) {
      await apiClient.delete<void>(`${USERS.ROLE}?role=${encodeURIComponent(key)}`);

      setUserData((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          roles: (prev.roles ?? []).filter(
            (r) =>
              r.role.toUpperCase() !== key &&
              r.role_display.toLowerCase() !== ROLE_DISPLAY[key].toLowerCase(),
          ),
        };
      });
    } else {
      const createdRole = await apiClient.post<ProfileRole | { role: ProfileRole }>(
        USERS.ROLE,
        { role: key },
      );

      setUserData((prev) => {
        if (!prev) return prev;

        if (roleAlreadyPresent(prev.roles ?? [], key)) return prev;

        const newRole = unwrapRoleResponse(createdRole);

        return {
          ...prev,
          roles: [...(prev.roles ?? []), newRole],
        };
      });
    }
  } catch (error) {
    console.error(`Couldn't toggle role ${key}:`, error);
    throw error;
  }
};

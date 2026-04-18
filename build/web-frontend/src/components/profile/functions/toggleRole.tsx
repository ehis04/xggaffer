import apiClient from "../../../services/api/client";
import { USERS } from "../../../services/api/endpoints";
import type { ProfileData, ProfileRole } from "../types/ProfileTypes";
import type { Dispatch, SetStateAction } from "react";

type RoleKey = "COACH" | "PLAYER" | "REFEREE" | "FAN";

const ROLE_DISPLAY: Record<RoleKey, string> = {
  COACH: "Coach",
  PLAYER: "Player",
  REFEREE: "Referee",
  FAN: "Fan",
};

const roleAlreadyPresent = (roles: ProfileRole[], key: RoleKey): boolean =>
  roles.some(
    (r) =>
      r.role.toUpperCase() === key ||
      r.role_display.toLowerCase() === ROLE_DISPLAY[key].toLowerCase(),
  );

export const toggleRole = async (
  roleKey: string,
  isCurrentlyActive: boolean,
  setUserData: Dispatch<SetStateAction<ProfileData | null>>,
): Promise<void> => {
  const key = roleKey.toUpperCase() as RoleKey;

  try {
    if (isCurrentlyActive) {
      await apiClient.delete(`${USERS.ROLE}?role=${key}`);

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
      await apiClient.post(USERS.ROLE, { role: key });

      setUserData((prev) => {
        if (!prev) return prev;

        if (roleAlreadyPresent(prev.roles ?? [], key)) return prev;

        const newRole: ProfileRole = {
          id: -Date.now(),
          role: key,
          role_display: ROLE_DISPLAY[key],
        };

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

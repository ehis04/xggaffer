import apiClient from "../../../services/api/client";
import { USERS } from "../../../services/api/endpoints";
import type { UserRole } from "../RoleProfileForm";

export const fetchUserRoles = async (
  setUserRoles: (roles: UserRole[]) => void,
  setCurrentRole: (role: string) => void,
  setFetchingRoles: (fetching: boolean) => void,
) => {
  try {
    const roles = await apiClient.get<UserRole[]>(USERS.ROLE);
    setUserRoles(roles);

    if (roles.length > 0) {
      setCurrentRole(roles[0].role);
    }
  } catch (error) {
    console.error("Error fetching user roles:", error);
  } finally {
    setFetchingRoles(false);
  }
};

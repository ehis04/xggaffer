import { Api_Endpoints, authenticatedFetch } from "../../../services/api/AuthenticateUserApi"
import type { UserRole } from "../RoleProfileForm";

export const fetchUserRoles = async (setUserRoles: (roles: UserRole[]) => void, setCurrentRole: (role: string) => void, setFetchingRoles: (fetching: boolean) => void) => {
    try {
        const response = await authenticatedFetch(Api_Endpoints.ASSIGN_ROLE,
            {method: "GET",}
        );

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || "Couldn't get user's roles");
        }

        const roles = await response.json();
        setUserRoles(roles);

        if (roles.length > 0) {
            setCurrentRole(roles[0].role);
        }
    } catch (error) {
        console.error("Error fetching user roles:", error);
    } finally {
        setFetchingRoles(false);
    }
}
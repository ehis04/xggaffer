import { Api_Endpoints, authenticatedFetch } from "../../../services/api/AuthenticateUserApi"
import type { UserData } from "../SideBar";

export const getUserProfile = async (setUserData: (userData: UserData) => void) => {
    try {
        const response = await authenticatedFetch(Api_Endpoints.USER_PROFILE);

        if (response.ok) {
            const data = await response.json();
            setUserData({
                username: data.user.username,
                display_name: data.display_name,
                bio: data.bio,
                followers_count: data.followers_count,
                following_count: data.following_count,
                gender: data.gender,
                // profile_image: data.profile_image,
            })
        }
    } catch (error) {
        console.error("Counldn't get user's profile", error);
    }
}
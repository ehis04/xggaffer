import { usersApi } from '../../../services/api/usersApi';
import type { UserData } from '../SideBar';

export const getUserProfile = async (setUserData: (userData: UserData) => void) => {
  try {
    const data = await usersApi.getMyProfile();
    
    setUserData({
      username: data.user.username,
    });
  } catch (error) {
    console.error("Couldn't get user's profile", error);
  }
};
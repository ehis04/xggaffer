import { useEffect, useState } from "react";
import type { UserData } from "../Navigation/SideBar";
import { useParams } from "react-router-dom";
import { getProfile } from "../Navigation/functions/getProfile";

export const ProfileDetails = () => {
  const { username } = useParams<{ username: string }>();
  const [userData, setUserData] = useState<UserData | null>(null);
  useEffect(() => {
    if (!username) return;
    getProfile(setUserData, username);
  }, [username]);

  return (
    <div className="profile-details-container">
        <span className="followers">{userData?.followers_count}</span>
        <span className="following">{userData?.following_count}</span>
        <span className="posts-total">28</span>
    </div>
  )
};

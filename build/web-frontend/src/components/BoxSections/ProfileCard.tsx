import "./css/ProfileCard.css";
import { useEffect, useState } from "react";
import type { UserData } from "../Navigation/SideBar";
import { getUserProfile } from "../Navigation/functions/getUserProfile";
import { ProfileButton } from "../Buttons/ProfileButton";

export const ProfileCard = () => {
    const [userData, setUserData] = useState<UserData | null>(null);

    useEffect(() => {
        getUserProfile(setUserData);
      }, [])

    const handleProfileClick = (username: string) => {
    globalThis.location.href = `/profile/${username}`;
    }


    return (
        <div className="profile-card-container">
            <div className="profile-pic-container">
                {userData && (
                    <ProfileButton
                        username={userData.username}
                        profileImage={userData.profile_image ?? undefined}
                        size="extra-large"
                        onClick={handleProfileClick}
                    />
                )}
            </div>
            <div className="profile-info">
                <p className="profile-name">
                    {userData?.display_name}
                </p>
                <div className="profile-title">
                    @{userData?.username}
                </div>
                <div className="profile-bio">
                    {userData?.bio}
                </div>
                <button className="go-to-profile">
                    Go to Profile
                </button>
                <div className="profile-stats">
                    <div className="stat-item">
                        <div className="stat-value">{userData?.followers_count}</div>
                        <div className="stat-label">Followers</div>
                    </div>
                    <div className="stat-item">
                        <div className="stat-value">{userData?.following_count}</div>
                        <div className="stat-label">Following</div>
                    </div>
                </div>
            </div>
        </div>
    )
}

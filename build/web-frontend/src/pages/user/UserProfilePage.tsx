import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Sidebar } from "../../components/Navigation/SideBar";
import { ProfileHeader } from "../../components/profile/ProfileHeader";
import { ProfileTabs } from "../../components/profile/ProfileTabs";
import { DetailsBox } from "../../components/profile/DetailsBox";
import { AccountDetails } from "../../components/profile/AccountDetails";
import { YourRoles } from "../../components/profile/YourRoles";
import { EditProfile } from "../../components/profile/EditProfile";
import { PostList } from "../../components/Social/PostList";
import type {
  ProfileData,
  FollowStatus,
} from "../../components/profile/types/ProfileTypes";
import { getUserProfile } from "../../components/Navigation/functions/getUserProfile";
import { getProfile } from "../../components/Navigation/functions/getProfile";
import { getFollowStatus } from "../../components/profile/functions/getFollowStatus";
import handleFollow from "../../components/profile/functions/handleFollow";
import "./css/UserProfilePage.css";
import { ProfileTopBar } from "../../components/profile/ProfileTopBar";
import {
  updateProfile,
  type UpdateProfilePayload,
} from "../../components/profile/functions/updateProfile";
import { toggleRole } from "../../components/profile/functions/toggleRole";

export function UserProfilePage() {
  const { username } = useParams<{ username: string }>();

  const [userData, setUserData] = useState<ProfileData | null>(null);
  const [loggedInUser, setLoggedInUser] = useState<ProfileData | null>(null);
  const [followStatus, setFollowStatus] = useState<FollowStatus | null>(null);
  const [editModalOpen, setEditModalOpen] = useState(false);

  const isOwnProfile = loggedInUser?.username === username;

  useEffect(() => {
    getUserProfile(setLoggedInUser);
  }, []);

  useEffect(() => {
    if (!username) return;
    getProfile(setUserData, username);
  }, [username]);

  useEffect(() => {
    if (!username || isOwnProfile || loggedInUser === null) return;
    getFollowStatus(setFollowStatus, username);
  }, [username, loggedInUser, isOwnProfile]);

  const onFollow = () => {
    if (!username) return;
    handleFollow(username, followStatus, setFollowStatus, setUserData);
  };

  const onSaveProfile = async (form: UpdateProfilePayload) => {
    try {
      await updateProfile(form, setUserData);
      setEditModalOpen(false);
    } catch {
      console.error("Couldn't save profile.");
    }
  };

  const onRoleToggle = async (roleKey: string, willBeActive: boolean) => {
    const isCurrentlyActive = !willBeActive;
    try {
      await toggleRole(roleKey, isCurrentlyActive, setUserData);
    } catch {
      console.log("")
    }
  };
  return (
    <div className="upp-layout">
      <div className="upp-sidebar">
        <Sidebar />
      </div>

      <main className="upp-main">
        <ProfileTopBar
          displayName={userData?.display_name || userData?.username}
          isOwnProfile={isOwnProfile}
        />
        <ProfileHeader
          userData={userData}
          loggedInUser={loggedInUser}
          followStatus={followStatus}
          isOwnProfile={isOwnProfile}
          onEditProfile={() => setEditModalOpen(true)}
          onFollow={onFollow}
        />

        <ProfileTabs />

        <div className="upp-feed">
          {username && (
            <PostList postListType="GET_USERS_POSTS" username={username} />
          )}
        </div>
      </main>

      <aside className="upp-right-panel">
        <DetailsBox userData={userData} />

        {isOwnProfile && (
          <>
            <YourRoles userData={userData} onRoleToggle={onRoleToggle}/>
            <AccountDetails onEditProfile={() => setEditModalOpen(true)} />
          </>
        )}
      </aside>

      {isOwnProfile && (
        <EditProfile
          isOpen={editModalOpen}
          userData={userData}
          onClose={() => setEditModalOpen(false)}
          onSave={onSaveProfile}
        />
      )}
    </div>
  );
}

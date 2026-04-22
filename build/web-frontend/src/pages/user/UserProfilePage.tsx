import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Sidebar } from "../../components/Navigation/SideBar";
import { ProfileHeader } from "../../components/profile/ProfileHeader";
import { ProfileTabs } from "../../components/profile/ProfileTabs";
import { DetailsBox } from "../../components/profile/DetailsBox";
import { AccountDetails } from "../../components/profile/AccountDetails";
import { YourRoles } from "../../components/profile/YourRoles";
import { EditProfile } from "../../components/profile/EditProfile";
import { PostList } from "../../components/Social/PostList";
import { ClubCard } from "../../components/Clubs/ClubCard";
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
import { clubsApi } from "../../services/api";
import type { Club } from "../../types/club";

export function UserProfilePage() {
  const { username } = useParams<{ username: string }>();
  const navigate = useNavigate();

  const [userData, setUserData] = useState<ProfileData | null>(null);
  const [loggedInUser, setLoggedInUser] = useState<ProfileData | null>(null);
  const [followStatus, setFollowStatus] = useState<FollowStatus | null>(null);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<"posts" | "clubs" | "acheivements" | "liked">("posts");
  const [clubs, setClubs] = useState<Club[]>([]);
  const [clubsLoaded, setClubsLoaded] = useState(false);
  const [clubsLoading, setClubsLoading] = useState(false);

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

  const onTabChange = (tab: typeof activeTab) => {
    setActiveTab(tab);
    if (tab === "clubs" && !clubsLoaded && isOwnProfile) {
      setClubsLoading(true);
      clubsApi.myClubs()
        .then((data) => { setClubs(data); setClubsLoaded(true); })
        .catch(() => setClubs([]))
        .finally(() => setClubsLoading(false));
    }
  };

  const renderTabContent = () => {
    if (activeTab === "posts") {
      return username ? <PostList postListType="GET_USERS_POSTS" username={username} /> : null;
    }

    if (activeTab === "clubs") {
      if (!isOwnProfile) {
        return <p style={{ padding: "1.5rem", color: "rgba(255,255,255,0.55)" }}>Clubs are not public on profiles yet.</p>;
      }
      if (clubsLoading) {
        return <p style={{ padding: "1.5rem", color: "rgba(255,255,255,0.55)" }}>Loading clubs...</p>;
      }
      if (clubs.length === 0 && clubsLoaded) {
        return (
          <div style={{ padding: "1.5rem" }}>
            <p style={{ color: "rgba(255,255,255,0.55)", marginBottom: "1rem" }}>You are not a member of any clubs yet.</p>
            <button
              style={{ background: "#2563eb", color: "white", border: "none", borderRadius: "8px", padding: "0.5rem 1.25rem", cursor: "pointer" }}
              onClick={() => navigate("/clubs")}
            >
              Go to Clubs
            </button>
          </div>
        );
      }
      return (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: "1rem", padding: "1rem" }}>
          {clubs.map((club) => (
            <ClubCard key={club.id} club={club} variant="mine" onClick={(c) => navigate(`/clubs/${c.id}/`)} />
          ))}
        </div>
      );
    }

    return <p style={{ padding: "1.5rem", color: "rgba(255,255,255,0.55)" }}>Nothing here yet.</p>;
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

        <ProfileTabs activeTab={activeTab} onTabChange={onTabChange} />

        <div className="upp-feed">
          {renderTabContent()}
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

import { CreatePost } from "../../components/Forms/CreatePost";
import { FeedTabs } from "../../components/Navigation/FeedTabs";
import { SearchBar } from "../../components/Navigation/SearchBar";
import { Sidebar } from "../../components/Navigation/SideBar";
import { SocialUserButtons } from "../../components/Social/SocialUserButtons";
import "./css/SocialPage.css";
import { PostList } from "../../components/Social/PostList";
import { ProfileCard } from "../../components/BoxSections/ProfileCard";
import { useState } from "react";

export const SocialPage = () => {
  const [activeTab, setActiveTab] = useState<"forYou" | "following">("forYou");
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const handleTabChange = (tab: "forYou" | "following") => {
    setActiveTab(tab);
  };
  const handlePost = (content: string) => {
    console.log("New Post:", content);
    setRefreshTrigger((prev) => prev + 1);
  };
  return (
    <div className="social-page">
      <div className="sidebar-section">
        <Sidebar />
      </div>
      <div className="searchBar-section">
        <SearchBar placeholder="Search" />
      </div>
      <div className="right-section">
        <div className="right-header">
          <SocialUserButtons />
        </div>
      </div>
      <div className="trendingBox-section">
        {/* <TrendingBox /> */}
        <ProfileCard />
      </div>
      <div className="main-section">
        <div className="social-tabs">
          <FeedTabs onTabChange={handleTabChange} />
        </div>
        <CreatePost onPost={handlePost} />
        <div className="feed-content">
          <PostList
            postListType={activeTab === "forYou" ? "EXPLORE_POSTS" : "FOLLOWING_POSTS"}
            refreshTrigger={refreshTrigger}
          />
        </div>
      </div>
    </div>
  );
};

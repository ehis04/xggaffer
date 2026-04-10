import { TrendingBox } from "../../components/BoxSections/TrendingBox";
import { CreatePost } from "../../components/Forms/CreatePost";
import { FeedTabs } from "../../components/Navigation/FeedTabs";
import { SearchBar } from "../../components/Navigation/SearchBar";
import { Sidebar } from "../../components/Navigation/SideBar";
import { SocialUserButtons } from "../../components/Social/SocialUserButtons";
import "./css/SocialPage.css";
import { PostList } from "../../components/Social/PostList";


export const SocialPage = () => {
  const handleTabChange = (tab: "forYou" | "following") => {
    console.log("Active tab:", tab);
  };
  const handlePost = (content: string) => {
    console.log("New Post:", content);
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
        <TrendingBox />
      </div>
      <div className="main-section">
        <div className="social-tabs">
          <FeedTabs onTabChange={handleTabChange} />
        </div>
        <CreatePost onPost={handlePost} />
        <div className="feed-content">
          <PostList />
        </div>
      </div>
    </div>
  );
};

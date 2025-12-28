import { TrendingBox } from "../../components/BoxSections/TrendingBox";
import { CreatePost } from "../../components/Forms/CreatePost";
import { FeedTabs } from "../../components/Navigation/FeedTabs";
import { SearchBar } from "../../components/Navigation/SearchBar";
import { Sidebar } from "../../components/Navigation/SideBar";
import { SocialUserButtons } from "../../components/Social/SocialUserButtons";
import "./css/SocialPage.css";
import { Post, type PostData } from "../../components/Social/Post";
import { PostList } from "../../components/Social/PostList";

const pdata = [{
    id: 123,
    author: {
        id: 1,
        username: "testuser",
        display_name: "Test User"
    },
    text_body: "This is a test post #first this is the first hashtag @admin hope this works",
    created_at: "2025-12-27T10:00:00Z",
    no_of_likes: 3,
    no_of_comments: 3,
    visibility: 'PB',
    moderation_status: 'OK',
    type: 'post',
    hashtags: ['first'],
    mentions: ['admin'],
    is_liked: false,
    is_reposted: false
},
{
    id: 124,
    author: {
        id: 1,
        username: "testuser",
        display_name: "Test User"
    },
    text_body: "This is a test post #first this is the first hashtag @admin hope this works",
    created_at: "2025-12-27T10:00:00Z",
    no_of_likes: 3,
    no_of_comments: 3,
    visibility: 'PB',
    moderation_status: 'OK',
    type: 'post',
    hashtags: ['first'],
    mentions: ['admin'],
    is_liked: false,
    is_reposted: false
},
{
    id: 125,
    author: {
        id: 1,
        username: "testuser",
        display_name: "Test User"
    },
    post_id: 123,
    text_body: "This is a test post #first this is the first hashtag @admin hope this works",
    created_at: "2025-12-27T10:00:00Z",
    no_of_likes: 3,
    no_of_comments: 3,
    visibility: 'PB',
    moderation_status: 'OK',
    type: 'comment',
    hashtags: ['first'],
    mentions: ['admin'],
    is_liked: false,
    is_reposted: false
},]

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
          <PostList postList={pdata} />
        </div>
      </div>
    </div>
  );
};

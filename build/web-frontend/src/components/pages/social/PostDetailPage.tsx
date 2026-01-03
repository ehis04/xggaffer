import { TrendingBox } from "../../components/BoxSections/TrendingBox";
import { SearchBar } from "../../components/Navigation/SearchBar";
import { Sidebar } from "../../components/Navigation/SideBar";
import { PostDetail } from "../../components/Social/PostDetail";
import { SocialUserButtons } from "../../components/Social/SocialUserButtons";
import "./css/SocialPage.css";

export const PostDetailPage = () => {
    return (
        <div className="post-detail-page">
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
                <div className="feed-content">
                    <PostDetail />
                </div>
            </div>
        </div>
    )
}
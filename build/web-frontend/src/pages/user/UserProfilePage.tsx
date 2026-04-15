import { Sidebar } from "../../components/Navigation/SideBar";
import { RoleDetails } from "../../components/profile/RoleDetails";

export function UserProfilePage () {
    return (
        <div className="user-profile-page-container">
            <div className="sidebar-section">
                <Sidebar />
            </div>
            <div className="main-section">
                <RoleDetails />
            </div>
            
        </div>
    )
}
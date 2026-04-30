import { AccountCreationForms } from "../../components/Forms/AccountCreationForms";
import { useAuth } from "../../context/useAuth";
import "./css/RoleAssignPage.css";

export const RoleAssignPage = () => {
  const { user } = useAuth();

  return (
    <div className="role-assign-page-container">
      <AccountCreationForms userEmail={user?.email ?? ""} />
    </div>
  );
};

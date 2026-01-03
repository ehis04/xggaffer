import { RoleAssignForm } from '../../components/Forms/RoleAssignForm';
import './css/RoleAssignPage.css';

export const RoleAssignPage = () => {
  return (
    <div className='role-assign-page-container'>
        <div className='role-assign-form-container'>
            <RoleAssignForm />
        </div>
    </div>
  )
}

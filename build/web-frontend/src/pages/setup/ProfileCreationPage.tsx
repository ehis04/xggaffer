import { ProfileCreation } from '../../components/Forms/ProfileCreation';
import './css/ProfileCreationPage.css';


export default function ProfileCreationPage() {
  return (
    <div className='profile-creation-page-container'>
        <div className='profile-form-container'>
            <ProfileCreation />
        </div>
    </div>
  )
}
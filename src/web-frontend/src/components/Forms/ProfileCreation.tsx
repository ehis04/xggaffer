import './css/ProfileCreation.css';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import apiClient from '../../services/api/client';
import { AppError } from '../../common/AppError';
import type { FormEvent } from 'react';

interface ProfileData {
  display_name: string;
  gender: string;
  date_of_birth: string;
  bio: string;
}

export const ProfileCreation = () => {
  const [formData, setFormData] = useState<ProfileData>({
    display_name: '',
    gender: 'NS',
    date_of_birth: '',
    bio: '',
  });
  const [error, setError] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const navigate = useNavigate();

  const handleInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) => {
    const { id, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [id]: value,
    }));
  };

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      const profile = {
        display_name: formData.display_name,
        gender: formData.gender,
        date_of_birth: formData.date_of_birth || null,
        bio: formData.bio || '',
      };
      try {
        await apiClient.patch('/users/profile/', profile);
      } catch (error) {
        if (!(error instanceof AppError) || error.status !== 404) throw error;
        await apiClient.post('/users/profile/create/', profile);
      }

      navigate('/create/profile/role');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred during profile creation');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="profile-creation-container">
      <h2>Create Your Profile</h2>

      {error && <div className="error-message">{error}</div>}

      <div className="profile-creation-form-group">
        <label htmlFor="display_name">Display Name</label>
        <input
          type="text"
          id="display_name"
          value={formData.display_name}
          onChange={handleInputChange}
          placeholder="Enter your desired display name"
        />
      </div>

      <div className="mid-section">
        <div className="profile-creation-form-group">
          <label htmlFor="gender">Gender</label>
          <select id="gender" value={formData.gender} onChange={handleInputChange}>
            <option value="F">Female</option>
            <option value="M">Male</option>
            <option value="O">Other</option>
            <option value="NS">Not Specified</option>
          </select>
        </div>

        <div className="profile-creation-form-group">
          <label htmlFor="date_of_birth">Date of Birth</label>
          <input
            type="date"
            id="date_of_birth"
            value={formData.date_of_birth}
            onChange={handleInputChange}
            className="profile-dob"
          />
        </div>
      </div>

      <div className="profile-creation-form-group">
        <label htmlFor="bio">Bio</label>
        <textarea
          className="bio-input"
          id="bio"
          value={formData.bio}
          placeholder="Tell us a little about yourself..."
          onChange={handleInputChange}
        />
      </div>

      <button type="submit" className="button-submit" disabled={isLoading}>
        {isLoading ? 'Creating Profile...' : 'Create Profile'}
      </button>
    </form>
  );
};

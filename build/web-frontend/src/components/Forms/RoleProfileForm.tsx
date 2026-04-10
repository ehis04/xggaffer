import { useEffect, useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import './css/RoleProfileForm.css';
import apiClient from '../../services/api/client';
import { useAuth } from '../../context/useAuth';

interface CoachProfileData {
  experience_level: string;
  formation_preferences: string;
  years_experience: number | string;
  club_name: string;
}

interface PlayerProfileData {
  primary_position: string;
  secondary_position: string;
  preferred_foot: string;
  height_cm: number | string;
  weight_kg: number | string;
}

export interface UserRole {
  id: number;
  role: string;
  role_display: string;
  created_at: string;
}

export const RoleProfileForm = () => {
  const [coachFormData, setCoachFormData] = useState<CoachProfileData>({
    experience_level: 'B',
    formation_preferences: '',
    years_experience: '',
    club_name: '',
  });
  const [playerFormData, setPlayerFormData] = useState<PlayerProfileData>({
    primary_position: '',
    secondary_position: '',
    preferred_foot: 'r',
    height_cm: '',
    weight_kg: '',
  });
  const [userRoles, setUserRoles] = useState<UserRole[]>([]);
  const [currentRole, setCurrentRole] = useState<string>('');
  const [fetchingRoles, setFetchingRoles] = useState<boolean>(true);
  const [error, setError] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const navigate = useNavigate();
  const { sendVerificationEmail } = useAuth();

  useEffect(() => {
    fetchUserRoles();
  }, []);

  const fetchUserRoles = async () => {
    try {
      const roles = await apiClient.get<UserRole[]>('/users/profile/role/');
      setUserRoles(roles);
      if (roles.length > 0) {
        setCurrentRole(roles[0].role);
      }
    } catch (err) {
      console.error('Failed to fetch user roles:', err);
    } finally {
      setFetchingRoles(false);
    }
  };

  const handleCoachInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) => {
    const { id, value } = e.target;
    setCoachFormData((prev) => ({
      ...prev,
      [id]: value,
    }));
  };

  const handlePlayerInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) => {
    const { id, value } = e.target;
    setPlayerFormData((prev) => ({
      ...prev,
      [id]: value,
    }));
  };

  const completeOnboarding = async () => {
    try {
      await sendVerificationEmail();
    } catch (err) {
      console.error('Failed to send verification email:', err);
    }
    navigate('/verify-email');
  };

  const handleCoachSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      await apiClient.post('/coaching/profile/create/', {
        experience_level: coachFormData.experience_level,
        formation_preferences: coachFormData.formation_preferences,
        years_experience: Number(coachFormData.years_experience),
        club_name: coachFormData.club_name,
      });

      await completeOnboarding();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred during coach profile creation');
    } finally {
      setIsLoading(false);
    }
  };

  const handlePlayerSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      await apiClient.post('/players/profile/create/', {
        primary_position: playerFormData.primary_position,
        secondary_position: playerFormData.secondary_position,
        preferred_foot: playerFormData.preferred_foot,
        height_cm: Number(playerFormData.height_cm),
        weight_kg: Number(playerFormData.weight_kg),
      });

      await completeOnboarding();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred during player profile creation');
    } finally {
      setIsLoading(false);
    }
  };

  if (fetchingRoles) {
    return <div className="loading">Loading roles...</div>;
  }

  if (userRoles.length === 0) {
    return (
      <div className="role-profile-error">
        <p>There are no roles assigned to this account</p>
      </div>
    );
  }

  return (
    <div className="role-profile-form-container">
      {error && <div className="error-message">{error}</div>}

      {userRoles.length > 1 && (
        <div className="profile-creation-form-group">
          <label htmlFor="role-select">Select Profile to Create:</label>
          <select
            id="role-select"
            value={currentRole}
            onChange={(e) => setCurrentRole(e.target.value)}
            className="role-select"
          >
            {userRoles.map((role) => (
              <option key={role.id} value={role.role}>
                {role.role_display}
              </option>
            ))}
          </select>
        </div>
      )}

      {currentRole === 'C' && (
        <form className="role-profile-form" onSubmit={handleCoachSubmit}>
          <h2>Create Coach Profile</h2>

          <div className="profile-creation-form-group">
            <label htmlFor="years_experience">Years of Experience</label>
            <input
              type="number"
              id="years_experience"
              value={coachFormData.years_experience}
              onChange={handleCoachInputChange}
              min="0"
              required
            />
          </div>

          <div className="mid-section">
            <div className="profile-creation-form-group">
              <label htmlFor="experience_level">Experience Level</label>
              <select
                id="experience_level"
                value={coachFormData.experience_level}
                onChange={handleCoachInputChange}
                required
              >
                <option value="B">Beginner</option>
                <option value="I">Intermediate</option>
                <option value="P">Professional</option>
              </select>
            </div>

            <div className="profile-creation-form-group">
              <label htmlFor="formation_preferences">Formation Preferences</label>
              <select
                id="formation_preferences"
                value={coachFormData.formation_preferences}
                onChange={handleCoachInputChange}
                required
              >
                <option value="">Select Formation</option>
                <option value="3-1-4-2">3-1-4-2</option>
                <option value="3-4-1-2">3-4-1-2</option>
                <option value="3-4-2-1">3-4-2-1</option>
                <option value="3-4-3">3-4-3</option>
                <option value="3-5-1-1">3-5-1-1</option>
                <option value="4-1-2-1-2">4-1-2-1-2</option>
                <option value="4-1-2-3">4-1-2-3</option>
                <option value="4-1-3-2">4-1-3-2</option>
                <option value="4-1-4-1">4-1-4-1</option>
                <option value="4-2-1-3">4-2-1-3</option>
                <option value="4-2-2-2">4-2-2-2</option>
                <option value="4-2-3-1">4-2-3-1</option>
                <option value="4-2-4">4-2-4</option>
                <option value="4-3-1-2">4-3-1-2</option>
                <option value="4-3-2-1">4-3-2-1</option>
                <option value="4-3-3">4-3-3</option>
                <option value="4-4-1-1">4-4-1-1</option>
                <option value="4-4-2">4-4-2</option>
                <option value="4-5-1">4-5-1</option>
                <option value="5-2-1-2">5-2-1-2</option>
                <option value="5-2-2-1">5-2-2-1</option>
                <option value="5-2-3">5-2-3</option>
                <option value="5-3-2">5-3-2</option>
                <option value="5-4-1">5-4-1</option>
              </select>
            </div>
          </div>

          <div className="profile-creation-form-group">
            <label htmlFor="club_name">Club Name</label>
            <input
              type="text"
              id="club_name"
              value={coachFormData.club_name}
              onChange={handleCoachInputChange}
              placeholder="Enter your club name"
            />
          </div>

          <button type="submit" disabled={isLoading} className="button-submit">
            {isLoading ? 'Creating...' : 'Create Coach Profile'}
          </button>
        </form>
      )}

      {currentRole === 'P' && (
        <form className="role-profile-form" onSubmit={handlePlayerSubmit}>
          <h2>Create Player Profile</h2>

          <div className="profile-creation-form-group">
            <label htmlFor="primary_position">Primary Position</label>
            <select
              id="primary_position"
              value={playerFormData.primary_position}
              onChange={handlePlayerInputChange}
              required
            >
              <option value="">Select Position</option>
              <option value="GK">Goalkeeper</option>
              <option value="RB">Right Back</option>
              <option value="RWB">Right Wing Back</option>
              <option value="CB">Centre Back</option>
              <option value="RCB">Right Centre Back</option>
              <option value="CCB">Central Centre Back</option>
              <option value="LCB">Left Centre Back</option>
              <option value="LB">Left Back</option>
              <option value="LWB">Left Wing Back</option>
              <option value="RDM">Right Defensive Midfielder</option>
              <option value="CDM">Central Defensive Midfielder</option>
              <option value="LDM">Left Defensive Midfielder</option>
              <option value="CM">Central Midfielder</option>
              <option value="RM">Right Midfielder</option>
              <option value="LM">Left Midfielder</option>
              <option value="RAM">Right Attacking Midfielder</option>
              <option value="CAM">Central Attacking Midfielder</option>
              <option value="LAM">Left Attacking Midfielder</option>
              <option value="RW">Right Winger</option>
              <option value="LW">Left Winger</option>
              <option value="CF">Centre Forward</option>
              <option value="ST">Striker</option>
            </select>
          </div>

          <div className="profile-creation-form-group">
            <label htmlFor="secondary_position">Secondary Position</label>
            <select
              id="secondary_position"
              value={playerFormData.secondary_position}
              onChange={handlePlayerInputChange}
              required
            >
              <option value="">Select Position</option>
              <option value="GK">Goalkeeper</option>
              <option value="RB">Right Back</option>
              <option value="RWB">Right Wing Back</option>
              <option value="CB">Centre Back</option>
              <option value="RCB">Right Centre Back</option>
              <option value="CCB">Central Centre Back</option>
              <option value="LCB">Left Centre Back</option>
              <option value="LB">Left Back</option>
              <option value="LWB">Left Wing Back</option>
              <option value="RDM">Right Defensive Midfielder</option>
              <option value="CDM">Central Defensive Midfielder</option>
              <option value="LDM">Left Defensive Midfielder</option>
              <option value="CM">Central Midfielder</option>
              <option value="RM">Right Midfielder</option>
              <option value="LM">Left Midfielder</option>
              <option value="RAM">Right Attacking Midfielder</option>
              <option value="CAM">Central Attacking Midfielder</option>
              <option value="LAM">Left Attacking Midfielder</option>
              <option value="RW">Right Winger</option>
              <option value="LW">Left Winger</option>
              <option value="CF">Centre Forward</option>
              <option value="ST">Striker</option>
            </select>
          </div>

          <div className="mid-section">
            <div className="profile-creation-form-group">
              <label htmlFor="height_cm">Height (cm)</label>
              <input
                type="number"
                id="height_cm"
                value={playerFormData.height_cm}
                onChange={handlePlayerInputChange}
                min="0"
                max="300"
                required
              />
            </div>

            <div className="profile-creation-form-group">
              <label htmlFor="weight_kg">Weight (kg)</label>
              <input
                type="number"
                id="weight_kg"
                value={playerFormData.weight_kg}
                onChange={handlePlayerInputChange}
                min="0"
                max="200"
                required
              />
            </div>
          </div>

          <div className="profile-creation-form-group">
            <label htmlFor="preferred_foot">Dominant Foot</label>
            <select
              id="preferred_foot"
              value={playerFormData.preferred_foot}
              onChange={handlePlayerInputChange}
              required
            >
              <option value="r">Right</option>
              <option value="l">Left</option>
              <option value="b">Both</option>
            </select>
          </div>

          <button type="submit" className="button-submit" disabled={isLoading}>
            {isLoading ? 'Creating...' : 'Create Player Profile'}
          </button>
        </form>
      )}

      {currentRole === 'R' && (
        <div className="role-profile-form">
          <h2>Referee Profile</h2>
          <p>Referee profile creation coming soon.</p>
          <button
            type="button"
            className="button-submit"
            onClick={() => completeOnboarding()}
          >
            Continue
          </button>
        </div>
      )}

      {currentRole === 'F' && (
        <div className="role-profile-form">
          <h2>Fan Profile</h2>
          <p>No additional profile needed for fans.</p>
          <button
            type="button"
            className="button-submit"
            onClick={() => completeOnboarding()}
          >
            Continue
          </button>
        </div>
      )}
    </div>
  );
};
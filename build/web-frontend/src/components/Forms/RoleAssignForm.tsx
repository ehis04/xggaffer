import './css/RoleAssignForm.css';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import apiClient from '../../services/api/client';
import type { FormEvent } from 'react';

interface RoleData {
  role: string;
}

export const RoleAssignForm = () => {
  const [formData, setFormData] = useState<RoleData>({
    role: 'P',
  });
  const [error, setError] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const navigate = useNavigate();

  const handleInputChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
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
      await apiClient.post('/users/profile/role/', {
        role: formData.role,
      });

      navigate('/create/profile/role/details');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred while assigning your role');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form className="role-assign-form-container" onSubmit={handleSubmit}>
      <h2>Choose a Role</h2>

      {error && <div className="error-message">{error}</div>}

      <div className="role-assign-form-group">
        <label htmlFor="role">Role</label>
        <select id="role" value={formData.role} onChange={handleInputChange}>
          <option value="C">Coach</option>
          <option value="P">Player</option>
          <option value="R">Referee</option>
          <option value="F">Fan</option>
        </select>
      </div>

      <button type="submit" className="button-submit" disabled={isLoading}>
        {isLoading ? 'Assigning Role...' : 'Continue'}
      </button>
    </form>
  );
};
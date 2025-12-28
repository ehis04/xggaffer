// src/components/pages/coaching/teamsheets/TeamsheetDetail.tsx
import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { teamsheetApi } from '../../../services/api/teamsheetApi';
import type { Teamsheet } from '../../../types/teamsheet';

export const TeamsheetDetail = () => {
  const { id } = useParams<{ id: string }>();
  const [teamsheet, setTeamsheet] = useState<Teamsheet | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    // Only attempt to load when id is a numeric string to avoid NaN fetches
    if (id && /^\d+$/.test(id)) {
      loadTeamsheet(Number.parseInt(id));
    }
  }, [id]);

  const loadTeamsheet = async (teamsheetId: number) => {
    try {
      setLoading(true);
      const data = await teamsheetApi.getTeamsheet(teamsheetId);
      setTeamsheet(data);
      setError(null);
    } catch (err) {
      setError('Failed to load teamsheet');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleBack = () => {
    navigate('/coaching/teamsheets');
  };

  if (loading) return <div>Loading teamsheet...</div>;
  if (error) return <div>Error: {error}</div>;
  if (!teamsheet) return <div>Teamsheet not found</div>;

  return (
    <div>
      <button onClick={handleBack}>← Back to List</button>
      
      <h1>{teamsheet.title}</h1>
      <p><strong>Formation:</strong> {teamsheet.formation}</p>
      <p><strong>Created:</strong> {new Date(teamsheet.created_at!).toLocaleDateString()}</p>
      <p><strong>Last Updated:</strong> {new Date(teamsheet.updated_at!).toLocaleDateString()}</p>

      <h2>Players</h2>
      {teamsheet.players && teamsheet.players.length > 0 ? (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th style={{ border: '1px solid #ccc', padding: '8px' }}>Number</th>
              <th style={{ border: '1px solid #ccc', padding: '8px' }}>Name</th>
              <th style={{ border: '1px solid #ccc', padding: '8px' }}>Position</th>
            </tr>
          </thead>
          <tbody>
            {teamsheet.players.map((player) => (
              <tr key={player.id}>
                <td style={{ border: '1px solid #ccc', padding: '8px' }}>{player.number}</td>
                <td style={{ border: '1px solid #ccc', padding: '8px' }}>{player.name}</td>
                <td style={{ border: '1px solid #ccc', padding: '8px' }}>{player.position}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p>No players added yet</p>
      )}
    </div>
  );
};

export default TeamsheetDetail;
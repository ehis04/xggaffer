// src/components/pages/coaching/teamsheets/TeamsheetDetail.tsx
import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { teamsheetApi } from '../../../../services/api';
import type { Teamsheet } from '../../../../types/teamsheet';

export const TeamsheetDetail = () => {
  const { clubId, id } = useParams<{ clubId: string; id: string }>();
  const [teamsheet, setTeamsheet] = useState<Teamsheet | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    // Only attempt to load when both clubId and id are numeric strings
    if (clubId && id && /^\d+$/.test(clubId) && /^\d+$/.test(id)) {
      loadTeamsheet(Number.parseInt(clubId), Number.parseInt(id));
    }
  }, [clubId, id]);

  const loadTeamsheet = async (clubId: number, teamsheetId: number) => {
    try {
      setLoading(true);
      const data = await teamsheetApi.get(clubId, teamsheetId);
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
    navigate(`/clubs/${clubId}/teamsheets`);
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
                <td style={{ border: '1px solid #ccc', padding: '8px' }}>{player.display_number}</td>
                <td style={{ border: '1px solid #ccc', padding: '8px' }}>{player.display_name}</td>
                <td style={{ border: '1px solid #ccc', padding: '8px' }}>{player.position_label}</td>
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
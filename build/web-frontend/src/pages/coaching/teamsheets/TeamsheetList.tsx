import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { teamsheetApi } from '../../../../services/api';
import type { TeamsheetListItem } from '../../../../types/teamsheet';

export const TeamsheetList = () => {
  const [teamsheets, setTeamsheets] = useState<TeamsheetListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  const { clubId } = useParams<{ clubId: string }>();

  useEffect(() => {
    if (clubId) {
      loadTeamsheets();
    }
  }, [clubId]);

  const loadTeamsheets = async () => {
    try {
      setLoading(true);
      const data = await teamsheetApi.list(Number(clubId));
      setTeamsheets(data);
      setError(null);
    } catch (err) {
      setError('Failed to load teamsheets');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleViewTeamsheet = (id: number) => {
    navigate(`/coaching/teamsheets/${id}`);
  };

  const handleCreateNew = () => {
    navigate('/coaching/teamsheets/create');
  };

  if (loading) return <div>Loading teamsheets...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div>
      <h1>Team Sheets</h1>
      <button onClick={handleCreateNew}>Create New Teamsheet</button>
      
      {teamsheets.length === 0 ? (
        <p>No teamsheets yet. Create your first one!</p>
      ) : (
        <div>
          {teamsheets.map((teamsheet) => (
            <div key={teamsheet.id} style={{ border: '1px solid #ccc', padding: '10px', margin: '10px 0' }}>
              <h3>{teamsheet.title}</h3>
              <p>Formation: {teamsheet.formation}</p>
              <p>Updated: {new Date(teamsheet.updated_at).toLocaleDateString()}</p>
              <button onClick={() => handleViewTeamsheet(teamsheet.id)}>View Details</button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default TeamsheetList;
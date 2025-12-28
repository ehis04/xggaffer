import { useNavigate } from 'react-router-dom';

export const TeamsheetCreate = () => {
  const navigate = useNavigate();

  const handleBack = () => navigate('/coaching/teamsheets');

  return (
    <div>
      <button onClick={handleBack}>← Back to List</button>
      <h1>Create Teamsheet</h1>
      <p>This is a placeholder create page. Implement form to create a teamsheet here.</p>
    </div>
  );
};

export default TeamsheetCreate;
// frontend/src/components/laws/LawsList.tsx
import React, { useEffect, useState } from 'react';
import { lawsApi } from '../../../../services/api';
import type { LawListItem, LawEdition } from '../../../../types/laws';

export const LawsList: React.FC = () => {
  const [laws, setLaws] = useState<LawListItem[]>([]);
  const [editions, setEditions] = useState<LawEdition[]>([]);
  const [selectedEdition, setSelectedEdition] = useState<number | undefined>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadEditions();
  }, []);

  useEffect(() => {
    loadLaws();
  }, [selectedEdition]);

  const loadEditions = async () => {
    try {
      const data = await lawsApi.getEditions();
      setEditions(data);
      
      // Set current edition as default
      const current = data.find(e => e.is_current);
      if (current) setSelectedEdition(current.id);
    } catch (err) {
      setError('Failed to load editions');
      console.error(err);
    }
  };

  const loadLaws = async () => {
    try {
      setLoading(true);
      const data = await lawsApi.getLaws(selectedEdition);
      setLaws(data);
    } catch (err) {
      setError('Failed to load laws');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="loading">Loading laws...</div>;
  if (error) return <div className="error">{error}</div>;

  return (
    <div className="laws-list">
      <div className="laws-header">
        <h1>Laws of the Game</h1>
        <select 
          value={selectedEdition} 
          onChange={(e) => setSelectedEdition(Number(e.target.value))}
          className="edition-selector"
        >
          {editions.map(edition => (
            <option key={edition.id} value={edition.id}>
              {edition.year} {edition.is_current && '(Current)'}
            </option>
          ))}
        </select>
      </div>

      <div className="laws-grid">
        {laws.map(law => (
          <div key={law.id} className="law-card">
            <h3>Law {law.number}</h3>
            <h4>{law.title}</h4>
            <p className="clause-count">{law.clause_count} clauses</p>
            <button onClick={() => globalThis.location.href = `/laws/${law.number}`}>
              View Details
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};

export default LawsList;
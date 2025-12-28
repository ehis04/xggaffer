
// frontend/src/components/laws/LawDetail.tsx
import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { lawsApi } from '../../../../services/api/lawsApi';
import type { Law, LawChange } from '../../../../types/laws';

export const LawDetail: React.FC = () => {
  const { lawNumber } = useParams<{ lawNumber: string }>();
  const [law, setLaw] = useState<Law | null>(null);
  const [changes, setChanges] = useState<LawChange[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadLawData();
  }, [lawNumber]);

  const loadLawData = async () => {
    if (!lawNumber) return;
    
    try {
      setLoading(true);
      const [lawData, changesData] = await Promise.all([
        lawsApi.getLawByNumber(Number(lawNumber)),
        lawsApi.getChanges(undefined, Number(lawNumber))
      ]);
      
      setLaw(lawData);
      setChanges(changesData);
    } catch (err) {
      console.error('Failed to load law', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div>Loading...</div>;
  if (!law) return <div>Law not found</div>;

  return (
    <div className="law-detail">
      <header>
        <h1>Law {law.number}: {law.title}</h1>
      </header>

      {changes.length > 0 && (
        <div className="changes-alert">
          <h3>Recent Changes</h3>
          {changes.map(change => (
            <div key={change.id} className={`change change-${change.change_type}`}>
              <strong>{change.clause_id}</strong>: {change.description}
            </div>
          ))}
        </div>
      )}

      <div className="clauses">
        {law.clauses.map(clause => (
          <div key={clause.id} className="clause">
            <h3>{clause.clause_id} {clause.heading}</h3>
            <p>{clause.content}</p>
            
            {clause.examples.length > 0 && (
              <div className="examples">
                <h4>Examples:</h4>
                <ul>
                  {clause.examples.map((example, idx) => (
                    <li key={idx}>{example}</li>
                  ))}
                </ul>
              </div>
            )}
            
            {clause.notes.length > 0 && (
              <div className="notes">
                <h4>Notes:</h4>
                <ul>
                  {clause.notes.map((note, idx) => (
                    <li key={idx}>{note}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default LawDetail;
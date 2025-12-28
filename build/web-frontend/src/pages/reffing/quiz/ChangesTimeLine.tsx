
// frontend/src/components/laws/ChangesTimeline.tsx
import React, { useEffect, useState } from 'react';
import { lawsApi } from '../../../services/api/lawsApi';
import type { LawChange, LawEdition } from '../../../types/laws';

export const ChangesTimeline: React.FC = () => {
  const [changes, setChanges] = useState<LawChange[]>([]);
  const [editions, setEditions] = useState<LawEdition[]>([]);
  const [selectedEdition, setSelectedEdition] = useState<number | undefined>();

  useEffect(() => {
    loadData();
  }, [selectedEdition]);

  const loadData = async () => {
    const [changesData, editionsData] = await Promise.all([
      lawsApi.getChanges(selectedEdition),
      lawsApi.getEditions()
    ]);
    
    setChanges(changesData);
    setEditions(editionsData);
  };

  const groupByLaw = (changes: LawChange[]) => {
    return changes.reduce((acc, change) => {
      if (!acc[change.law_number]) {
        acc[change.law_number] = [];
      }
      acc[change.law_number].push(change);
      return acc;
    }, {} as Record<number, LawChange[]>);
  };

  const grouped = groupByLaw(changes);

  return (
    <div className="changes-timeline">
      <h1>Law Changes</h1>
      
      <select onChange={(e) => setSelectedEdition(Number(e.target.value))}>
        <option value="">All editions</option>
        {editions.map(ed => (
          <option key={ed.id} value={ed.id}>{ed.year}</option>
        ))}
      </select>

      {Object.entries(grouped).map(([lawNum, lawChanges]) => (
        <div key={lawNum} className="law-changes-group">
          <h2>Law {lawNum}</h2>
          {lawChanges.map(change => (
            <div key={change.id} className={`change-item ${change.change_type}`}>
              <span className="change-badge">{change.change_type}</span>
              <span className="clause-id">{change.clause_id}</span>
              <p>{change.description}</p>
              
              {change.old_content && (
                <details>
                  <summary>View details</summary>
                  <div className="change-diff">
                    <div className="old-content">
                      <strong>Old:</strong>
                      <p>{change.old_content}</p>
                    </div>
                    <div className="new-content">
                      <strong>New:</strong>
                      <p>{change.new_content}</p>
                    </div>
                  </div>
                </details>
              )}
            </div>
          ))}
        </div>
      ))}
    </div>
  );
};

export default ChangesTimeline;
import { useEffect } from "react";
import type { CourseContentProps } from "./types/CourseTypes";
import { ClauseContent } from "./ClauseContent";
import { ScenarioContent } from "./ScenarioContent";
import { DrillContent } from "./DrillContent";

export const CourseContent = ({
  item,
  completedIds,
  scenarioSelections,
  scenarioRevealed,
  onScenarioSelect,
  onScenarioCheck,
  drillAnswers,
  drillSubmitted,
  onDrillAnswer,
  onDrillSubmit,
  onDrillReset,
  onScenarioReset,
}: CourseContentProps) => {
  useEffect(() => {}, [item.id]);

  switch (item.type) {
    case "clause":
      return <ClauseContent item={item} isRead={completedIds.has(item.id)} />;

    case "scenario":
      return (
        <ScenarioContent
          item={item}
          selectedOption={scenarioSelections[item.id]}
          revealed={scenarioRevealed.has(item.id)}
          onSelect={(optId) => onScenarioSelect(item.id, optId)}
          onCheck={() => onScenarioCheck(item.id)}
          onReset={() => onScenarioReset(item.id)} 
        />
      );

    case "drill":
      return (
        <DrillContent
          item={item}
          answers={drillAnswers[item.id] ?? {}}
          submitted={drillSubmitted.has(item.id)}
          onAnswer={(index, value) => onDrillAnswer(item.id, index, value)}
          onSubmit={() => onDrillSubmit(item.id)}
          onReset={() => onDrillReset(item.id)}
        />
      );
    
    // case 'quiz':

    default:
        return null;
  }
};

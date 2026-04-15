import { getGrade, overallGrade } from "./functions/getGrade";
import './css/PlayerAnalyticsWidget.css';
import type {
  PlayerAttributes,
  PlayerAnalyticsWidgetProps,
} from "./types/DashboardTypes";
import {
  PlayerAttributeDetails,
} from "./PlayerAttributeDetails";
import { attributeLabels } from "./functions/attributeLabels";

const attributeKeys = Object.keys(attributeLabels) as Array<
  keyof PlayerAttributes
>;

export const PlayerAnalyticsWidget = ({
  player,
}: PlayerAnalyticsWidgetProps) => {
  if (!player) {
    return (
      <div className="analytics-widget-empty">
        <span className="analytics-widget-empty-text">
          Select a Player.
        </span>
      </div>
    );
  }

  const overall = overallGrade(player.attributes);

  return (
    <div className="analytics-widget">
      <div className="analytics-widget-header">
        <div className="analytics-widget-player-info">
          <span className="analytics-widget-name">{player.display_name}</span>
          <span className="analytics-widget-position">{player.position}</span>
        </div>
        <div
          className="analytics-widget-overall"
          style={{ color: overall.colour, background: overall.bg }}
          title="Overall grade"
        >
          <span className="analytics-widget-overall-grade">
            {overall.grade}
          </span>
          <span className="analytics-widget-overall-lbl">Overall</span>
        </div>
      </div>

      <div className="analytics-widget-divider" />

      <div className="analytics-widget-attributes">
        {attributeKeys.map((key) => {
          const value = player.attributes[key];
          const { grade, colour, bg } = getGrade(value);

          return (
            <PlayerAttributeDetails
              attrKey={key}
              value={value}
              colour={colour}
              bg={bg}
              grade={grade}
            />
          );
        })}
      </div>
    </div>
  );
};

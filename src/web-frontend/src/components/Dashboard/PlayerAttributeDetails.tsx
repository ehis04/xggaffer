import type { PlayerAttributeDetailsProps } from "./types/DashboardTypes"
import { attributeLabels } from "./functions/attributeLabels"
import './css/PlayerAnalyticsWidget.css'

export const PlayerAttributeDetails = ({ attrKey, value, colour, bg, grade }: PlayerAttributeDetailsProps) => {
  return (
    <div className="attribute-row">
      <span className="attribute-row-lbl">{attributeLabels[attrKey]}</span>

      <div className="attribute-row-bar-track">
        <div className="attribute-row-bar-fill" style={{ width: `${value}%`, background: colour }} />
      </div>

      <span className="attribute-row-value">{value}</span>

      <span className="attribute-row-grade" style={{ color: colour, background: bg }}>
        {grade}
      </span>
    </div>
  )
}
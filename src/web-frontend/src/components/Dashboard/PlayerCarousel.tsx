import './css/PlayerCarousel.css';

import type { PlayerCarouselProps } from "./types/DashboardTypes"
import { statusConfig } from "./functions/statusConfig"
import { PlayerCard } from "./PlayerCard"

export const PlayerCarousel = ({ players, selectedId, onPlayerSelect }: PlayerCarouselProps) => {
    return (
        <div className="pc-container">
            {players.map(player => {
                const status = statusConfig[player.status]
                const isSelected = player.id === selectedId
                const isUnavailable = player.status !== 'AV'

                return (
                    <PlayerCard
                        key={player.id}
                        player={player}
                        status={status}
                        isSelected={isSelected}
                        isUnavailable={isUnavailable}
                        onPlayerSelect={onPlayerSelect}
                    />
                )
            })}
        </div>
    )
}
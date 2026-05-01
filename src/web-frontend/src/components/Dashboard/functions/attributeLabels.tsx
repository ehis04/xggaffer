import type { PlayerAttributes } from "../types/DashboardTypes";

export const attributeLabels: Record<keyof PlayerAttributes, string> = {
  pace:        'Pace',
  passing:     'Passing',
  stamina:     'Stamina',
  shooting:    'Shooting',
  defending:   'Defending',
  dribbling:   'Dribbling',
  physicality: 'Physicality',
  fitness:     'Fitness',
}
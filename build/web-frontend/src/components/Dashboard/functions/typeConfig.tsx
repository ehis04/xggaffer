import type { SessionType } from "../types/DashboardTypes";

export const typeConfig: Record<SessionType, { label: string; colour: string; bg: string }> = {
  training:  { label: 'Training',  colour: '#3dd68c', bg: 'rgba(61,214,140,0.12)'  },
  match:     { label: 'Match',     colour: '#5599e0', bg: 'rgba(85,153,224,0.12)'  },
  rest:      { label: 'Rest',      colour: '#888780', bg: 'rgba(136,135,128,0.12)' },
  friendly:  { label: 'Friendly',  colour: '#e0a155', bg: 'rgba(224,161,85,0.12)'  },
}
import type { ActivityConfig, ActivityEventType } from "../types/DashboardTypes"

export const activityConfig: Record<ActivityEventType, ActivityConfig> = {
  session_logged:    { colour: '#3dd68c', bg: 'rgba(61,214,140,0.12)'  },
  player_injured:    { colour: '#e05555', bg: 'rgba(224,85,85,0.12)'   },
  player_recovered:  { colour: '#3dd68c', bg: 'rgba(61,214,140,0.12)'  },
  formation_updated: { colour: '#5599e0', bg: 'rgba(85,153,224,0.12)'  },
  player_added:      { colour: '#e0a155', bg: 'rgba(224,161,85,0.12)'  },
  match_result:      { colour: '#8a55e0', bg: 'rgba(138,85,224,0.12)'  },
}
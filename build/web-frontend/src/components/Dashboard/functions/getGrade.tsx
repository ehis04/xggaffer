import type { GradeResult, Grade, PlayerAttributes } from "../types/DashboardTypes";

const gradeThresholds: Array<{ min: number; grade: Grade; colour: string; bg: string }> = [
  { min: 97, grade: 'A+', colour: '#1adb6e', bg: 'rgba(26,219,110,0.12)'  },
  { min: 93, grade: 'A',  colour: '#3dd68c', bg: 'rgba(61,214,140,0.12)'  },
  { min: 90, grade: 'A-', colour: '#5dd4a0', bg: 'rgba(93,212,160,0.12)'  },
  { min: 87, grade: 'B+', colour: '#8ecf3d', bg: 'rgba(142,207,61,0.12)'  },
  { min: 83, grade: 'B',  colour: '#b8d43d', bg: 'rgba(184,212,61,0.12)'  },
  { min: 80, grade: 'B-', colour: '#d4c83d', bg: 'rgba(212,200,61,0.12)'  },
  { min: 77, grade: 'C+', colour: '#d4a83d', bg: 'rgba(212,168,61,0.12)'  },
  { min: 73, grade: 'C',  colour: '#d4883d', bg: 'rgba(212,136,61,0.12)'  },
  { min: 70, grade: 'C-', colour: '#d4683d', bg: 'rgba(212,104,61,0.12)'  },
  { min: 60, grade: 'D',  colour: '#d44e3d', bg: 'rgba(212,78,61,0.12)'   },
  { min: 0,  grade: 'F',  colour: '#a01a1a', bg: 'rgba(160,26,26,0.12)'   },
]

export function getGrade(value: number): GradeResult {
  const clamped = Math.max(0, Math.min(100, value))
  const match = gradeThresholds.find(t => clamped >= t.min)
  return match ?? gradeThresholds[gradeThresholds.length - 1]
}

export function overallGrade(attrs: PlayerAttributes): ReturnType<typeof getGrade> {
  const values = Object.values(attrs)
  const avg = Math.round(values.reduce((a, b) => a + b, 0) / values.length)
  return getGrade(avg)
}
export interface TeamsheetPlayer {
  id?: number;
  name: string;
  number: number;
  position: string;
  teamsheet?: number;
}


export interface Teamsheet {
  id?: number;
  title: string;
  formation: string;
  players?: TeamsheetPlayer[];
  created_at?: string;
  updated_at?: string;
}
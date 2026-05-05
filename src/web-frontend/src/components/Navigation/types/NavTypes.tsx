export interface ClubsNavItem {
  id: string;
  label: string;
  badge?: number;
  onClick?: () => void;
  cls: string;
}
import type { Club } from "../types/club";

export const FEATURED_FAN_CLUB_NAMES = [
  "manchester united",
  "manchester united fc",
  "real madrid",
  "real madrid cf",
  "bayern munich",
  "fc bayern munchen",
  "fc bayern munich",
  "paris saint germain",
  "paris saint germain fc",
  "psg",
  "juventus",
  "juventus fc",
] as const;

const ORDERED_FEATURED_CLUBS = [
  ["manchester united", "manchester united fc"],
  ["real madrid", "real madrid cf"],
  ["bayern munich", "fc bayern munchen", "fc bayern munich"],
  ["psg", "paris saint germain", "paris saint germain fc"],
  ["juventus", "juventus fc"],
] as const;

export const normalizeFeaturedClubName = (name: string): string =>
  name
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9 ]/g, " ")
    .replace(/\s+/g, " ")
    .trim();

const FEATURED_CLUB_ORDER = new Map<string, number>(
  ORDERED_FEATURED_CLUBS.flatMap((names, idx) =>
    names.map((name) => [normalizeFeaturedClubName(name), idx] as const)
  )
);

export const getFeaturedClubOrder = (club: Club): number | undefined =>
  FEATURED_CLUB_ORDER.get(normalizeFeaturedClubName(club.name));

export const isFeaturedFanClub = (club: Club): boolean =>
  getFeaturedClubOrder(club) !== undefined;

export const sortFeaturedFanClubs = (clubs: Club[]): Club[] =>
  [...clubs].sort(
    (a, b) =>
      (getFeaturedClubOrder(a) ?? Number.MAX_SAFE_INTEGER) -
      (getFeaturedClubOrder(b) ?? Number.MAX_SAFE_INTEGER)
  );

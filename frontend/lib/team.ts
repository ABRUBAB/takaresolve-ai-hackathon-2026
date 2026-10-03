/**
 * The team shown on /about. Edit this file to change names, roles or links (no other code needs to change).
 */
export type Member = { name: string; role: string; work: string; github?: string; initial?: string };

export const TEAM_NAME = "UVERA team";

export const TEAM: Member[] = [
  { name: "Tanvir Hossin", role: "Team lead & design", work: "Leads the team, the product story and the visual design." },
  {
    name: "Abdullah Rubab",
    role: "Lead AI/ML & development",
    work: "Machine learning, the website and the API: synthetic world, Pause Check, briefs and evaluation.",
    github: "ABRUBAB",
  },
  { name: "Abdur Rahman", role: "Backend & AI/ML", work: "Backend services and model notebooks." },
];

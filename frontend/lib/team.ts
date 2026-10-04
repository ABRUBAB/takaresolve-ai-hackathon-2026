/**
 * The team shown on /about. Edit this file to change names, roles or links (no other code needs to change).
 */
export type Member = { name: string; role: string; work: string; github?: string; initial?: string; photo?: string };

export const TEAM_NAME = "UVERA team";

// photo: a 4:5 portrait in public/team (640×800 WebP)
export const TEAM: Member[] = [
  {
    name: "Tanvir Hossin",
    role: "Team lead & design",
    work: "Leads the team, the product story and the visual design.",
    photo: "/team/tanvir.webp",
  },
  {
    name: "Abdullah Rubab",
    role: "Lead AI/ML & development",
    work: "Machine learning, the website and the API: synthetic world, Pause Check, briefs and evaluation.",
    github: "ABRUBAB",
    photo: "/team/rubab.webp",
  },
  { name: "Abdur Rahman", role: "Backend & AI/ML", work: "Backend services and model notebooks.", photo: "/team/abdur-rahman.webp" },
];

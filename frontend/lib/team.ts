/**
 * The team shown on /about. Edit this file to change names, roles or links (no other code needs to change).
 * Leave `name` empty to show a neutral "Team member" card.
 */
export type Member = { name: string; role: string; work: string; github?: string; initial?: string };

export const TEAM_NAME = "UVERA team";

export const TEAM: Member[] = [
  { name: "Rubab", role: "Product & engineering", work: "Website, API, synthetic world (NB00), Pause Check (NB01), briefs (NB07), evaluation (NB99)", github: "ABRUBAB" },
  { name: "", role: "Machine learning", work: "Scam text, forecasting, QR Shield and case linking notebooks (NB02–NB06)" },
  { name: "", role: "Research & presentation", work: "Problem research, report and pitch" },
];

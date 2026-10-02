export const tk = (v: number | null | undefined, digits = 0) =>
  v == null || Number.isNaN(v) ? "—" : `Tk ${v.toLocaleString("en-US", { maximumFractionDigits: digits, minimumFractionDigits: 0 })}`;

/** Probabilities are estimates: never shown as exactly 0% or 100%. */
export const pct = (p: number | null | undefined, digits = 0) => {
  if (p == null || Number.isNaN(p)) return "—";
  if (p < 0.01) return "<1%";
  if (p > 0.99) return ">99%";
  return `${(p * 100).toFixed(digits)}%`;
};

export const num = (v: number | null | undefined, digits = 0) =>
  v == null || Number.isNaN(v) ? "—" : v.toLocaleString("en-US", { maximumFractionDigits: digits });

export const metric = (v: unknown, digits = 3) => (typeof v === "number" ? v.toFixed(digits) : "not measured yet");

export const shortDate = (s: string) => {
  const d = new Date(s);
  return Number.isNaN(d.getTime()) ? s : d.toLocaleDateString("en-GB", { day: "numeric", month: "short" });
};

export const hoursText = (h: number) => {
  if (h < 0) return `${Math.abs(Math.round(h))} h overdue`;
  if (h < 48) return `${Math.round(h)} h left`;
  return `${Math.round(h / 24)} days left`;
};

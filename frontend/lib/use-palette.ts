"use client";

import { useTheme } from "next-themes";
import { useMemo } from "react";

const DARK = { fg: "#fafafa", muted: "#a3a3a3", faint: "#737373", border: "#262626", bar: "#525252", volt: "#d7ff3a", risk: "#ff4d4f", caution: "#f5a524", safe: "#34d399", popover: "#111111" };
const LIGHT = { fg: "#0a0a0a", muted: "#52525b", faint: "#71717a", border: "#e4e4e7", bar: "#a1a1aa", volt: "#4d7c0f", risk: "#b91c1c", caution: "#b45309", safe: "#047857", popover: "#ffffff" };

/** Chart colours as plain hex values: SVG attributes (used by Recharts) cannot read CSS variables. Mirrors globals.css. */
export function usePalette() {
  const { resolvedTheme } = useTheme();
  return useMemo(() => (resolvedTheme === "light" ? LIGHT : DARK), [resolvedTheme]);
}

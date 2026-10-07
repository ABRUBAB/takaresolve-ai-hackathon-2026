import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "What we changed after Phase 1",
  description: "For each judging criterion: the Phase 1 concern, what UVERA built in response, and the measured evidence.",
};

export default function Layout({ children }: { children: ReactNode }) {
  return children;
}

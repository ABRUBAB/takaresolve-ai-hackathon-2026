import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "Trust Center",
  description: "Every UVERA metric with its source notebook, fairness slices, the data card, live health and limitations.",
};

export default function Layout({ children }: { children: ReactNode }) {
  return children;
}

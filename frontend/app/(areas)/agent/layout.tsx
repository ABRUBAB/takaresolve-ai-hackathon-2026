import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "Agent · Karim",
  description: "Cash to hold for a 90%-safe day, the riskiest days and QR cash-out pressure in the area. Synthetic demo.",
};

export default function Layout({ children }: { children: ReactNode }) {
  return children;
}

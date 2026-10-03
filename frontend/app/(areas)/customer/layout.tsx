import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "Customer · Rina",
  description: "Send money with a Pause Check, check a suspicious SMS and see the week ahead. Synthetic demo.",
};

export default function Layout({ children }: { children: ReactNode }) {
  return children;
}

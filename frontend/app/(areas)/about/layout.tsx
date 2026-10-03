import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "About us",
  description: "Who built UVERA, why, and how: seven AIs, nine Kaggle notebooks and one website in 72 hours.",
};

export default function Layout({ children }: { children: ReactNode }) {
  return children;
}

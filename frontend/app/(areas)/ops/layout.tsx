import type { Metadata } from "next";
import type { ReactNode } from "react";
import { OpsNav } from "@/components/ops/ops-nav";

export const metadata: Metadata = {
  title: "Operations · Nusrat",
  description: "Linked scam cases with evidence, a grounded brief, a dispute deadline clock and human decisions. Synthetic demo.",
};

export default function OpsLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <OpsNav />
      {children}
    </>
  );
}

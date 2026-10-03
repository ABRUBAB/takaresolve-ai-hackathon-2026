import type { Metadata } from "next";
import type { ReactNode } from "react";
import { AreaServices } from "@/components/shell/area-services";

export const metadata: Metadata = {
  title: "Operations · Abdur Rahman",
  description: "Linked scam cases with evidence, a grounded brief, a dispute deadline clock and human decisions. Synthetic demo.",
};

export default function OpsLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <AreaServices area="ops" />
      {children}
    </>
  );
}

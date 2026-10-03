import type { Metadata } from "next";
import type { ReactNode } from "react";
import { AreaServices } from "@/components/shell/area-services";

export const metadata: Metadata = {
  title: "Agent · Tanvir",
  description: "Cash to hold for a 90%-safe day, the demand forecast, peers and QR cash-out pressure in the area. Synthetic demo.",
};

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <>
      <AreaServices area="agent" />
      {children}
    </>
  );
}

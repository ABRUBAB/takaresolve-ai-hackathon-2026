import type { Metadata } from "next";
import type { ReactNode } from "react";
import { AreaServices } from "@/components/shell/area-services";

export const metadata: Metadata = {
  title: "Customer · Rubab",
  description: "Send money with a Pause Check, check a suspicious SMS and see the week ahead. Synthetic demo.",
};

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <>
      <AreaServices area="customer" />
      {children}
    </>
  );
}

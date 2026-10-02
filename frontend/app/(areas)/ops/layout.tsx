import type { ReactNode } from "react";
import { OpsNav } from "@/components/ops/ops-nav";

export default function OpsLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <OpsNav />
      {children}
    </>
  );
}

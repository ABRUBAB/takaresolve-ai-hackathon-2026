import type { ReactNode } from "react";
import { Footer } from "@/components/shell/footer";
import { TopBar } from "@/components/shell/top-bar";

export default function AreasLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <TopBar />
      <main id="main" className="min-h-[calc(100svh-3.5rem)]">
        {children}
      </main>
      <Footer />
    </>
  );
}

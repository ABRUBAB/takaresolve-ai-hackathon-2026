import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "User study",
  description: "A short, anonymous on-site usability study of the UVERA scam warning. Synthetic demo screens only.",
  robots: { index: false, follow: false },
};

export const viewport: Viewport = { width: "device-width", initialScale: 1, viewportFit: "cover" };

export default function StudyLayout({ children }: { children: ReactNode }) {
  return children;
}

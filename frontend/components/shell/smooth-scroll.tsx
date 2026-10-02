"use client";

import { ReactLenis } from "lenis/react";
import type { ReactNode } from "react";
import { useMotionPref } from "@/lib/motion-pref";

/** Lenis smooth scrolling on the homepage only; switched off when motion is paused or reduced. */
export function SmoothScroll({ children }: { children: ReactNode }) {
  const { animate } = useMotionPref();
  if (!animate) return <>{children}</>;
  return (
    <ReactLenis root options={{ lerp: 0.12, anchors: { offset: -64 } }}>
      {children}
    </ReactLenis>
  );
}

"use client";

import dynamic from "next/dynamic";

// Client only: each participant gets a random id, a balanced A/B + language assignment and an offline queue.
const StudyFlow = dynamic(() => import("@/components/study/flow").then((m) => m.StudyFlow), {
  ssr: false,
  loading: () => <div className="min-h-svh" />,
});

export default function StudyPage() {
  return <StudyFlow />;
}

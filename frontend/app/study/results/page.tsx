"use client";

import dynamic from "next/dynamic";

const StudyResults = dynamic(() => import("@/components/study/results").then((m) => m.StudyResults), {
  ssr: false,
  loading: () => <div className="min-h-svh" />,
});

export default function StudyResultsPage() {
  return <StudyResults />;
}

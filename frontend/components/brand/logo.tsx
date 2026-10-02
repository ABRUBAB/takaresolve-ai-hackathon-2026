import { cn } from "@/lib/utils";

/** The UVERA mark: a pause ring — a thin circle holding two bars. */
export function Mark({ className, animated = false }: { className?: string; animated?: boolean }) {
  return (
    <svg viewBox="0 0 32 32" className={cn("size-6", className)} aria-hidden="true">
      <circle cx="16" cy="16" r="14" fill="none" stroke="currentColor" strokeWidth="1.6" className={animated ? "pause-ring origin-center" : ""} />
      <rect x="11.2" y="10" width="3" height="12" rx="1" fill="currentColor" />
      <rect x="17.8" y="10" width="3" height="12" rx="1" fill="var(--volt)" />
    </svg>
  );
}

export function Logo({ className }: { className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-2 font-semibold tracking-[-0.03em]", className)}>
      <Mark />
      <span className="text-[17px]">UVERA</span>
    </span>
  );
}

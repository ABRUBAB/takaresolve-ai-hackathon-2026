import { Pointer } from "lucide-react";
import { cn } from "@/lib/utils";

/** Tells people that the thing next to it responds to a tap or click. */
export function TapHint({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <p className={cn("inline-flex items-center gap-2 rounded-full border border-dashed border-volt-ink/50 px-3 py-1 text-xs text-muted-foreground dark:border-volt/40", className)}>
      <span className="relative flex size-2">
        <span className="absolute inline-flex size-full animate-ping rounded-full bg-volt-ink opacity-60 dark:bg-volt" />
        <span className="relative inline-flex size-2 rounded-full bg-volt-ink dark:bg-volt" />
      </span>
      <Pointer className="size-3.5" aria-hidden="true" />
      {children}
    </p>
  );
}

import Link from "next/link";
import { Mark } from "@/components/brand/logo";
import { Footer } from "@/components/shell/footer";
import { TopBar } from "@/components/shell/top-bar";

export default function NotFound() {
  return (
    <>
      <TopBar />
      <main id="main" className="mx-auto flex min-h-[70svh] max-w-7xl flex-col items-start justify-center gap-6 px-4 py-24 md:px-6">
        <Mark className="size-14" />
        <p className="label-mono">404 · page not found</p>
        <h1 className="font-serif text-6xl leading-none md:text-7xl">
          We paused here. <span className="italic text-muted-foreground">Nothing to see.</span>
        </h1>
        <p className="max-w-md text-muted-foreground">The page you asked for does not exist. Every area of the demo is one click away.</p>
        <div className="flex flex-wrap gap-3">
          <Link href="/" className="inline-flex h-11 items-center rounded-full bg-volt px-6 text-sm font-semibold text-black">
            Back to the homepage
          </Link>
          <Link href="/trust" className="inline-flex h-11 items-center rounded-full border border-border px-6 text-sm">
            Trust Center
          </Link>
        </div>
      </main>
      <Footer />
    </>
  );
}

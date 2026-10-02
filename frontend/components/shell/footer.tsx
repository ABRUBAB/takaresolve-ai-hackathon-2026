import Link from "next/link";
import { Logo } from "@/components/brand/logo";

const REPO = "https://github.com/ABRUBAB/takaresolve-ai-hackathon-2026";

export function Footer() {
  return (
    <footer className="border-t border-border">
      <div className="mx-auto grid max-w-7xl gap-10 px-4 py-14 md:grid-cols-[2fr_1fr_1fr] md:px-6">
        <div className="space-y-4">
          <Logo />
          <p className="max-w-md text-sm text-muted-foreground">
            A hackathon prototype for AI DEV FEST 2026 (DIU-CPC). All people, wallets, shops and messages are synthetic. Not affiliated
            with, or endorsed by, any payment provider. Not financial advice.
          </p>
        </div>
        <nav aria-label="Areas" className="space-y-2 text-sm">
          <p className="label-mono mb-3">Areas</p>
          <Link className="block text-muted-foreground hover:text-foreground" href="/customer">Customer · Rina</Link>
          <Link className="block text-muted-foreground hover:text-foreground" href="/agent">Agent · Karim</Link>
          <Link className="block text-muted-foreground hover:text-foreground" href="/ops">Operations · Nusrat</Link>
          <Link className="block text-muted-foreground hover:text-foreground" href="/trust">Trust Center</Link>
        </nav>
        <nav aria-label="Project" className="space-y-2 text-sm">
          <p className="label-mono mb-3">Project</p>
          <a className="block text-muted-foreground hover:text-foreground" href={REPO} target="_blank" rel="noreferrer">Source code</a>
          <a className="block text-muted-foreground hover:text-foreground" href={`${REPO}/tree/main/notebooks`} target="_blank" rel="noreferrer">Notebooks</a>
          <a className="block text-muted-foreground hover:text-foreground" href={`${REPO}/tree/main/docs/model_cards`} target="_blank" rel="noreferrer">Model cards</a>
        </nav>
      </div>
      <div className="border-t border-border">
        <p className="mx-auto max-w-7xl px-4 py-5 font-mono text-[11px] text-faint md:px-6">UVERA · Trust you can verify · synthetic demo data</p>
      </div>
    </footer>
  );
}

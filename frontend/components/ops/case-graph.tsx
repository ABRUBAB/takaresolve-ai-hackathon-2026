"use client";

import type { Core, ElementDefinition } from "cytoscape";
import { Maximize2, Play } from "lucide-react";
import { useTheme } from "next-themes";
import { useEffect, useRef, useState } from "react";
import { tk } from "@/lib/format";
import type { GraphEdge, GraphNode } from "@/lib/types";
import { cn } from "@/lib/utils";

type Picked = { id: string; role: string; qr: string | null; sentIn: number; sentOut: number; links: number } | null;

const ROLE: Record<string, string> = { victim: "Customer who reported / was flagged", mule_suspect: "Suspected mule wallet", merchant: "QR merchant", agent: "Agent (cash-out point)" };

function css(name: string, fallback: string) {
  if (typeof window === "undefined") return fallback;
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;
}

/** Money paths inside one case: victims → mule wallets → shops / agents, replayable hop by hop. */
export function CaseGraph({ nodes, edges }: { nodes: GraphNode[]; edges: GraphEdge[] }) {
  const box = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const { resolvedTheme } = useTheme();
  const [hop, setHop] = useState(3);
  const [picked, setPicked] = useState<Picked>(null);
  const maxHop = Math.max(0, ...edges.map((e) => e.hop));

  useEffect(() => {
    let cy: Core | null = null;
    let alive = true;
    import("cytoscape").then(({ default: cytoscape }) => {
      if (!alive || !box.current) return;
      const fg = css("--foreground", "#fafafa");
      const muted = css("--faint", "#737373");
      const volt = resolvedTheme === "light" ? css("--volt-ink", "#4d7c0f") : css("--volt", "#d7ff3a");
      const risk = css("--risk", "#ff4d4f");
      const caution = css("--caution", "#f5a524");
      const bg = css("--card", "#111111");
      const ids = new Set(nodes.map((n) => n.id));
      const els: ElementDefinition[] = [
        ...nodes.map((n) => ({ data: { id: n.id, role: n.role, qr: n.qr_state ?? "none" } })),
        ...edges
          .filter((e) => ids.has(e.source) && ids.has(e.target))
          .map((e) => ({ data: { id: e.id, source: e.source, target: e.target, type: e.type, hop: e.hop, amount: e.amount } })),
      ];
      cy = cytoscape({
        container: box.current,
        elements: els,
        wheelSensitivity: 0.25,
        minZoom: 0.2,
        maxZoom: 3,
        style: [
          { selector: "node", style: { width: 8, height: 8, "background-color": muted, "border-width": 0 } },
          { selector: 'node[role = "mule_suspect"]', style: { width: 16, height: 16, "background-color": volt } },
          { selector: 'node[role = "merchant"]', style: { shape: "round-rectangle", width: 13, height: 13, "background-color": bg, "border-width": 1.5, "border-color": fg } },
          { selector: 'node[qr = "red"]', style: { "border-color": risk, "border-width": 2.5 } },
          { selector: 'node[qr = "amber"]', style: { "border-color": caution, "border-width": 2.5 } },
          { selector: 'node[role = "agent"]', style: { shape: "diamond", width: 13, height: 13, "background-color": fg } },
          { selector: "node:selected", style: { "border-width": 3, "border-color": volt, "overlay-opacity": 0 } },
          { selector: "edge", style: { width: 1, "line-color": muted, opacity: 0.35, "curve-style": "haystack" } },
          { selector: 'edge[hop >= 1][type = "p2p"]', style: { "line-color": volt, opacity: 0.8, width: 1.5 } },
          { selector: 'edge[type = "qr_pay"]', style: { "line-style": "dashed", "line-color": fg, opacity: 0.45 } },
          { selector: 'edge[type = "cash_out"]', style: { "line-style": "dotted", "line-color": fg, opacity: 0.45 } },
          { selector: ".hidden", style: { opacity: 0.03 } },
        ],
        layout: { name: "cose", animate: false, nodeRepulsion: () => 9000, idealEdgeLength: () => 40, gravity: 0.6, numIter: 1200, randomize: true },
      });
      cy.on("tap", "node", (evt) => {
        const n = evt.target;
        const inc = n.incomers("edge");
        const out = n.outgoers("edge");
        setPicked({
          id: n.id(),
          role: n.data("role"),
          qr: n.data("qr") === "none" ? null : n.data("qr"),
          sentIn: inc.reduce((s: number, e: { data: (k: string) => number }) => s + Number(e.data("amount")), 0),
          sentOut: out.reduce((s: number, e: { data: (k: string) => number }) => s + Number(e.data("amount")), 0),
          links: inc.length + out.length,
        });
      });
      cy.on("tap", (evt) => {
        if (evt.target === cy) setPicked(null);
      });
      cyRef.current = cy;
    });
    return () => {
      alive = false;
      cy?.destroy();
      cyRef.current = null;
    };
  }, [nodes, edges, resolvedTheme]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.batch(() => {
      cy.edges().forEach((e) => {
        if (Number(e.data("hop")) > hop) e.addClass("hidden");
        else e.removeClass("hidden");
      });
    });
  }, [hop]);

  const replay = () => {
    setHop(0);
    for (let h = 1; h <= maxHop; h++) setTimeout(() => setHop(h), h * 900);
  };

  return (
    <div className="relative">
      <div ref={box} className="h-[460px] w-full md:h-[560px]" role="img" aria-label={`Money-path graph with ${nodes.length} accounts and ${edges.length} transfers`} />
      <div className="absolute left-3 top-3 flex flex-wrap gap-2">
        <button onClick={replay} className="inline-flex items-center gap-1.5 rounded-full border border-border bg-background/80 px-3 py-1.5 text-xs backdrop-blur hover:border-foreground/40">
          <Play className="size-3" /> Replay money path
        </button>
        <button onClick={() => cyRef.current?.fit(undefined, 30)} className="grid size-8 place-items-center rounded-full border border-border bg-background/80 backdrop-blur" aria-label="Fit graph">
          <Maximize2 className="size-3.5" />
        </button>
      </div>
      <div className="absolute right-3 top-3 rounded-full border border-border bg-background/80 px-3 py-1.5 font-mono text-[11px] backdrop-blur">
        hop ≤ {hop}
        <input type="range" min={0} max={maxHop} value={hop} onChange={(e) => setHop(Number(e.target.value))} className="ml-2 w-20 align-middle" aria-label="Show money paths up to this hop" />
      </div>
      <ul className="flex flex-wrap gap-x-4 gap-y-1 border-t border-border px-4 py-3 text-xs text-muted-foreground">
        <li className="flex items-center gap-1.5"><span className="size-2 rounded-full bg-faint" /> Victims</li>
        <li className="flex items-center gap-1.5"><span className="size-3 rounded-full bg-volt-ink dark:bg-volt" /> Mule wallets</li>
        <li className="flex items-center gap-1.5"><span className="size-2.5 rounded-sm border border-foreground" /> Shops (red border = QR Shield flag)</li>
        <li className="flex items-center gap-1.5"><span className="size-2.5 rotate-45 bg-foreground" /> Agents</li>
        <li>— transfer · - - QR payment · ··· cash-out</li>
      </ul>
      {picked && (
        <div className="absolute bottom-16 left-3 w-64 rounded-2xl border border-border bg-popover p-3 text-sm shadow-xl">
          <p className="font-mono font-medium">{picked.id}</p>
          <p className="text-xs text-muted-foreground">{ROLE[picked.role] ?? picked.role}</p>
          <dl className="mt-2 space-y-1 text-xs">
            <div className="flex justify-between"><dt className="text-muted-foreground">Received in case</dt><dd className="num font-mono">{tk(picked.sentIn)}</dd></div>
            <div className="flex justify-between"><dt className="text-muted-foreground">Sent on</dt><dd className="num font-mono">{tk(picked.sentOut)}</dd></div>
            <div className="flex justify-between"><dt className="text-muted-foreground">Links</dt><dd className="num font-mono">{picked.links}</dd></div>
            {picked.qr && <div className="flex justify-between"><dt className="text-muted-foreground">QR Shield</dt><dd className={cn("font-mono", picked.qr === "red" && "text-risk")}>{picked.qr}</dd></div>}
          </dl>
        </div>
      )}
    </div>
  );
}

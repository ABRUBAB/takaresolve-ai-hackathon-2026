import { ImageResponse } from "next/og";

export const alt = "UVERA — Trust you can verify";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OpengraphImage() {
  return new ImageResponse(
    (
      <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column", justifyContent: "space-between", background: "#0a0a0a", color: "#fafafa", padding: 72, fontFamily: "serif" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 18, fontSize: 40, fontFamily: "sans-serif", fontWeight: 700, letterSpacing: -1 }}>
          <svg width="56" height="56" viewBox="0 0 32 32">
            <circle cx="16" cy="16" r="14" fill="none" stroke="#fafafa" strokeWidth="1.6" />
            <rect x="11.2" y="10" width="3" height="12" rx="1" fill="#fafafa" />
            <rect x="17.8" y="10" width="3" height="12" rx="1" fill="#d7ff3a" />
          </svg>
          UVERA
        </div>
        <div style={{ display: "flex", flexDirection: "column", fontSize: 112, lineHeight: 1 }}>
          <span>Trust you can</span>
          <span style={{ color: "#d7ff3a", fontStyle: "italic" }}>verify.</span>
        </div>
        <div style={{ display: "flex", fontSize: 26, color: "#a3a3a3", fontFamily: "sans-serif" }}>
          Pause a scam before the money moves · AI DEV FEST 2026 · synthetic demo
        </div>
      </div>
    ),
    size,
  );
}

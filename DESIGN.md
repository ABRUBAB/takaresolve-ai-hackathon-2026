---
name: UVERA
direction: editorial-monochrome
dials: {homepage: {variance: 7, motion: 7, density: 3}, portals: {variance: 3, motion: 3, density: 7}}
colors:
  dark:
    bg: "#0A0A0A"
    surface: "#111111"
    surface-2: "#171717"
    line: "#262626"
    text: "#FAFAFA"
    muted: "#A3A3A3"
    faint: "#737373"
  light:
    bg: "#FAFAFA"
    surface: "#FFFFFF"
    surface-2: "#F4F4F5"
    line: "#E4E4E7"
    text: "#0A0A0A"
    muted: "#52525B"
    faint: "#71717A"
  accent:
    volt: "#D7FF3A"          # fill with black text; as text on light use #4D7C0F
  state:                     # dark / light
    safe: ["#34D399", "#047857"]
    caution: ["#F5A524", "#B45309"]
    risk: ["#FF4D4F", "#B91C1C"]
    unsure: ["#A3A3A3", "#71717A"]   # always with dashed border + "?" icon
  output-type:               # chips: dark / light
    model: ["#60A5FA", "#1D4ED8"]
    rule: ["#A78BFA", "#6D28D9"]
    generated: ["#2DD4BF", "#0F766E"]
typography:
  sans: Geist
  mono: Geist Mono           # amounts, IDs, trace IDs, timers (tabular figures)
  display: Instrument Serif  # italic accents, homepage only
  bangla: Anek Bangla        # line-height 1.6
  display-size: "clamp(48px, 9vw, 144px)"
  display-tracking: "-0.04em"
  body-size: "15-16px"
radius: {card: 12, input: 8, chip: 999}
spacing-base: 4
elevation: hairlines; one shadow level for dialogs only
motion:
  hover-press: 150ms
  drawer-dialog: 220ms
  risk-reveal: 400ms
  homepage-section: 600-900ms
  easing-enter: ease-out
  reduced-motion: instant state, no movement
breakpoints: [640, 768, 1024, 1280, 1536]
---

# UVERA design system

**Feeling:** calm, precise, trustworthy — a premium annual report, not a crypto app.

## Rules
- **Colour is reserved for meaning.** Surfaces are black/white/grey. Red/amber/green/grey = risk states. Blue/violet/teal = output type (model / rule / generated). **Volt** appears only at the single most important moment: the Pause.
- **Never colour alone:** every state has an icon and a word.
- **"Not sure" is calm:** grey, dashed border, "?" icon, no motion.
- **The pause ring** (a thin circle that expands and holds) is the brand motif: logo, homepage 3D, Pause Check, loading states.
- Hairlines (1 px `line`) instead of shadows. Large type on the homepage; dense, quiet portals.
- GSAP + Lenis only on the homepage; portals use Motion only.

## Don'ts
- No purple/blue AI gradients, neon glows, robot or brain imagery, decorative 3D, glassmorphism on content.
- No bounce/shake on risk or error states.
- No upay logo, colours or screenshots (our own brand).
- No number on screen that doesn't come from `reports/*.json` or the API.

Component sources and licenses: [`docs/third_party.md`](docs/third_party.md).

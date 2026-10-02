import { DecisionFlow } from "@/components/home/flow";
import { Hero } from "@/components/home/hero";
import { LivePause } from "@/components/home/live-pause";
import { AiOrbit } from "@/components/home/orbit";
import { Results } from "@/components/home/results";
import { Portals, Principles } from "@/components/home/sections";
import { Story } from "@/components/home/story";
import { Footer } from "@/components/shell/footer";
import { SmoothScroll } from "@/components/shell/smooth-scroll";
import { TopBar } from "@/components/shell/top-bar";

export default function Home() {
  return (
    <SmoothScroll>
      <TopBar floating />
      <main id="main">
        <Hero />
        <Story />
        <LivePause />
        <DecisionFlow />
        <AiOrbit />
        <Results />
        <Principles />
        <Portals />
      </main>
      <Footer />
    </SmoothScroll>
  );
}

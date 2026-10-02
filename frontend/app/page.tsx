import { Hero } from "@/components/home/hero";
import { LivePause } from "@/components/home/live-pause";
import { Results } from "@/components/home/results";
import { AiGrid, Portals, Principles } from "@/components/home/sections";
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
        <Results />
        <AiGrid />
        <Principles />
        <Portals />
      </main>
      <Footer />
    </SmoothScroll>
  );
}

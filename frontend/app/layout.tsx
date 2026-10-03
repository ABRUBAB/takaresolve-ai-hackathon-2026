import type { Metadata, Viewport } from "next";
import { Anek_Bangla, Geist, Geist_Mono, Instrument_Serif } from "next/font/google";
import { ThemeProvider } from "next-themes";
import { Toaster } from "@/components/ui/sonner";
import { LangProvider } from "@/lib/i18n";
import "./globals.css";

const geist = Geist({ variable: "--font-geist", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });
const instrument = Instrument_Serif({ variable: "--font-instrument", subsets: ["latin"], weight: "400", style: ["normal", "italic"] });
const anek = Anek_Bangla({ variable: "--font-anek", subsets: ["bengali", "latin"] });

const SITE = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";
const DESCRIPTION =
  "UVERA is a trust layer for mobile money: it pauses a scam before the money moves, helps agents hold enough cash, spots QR codes used as hidden cash-out and joins alerts into one case. Synthetic demo data.";

export const metadata: Metadata = {
  metadataBase: new URL(SITE),
  title: { default: "UVERA — Trust you can verify", template: "%s · UVERA" },
  description: DESCRIPTION,
  applicationName: "UVERA",
  openGraph: { type: "website", siteName: "UVERA", title: "UVERA — Trust you can verify", description: DESCRIPTION, url: "/" },
  twitter: { card: "summary_large_image", title: "UVERA — Trust you can verify", description: DESCRIPTION },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: dark)", color: "#0a0a0a" },
    { media: "(prefers-color-scheme: light)", color: "#fafafa" },
  ],
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" suppressHydrationWarning className={`${geist.variable} ${geistMono.variable} ${instrument.variable} ${anek.variable} h-full`}>
      <body className="min-h-full">
        <ThemeProvider attribute="class" defaultTheme="dark" enableSystem={false} disableTransitionOnChange>
          <LangProvider>
            <a
              href="#main"
              className="sr-only z-[100] rounded-full bg-volt px-4 py-2 font-medium text-black focus:not-sr-only focus:fixed focus:left-4 focus:top-4"
            >
              Skip to content
            </a>
            {children}
            <Toaster position="bottom-right" />
          </LangProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}

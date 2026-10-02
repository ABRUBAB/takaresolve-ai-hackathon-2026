import type { Metadata } from "next";
import { Anek_Bangla, Geist, Geist_Mono, Instrument_Serif } from "next/font/google";
import { ThemeProvider } from "next-themes";
import { Toaster } from "@/components/ui/sonner";
import { LangProvider } from "@/lib/i18n";
import "./globals.css";

const geist = Geist({ variable: "--font-geist", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });
const instrument = Instrument_Serif({ variable: "--font-instrument", subsets: ["latin"], weight: "400", style: ["normal", "italic"] });
const anek = Anek_Bangla({ variable: "--font-anek", subsets: ["bengali", "latin"] });

export const metadata: Metadata = {
  title: "UVERA — Trust you can verify",
  description: "AI that pauses scams before money moves, protects agents from QR cash-out abuse, and turns many alerts into one case. Synthetic demo data.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" suppressHydrationWarning className={`${geist.variable} ${geistMono.variable} ${instrument.variable} ${anek.variable} h-full`}>
      <body className="min-h-full">
        <ThemeProvider attribute="class" defaultTheme="dark" enableSystem={false} disableTransitionOnChange>
          <LangProvider>
            {children}
            <Toaster position="bottom-right" />
          </LangProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}

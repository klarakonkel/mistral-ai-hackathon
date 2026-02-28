import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "KotoFlow - Automate Anything by Talking",
  description:
    "KotoFlow lets you build powerful automations just by describing what you want — no coding required. Speak or type, and your workflow is ready in seconds.",
  keywords: ["automation", "no-code", "voice", "workflow", "AI", "productivity"],
  authors: [{ name: "KotoFlow" }],
  openGraph: {
    title: "KotoFlow - Automate Anything by Talking",
    description: "Build powerful automations just by describing what you want. No coding required.",
    type: "website",
  },
  icons: { icon: "/favicon.ico" },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  themeColor: "#030712",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="antialiased min-h-screen bg-gray-950 text-gray-50">
        {children}
      </body>
    </html>
  );
}

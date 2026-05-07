import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

// Standardize on Inter for UI as per design system
const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

// Standardize on JetBrains Mono for logs/telemetry as per design system
const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "AegisOps AI | SOC Readiness Command Center",
  description: "Advanced ATT&CK simulation turning attacker behavior into realtime detections on AMD MI300X.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${jetbrainsMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-[#050814] text-[#F8FAFC]">
        {children}
      </body>
    </html>
  );
}
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Paytree — Cold Outreach Generator",
  description: "Generate personalized cold outreach sequences for cannabis dispensaries",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen">{children}</body>
    </html>
  );
}

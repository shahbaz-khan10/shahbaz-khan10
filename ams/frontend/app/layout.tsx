import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "FCT ERP",
  description: "Garments factory ERP - Admin & Master System",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen">{children}</body>
    </html>
  );
}
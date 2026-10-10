import type { Metadata } from "next";
import "./globals.css";
import "maplibre-gl/dist/maplibre-gl.css";
export const metadata: Metadata = {
  title: "Sehat Grid · Care, connected",
  description:
    "An Islamabad hospital map and directory with simulated capacity, referral, and resource planning workflows.",
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

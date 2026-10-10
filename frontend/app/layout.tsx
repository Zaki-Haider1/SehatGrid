import type { Metadata } from "next";
import "./globals.css";
import "maplibre-gl/dist/maplibre-gl.css";
export const metadata: Metadata = {
  title: "Sehat Grid · Care, connected",
  description:
    "A synthetic Islamabad primary-care network for hospital operators and monthly resource planners.",
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

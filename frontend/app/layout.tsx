import type { Metadata } from "next";
import "./globals.css";
import "./city-theme.css";
import "./city-refinements.css";
export const metadata: Metadata = {
  title: "Sehat Grid · Care, connected",
  description:
    "Explore Islamabad’s hospital network, coordinate referrals and onboard services in one connected workspace.",
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

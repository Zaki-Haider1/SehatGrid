import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {
  title: "Sehat Grid · Care, connected",
  description:
    "A shared view of healthcare capacity, referrals, and resources. Synthetic MVP demo.",
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

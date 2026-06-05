import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "J.A.R.V.I.S.",
  description: "AI Companion",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

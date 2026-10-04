import type { Metadata } from "next";
import "./globals.css";
import "./aurora.css";
import "./urdu-font.css";
import "./modern.css";

export const metadata: Metadata = {
  title: "Dawa-e-Nuskha — Understand your prescription",
  description: "Read, organize and review prescriptions with accessible tools and transparent uncertainty.",
  icons: {
    icon: "/brand/monogram.png",
    shortcut: "/brand/monogram.png",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  // Extensions can inject root attributes before hydration; keep suppression shallow.
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="antialiased" suppressHydrationWarning>{children}</body>
    </html>
  );
}
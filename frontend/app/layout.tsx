import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FT-04: Algorithmic Dunning & Churn Retry Middleware",
  description:
    "AI middleware mitigating passive credit card churn with calibrated CatBoost recovery scheduling, dynamic multi-gateway routing, and circuit breaker protection.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="bg-obsidian text-slate-100 min-h-screen antialiased selection:bg-cyan-500/20 selection:text-cyan-300">
        {children}
      </body>
    </html>
  );
}


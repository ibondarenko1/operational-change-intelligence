import Link from "next/link";
import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "Operational Change Intelligence",
  description: "Risk intelligence for Microsoft security changes",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <div className="app-shell">
          <aside className="sidebar">
            <Link className="brand" href="/">
              <span>OCI</span>
              <strong>Operational Change Intelligence</strong>
            </Link>
            <nav>
              <Link href="/">Dashboard</Link>
              <Link href="/changes/new">New Change</Link>
              <Link href="/historical">Historical Changes</Link>
              <Link href="/analytics">Human Error Analytics</Link>
            </nav>
          </aside>
          <main className="main-content">{children}</main>
        </div>
      </body>
    </html>
  );
}

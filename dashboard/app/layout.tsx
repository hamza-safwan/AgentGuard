import "./globals.css";
import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "AgentGuard",
  description: "CI/CD reliability and security testing for LLM agents"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="shell">
          <aside className="sidebar">
            <div className="brand">AgentGuard</div>
            <nav className="nav">
              <Link href="/">Overview</Link>
              <Link href="/runs">Runs</Link>
              <Link href="/compare">Compare</Link>
            </nav>
          </aside>
          <main className="main">{children}</main>
        </div>
      </body>
    </html>
  );
}

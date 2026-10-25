import { Link2, Trophy } from "lucide-react";
import type { Metadata } from "next";
import { Poppins } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const poppins = Poppins({
  subsets: ["latin"],
  weight: ["100", "300", "400", "500", "600", "700"],
  variable: "--font-sans", // important
});

export const metadata: Metadata = {
  title: "Word Chain Game",
  description: "An AI-opponent word chain game built with Google ADK.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${poppins.variable} h-full antialiased`}>
      <body className="flex h-full flex-col">
        <header className="shrink-0 border-b border-border">
          <nav className="mx-auto flex max-w-3xl items-center justify-between px-6 py-4">
            <Link href="/" className="flex items-center gap-2 font-semibold">
              <Link2 className="h-5 w-5" />
              Word Chain
            </Link>
            <Link
              href="/leaderboard"
              className="cursor-pointer flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
            >
              <Trophy className="h-4 w-4" />
              Leaderboard
            </Link>
          </nav>
        </header>
        <main className="flex min-h-0 flex-1 flex-col">{children}</main>
      </body>
    </html>
  );
}

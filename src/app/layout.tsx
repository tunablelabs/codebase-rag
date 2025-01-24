import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";
import Link from "next/link";
import NavLink from "@/app/NavLink";
import { GitHubLogoIcon } from "@radix-ui/react-icons";
import { ColorSchemeScript } from '@mantine/core';

const geistSans = localFont({
  src: "./fonts/GeistVF.woff",
  variable: "--font-geist-sans",
  weight: "100 900",
});
const geistMono = localFont({
  src: "./fonts/GeistMonoVF.woff",
  variable: "--font-geist-mono",
  weight: "100 900",
});

export const metadata: Metadata = {
  title: "Code RAG Assistant",
  description: "Quickstart",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full">

      <head>
        <ColorSchemeScript defaultColorScheme="dark" />
      </head>
      <body
        className={`${geistSans.variable} ${geistMono.variable} flex min-h-full flex-col bg-gradient-to-br from-slate-100 to-white dark:from-slate-950 dark:to-slate-900 text-slate-900 dark:text-slate-100 antialiased`}
      >
        <header className="bg-white/50 dark:bg-slate-900/50 backdrop-blur-sm border-b border-slate-200 dark:border-slate-800 sticky top-0 z-50">
          <div className="mx-auto flex max-w-5xl items-center justify-center px-4 py-1 relative">
            <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
              Code RAG Assistant
            </h1>
            <div className="absolute right-4 flex items-center gap-6">
              <NavLink
                className="text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white transition-colors"
                href="/"
              >
                Ask a Question
              </NavLink>
              <a
                href="https://github.com"
                className="text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white transition-colors"
              >
                <GitHubLogoIcon width="24" height="24" />
              </a>
            </div>
          </div>
        </header>

        <main className="flex-grow flex-col px-1 py-1">
          {children}
        </main>

        <footer className="border-t border-slate-200 dark:border-slate-800 sticky bottom-0" >
          <div className="mx-auto max-w-5xl px-4 text-sm text-slate-600 dark:text-slate-400">
            Powered by{" "}
            <Link
              className="font-medium text-blue-600 dark:text-blue-400 hover:underline"
              target="_blank"
              href="https://www.tunablelabs.ai/"
            >
              TunableLabs
            </Link>
          </div>
        </footer>
      </body>
    </html>
  );
}
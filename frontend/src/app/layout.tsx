
import { SessionProvider } from "@/context/SessionProvider";
import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";
import Header from "@/components/layout/Header";
import Footer from "@/components/layout/Footer";
import { createClient } from "@/utils/supabase/server";

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
  description: "AI-powered code analysis and chat assistant",
  keywords: "code analysis, AI assistant, development tools",
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const supabase = await createClient()
  const { data, error } = await supabase.auth.getUser()
  return (
    <html lang="en" className="h-full" suppressHydrationWarning>
      <body
        className={`
          ${geistSans.variable} 
          ${geistMono.variable} 
          flex min-h-full flex-col 
          bg-gradient-to-br from-base-100 to-base-200
          text-base-content
          antialiased
          transition-colors duration-200
        `}
      >
        <SessionProvider>
          <Header user={data?.user || null} />
          <main className="flex-grow flex-col px-4 py-6">
            {children}
          </main>
          <Footer />
        </SessionProvider>
      </body>
    </html>
  );
}
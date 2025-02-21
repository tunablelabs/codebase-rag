'use client'
import NavLink from "@/app/NavLink";
import { GitHubLogoIcon } from "@radix-ui/react-icons";
import { ExternalLink } from 'lucide-react';
import { ThemeToggle } from '@/app/ThemeToggle';
import type { User } from "@supabase/supabase-js";
import { Scale, LogOut, User2 } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { signOut } from "@/app/(auth)/login/actions";
import { useRouter } from "next/navigation";
export default function Header({ user }: { user: User | null }) {
  const router = useRouter();
  const signOut = async () => {
    const res = await fetch("/api/signout", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
    });
    if (res.ok) {
      console.log('success signout')
      localStorage.setItem("logout", "true");
      router.push("/login?t=" + Date.now());
      window.location.reload(); // Ensure UI updates immediately
    }else{
      console.error("Failed to sign out");
    }
  }
  return (
    <header className="sticky top-0 z-50 bg-base-100/95 backdrop-blur-md border-b border-sky-800/50 h-12">
      <div className="w-full px-3">
        <div className="flex h-full items-center justify-between">
          <div className="flex items-center">
            <h1 className="text-2xl font-semibold tracking-tight flex items-center">
              <span className="bg-gradient-to-r from-blue-500 to-blue-600 bg-clip-text text-transparent">Code</span>
              <span className="bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent ml-1">RAG</span>
              <span className="text-base-content/80 ml-1">Assistant</span>
            </h1>
          </div>

          <nav className="flex items-center space-x-4">
            <NavLink
              className="group flex items-center px-2 py-1 text-sm font-medium 
                text-base-content/70 hover:text-primary transition-colors relative"
              href="/"
            >
              <span className="relative">
                Ask a Question
                <span className="absolute -bottom-0.5 left-0 h-0.5 w-0 bg-primary 
                  transition-all duration-300 group-hover:w-full" />
              </span>
            </NavLink>

            <a
              href="https://github.com"
              className="group flex items-center px-2 py-1 text-sm font-medium 
                text-base-content/70 hover:text-primary transition-colors relative"
              target="_blank"
              rel="noopener noreferrer"
            >
              <span className="flex items-center gap-1 relative">
                <GitHubLogoIcon className="w-4 h-4" />
                <span>GitHub</span>
                <ExternalLink className="w-3 h-3 opacity-0 -translate-y-1 
                  group-hover:opacity-100 group-hover:translate-y-0 
                  transition-all duration-300" />
              </span>
            </a>

            <ThemeToggle />

            <div className="flex items-center space-x-4 flex-1 justify-end">
            {user ? (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" className="relative h-8 w-8 rounded-full">
                    <Avatar className="h-8 w-8">
                      <AvatarImage src={user.user_metadata?.picture || ""} alt={user.email || ""} className="object-cover"/>
                      <AvatarFallback className="text-sm">{user.user_metadata?.full_name?.charAt(0).toUpperCase() || user.email?.charAt(0).toUpperCase()}</AvatarFallback>
                    </Avatar>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent className="w-56" align="end" forceMount>
                  <DropdownMenuItem className="flex items-center">
                    <User2 className="mr-2 h-4 w-4" />
                    <span className="text-sm">Profile</span>
                  </DropdownMenuItem>
                  <DropdownMenuItem className="flex items-center" onSelect={signOut} >
                    <LogOut className="mr-2 h-4 w-4" />
                    <span className="text-sm">Log out</span>
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            ) : (
              <Link href="/login">
                <Button variant="outline" className="border-blue-800 text-blue-400 hover:bg-blue-900 text-sm">
                  Login
                </Button>
              </Link>
            )}
        </div>
          </nav>
        </div>
      </div>
    </header>
  );
}
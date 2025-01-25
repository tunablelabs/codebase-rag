import NavLink from "@/app/NavLink";
import { GitHubLogoIcon } from "@radix-ui/react-icons";
import { ExternalLink } from 'lucide-react';
import { ThemeToggle } from '@/app/ThemeToggle';

export default function Header() {
  return (
    <header className="sticky top-0 z-50 bg-base-100/95 backdrop-blur-md border-b border-base-200">
      <div className="w-full px-4">
        <div className="flex h-16 items-center justify-between">
          <div className="flex items-center ml-0">
            <h1 className="text-2xl font-semibold tracking-tight flex items-center">
              <span className="bg-gradient-to-r from-blue-500 to-blue-600 bg-clip-text text-transparent">Code</span>
              <span className="bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent ml-1.5">RAG</span>
              <span className="text-base-content/80 ml-1.5">Assistant</span>
            </h1>
          </div>

          <nav className="flex items-center space-x-6">
            <NavLink
              className="group flex items-center px-3 py-2 text-sm font-medium 
                text-base-content/70 hover:text-primary
                transition-colors relative"
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
              className="group flex items-center px-3 py-2 text-sm font-medium 
                text-base-content/70 hover:text-primary
                transition-colors relative"
              target="_blank"
              rel="noopener noreferrer"
            >
              <span className="flex items-center gap-2 relative">
                <GitHubLogoIcon className="w-5 h-5" />
                <span>GitHub</span>
                <ExternalLink className="w-4 h-4 opacity-0 -translate-y-1 
                  group-hover:opacity-100 group-hover:translate-y-0 
                  transition-all duration-300" />
              </span>
            </a>

            <ThemeToggle />
          </nav>
        </div>
      </div>
    </header>
  );
}
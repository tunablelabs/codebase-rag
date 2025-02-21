"use client"
import { oAuthSignIn } from "@/app/(auth)/login/actions"
import { Button } from "@/components/ui/button"
import type { Provider } from "@supabase/supabase-js"
import { Github, Mail } from "lucide-react"
import React, { type JSX } from "react"

type OAuthProvider = {
  name: Provider
  displayName: string
  icon?: JSX.Element
}

export function OAuthButtons() {
  const oAuthProviders: OAuthProvider[] = [
    {
      name: "github",
      displayName: "GitHub",
      icon: <Github className="size-5" />,
    },
    {
      name: "google",
      displayName: "Google",
      icon: <Mail className="size-5" />,
    },
  ]

  return (
    <>
      {oAuthProviders.map((provider) => (
        <Button
          key={provider.name}
          className="w-full flex items-center justify-center gap-2 text-sm"
          variant="outline"
          onClick={async () => {
            console.log("clicked")
            await oAuthSignIn(provider.name)
          }}
        >
          {provider.icon}
          <span className="hidden sm:inline">Login with </span>
          {provider.displayName}
        </Button>
      ))}
    </>
  )
}

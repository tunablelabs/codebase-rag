"use client"

import { AlertCircle } from "lucide-react"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { useState, useEffect } from "react"

interface NotificationBannerProps {
  messagesLeft: number | null
  isVisible: boolean
}

export function NotificationBanner({ messagesLeft, isVisible }: NotificationBannerProps) {
  const [dismissed, setDismissed] = useState(false)
  
  // Reset dismissed state when messagesLeft changes
  useEffect(() => {
    setDismissed(false)
  }, [messagesLeft])
  
  if (!isVisible || dismissed || messagesLeft === null) return null
  
  const severity = messagesLeft <= 5 ? "high" : "medium"
  
  return (
    <Alert 
      variant={severity === "high" ? "destructive" : "default"}
      className="mb-4 animate-fadeIn relative"
    >
      <AlertCircle className="h-4 w-4" />
      <AlertTitle>Message Limit Approaching</AlertTitle>
      <AlertDescription>
        You have {messagesLeft} message{messagesLeft !== 1 ? 's' : ''} left in your current quota.
      </AlertDescription>
      <button 
        onClick={() => setDismissed(true)}
        className="absolute top-2 right-2 text-sm opacity-70 hover:opacity-100"
        aria-label="Dismiss notification"
      >
        ✕
      </button>
    </Alert>
  )
} 
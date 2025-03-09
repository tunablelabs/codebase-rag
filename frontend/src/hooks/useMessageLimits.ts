"use client"

import { useState, useEffect } from "react"

export function useMessageLimits() {
  const [messagesLeft, setMessagesLeft] = useState<number | null>(null)
  const [shouldShowNotification, setShouldShowNotification] = useState(false)
  
  const fetchMessageLimits = async () => {
    try {
      const response = await fetch("/api/user/message-limits")
      if (response.ok) {
        const data = await response.json()
        setMessagesLeft(data.messagesLeft)
        
        // Show notification only when approaching limits (10 or 5 messages left)
        setShouldShowNotification(data.messagesLeft <= 10)
      }
    } catch (error) {
      console.error("Failed to fetch message limits:", error)
    }
  }
  
  useEffect(() => {
    fetchMessageLimits()
    
    // Refresh limits periodically
    const intervalId = setInterval(fetchMessageLimits, 60000) // every minute
    
    return () => clearInterval(intervalId)
  }, [])
  
  return {
    messagesLeft,
    shouldShowNotification,
    refreshLimits: fetchMessageLimits
  }
} 
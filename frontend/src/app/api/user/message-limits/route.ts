import { createClient } from "@/utils/supabase/server"
import { NextResponse } from "next/server"

export async function GET() {
  try {
    const supabase = await createClient()
    const { data: { user } } = await supabase.auth.getUser()
    
    if (!user) {
      return NextResponse.json(
        { error: "Unauthorized" },
        { status: 401 }
      )
    }
    
    // Fetch user's message limits from your backend
    const response = await fetch(`${process.env.BACKEND_URL}/api/user/message-limits`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${user.id}`
      }
    })
    
    if (!response.ok) {
      throw new Error("Failed to fetch message limits")
    }
    
    const data = await response.json()
    
    return NextResponse.json({
      messagesLeft: data.messagesLeft
    })
  } catch (error) {
    console.error("Error fetching message limits:", error)
    return NextResponse.json(
      { error: "Failed to fetch message limits" },
      { status: 500 }
    )
  }
} 
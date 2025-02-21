"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Scale, Github, Mail } from "lucide-react"
import Link from "next/link"
import { login, signup } from "./actions"
import { OAuthButtons } from "@/components/buttons/oauth-signin"

export default function AuthPage() {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const handleLogin = async (formData: FormData) => {
    setIsLoading(true)
    setError(null)
    setSuccess(null)

    try {
      const { error } = await login(formData)
      if (error) {
        setError(error)
      } else {
        setSuccess("Login successful!")
      }
    } catch (err) {
      setError("Login failed. Please check your credentials.")
    } finally {
      setIsLoading(false)
    }
  }

  const handleSignup = async (formData: FormData) => {
    setIsLoading(true)
    setError(null)
    setSuccess(null)

    try {
      const { error } = await signup(formData)
      if (error) {
        setError(error)
      } else {
        setSuccess("Signup successful! Please check your email to verify your account.")
      }
    } catch (err) {
      setError("Signup failed. Please try again.")
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-b  flex flex-col justify-center items-center px-4">
      <div className="mb-8 flex items-center space-x-2">
        <Scale className="h-8 w-8 text-blue-500" />
        <span className="text-2xl font-bold">Code Base RAG</span>
      </div>
      <Card className="w-full max-w-md p-8 border-gray-700">
        <Tabs defaultValue="login" className="w-full">
          <TabsList className="grid w-full grid-cols-2 mb-8">
            <TabsTrigger value="login">Login</TabsTrigger>
            <TabsTrigger value="signup">Sign Up</TabsTrigger>
          </TabsList>
          <TabsContent value="login">
            <form action={handleLogin} className="space-y-4">
              <Input
                type="email"
                name="email"
                placeholder="Email"
                required
                className=" text-white placeholder:text-gray-400"
              />
              <Input
                type="password"
                name="password"
                placeholder="Password"
                required
                className=" border-gray-600 text-white placeholder:text-gray-400"
              />
              {error && <p className="text-red-500 text-sm">{error}</p>}
              {success && <p className="text-green-500 text-sm">{success}</p>}
              <Button type="submit" className="w-full" disabled={isLoading}>
                {isLoading ? "Logging in..." : "Login"}
              </Button>
            </form>
          </TabsContent>
          <TabsContent value="signup">
            <form action={handleSignup} className="space-y-4">
              <Input
                type="text"
                name="name"
                placeholder="Full Name"
                required
                className="bg-gray-700/50 border-gray-600 text-white placeholder:text-gray-400"
              />
              <Input
                type="email"
                name="email"
                placeholder="Email"
                required
                className="bg-gray-700/50 border-gray-600 text-white placeholder:text-gray-400"
              />
              <Input
                type="password"
                name="password"
                placeholder="Password"
                required
                className="bg-gray-700/50 border-gray-600 text-white placeholder:text-gray-400"
              />
              {error && <p className="text-red-500 text-sm">{error}</p>}
              {success && <p className="text-green-500 text-sm">{success}</p>}
              <Button type="submit" className="w-full" disabled={isLoading}>
                {isLoading ? "Signing up..." : "Sign Up"}
              </Button>
            </form>
          </TabsContent>
        </Tabs>
        <div className="mt-6">
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <span className="w-full border-t border-gray-600" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-gray-800 px-2 text-gray-400">Or continue with</span>
            </div>
          </div>
          <div className="mt-6 grid grid-cols-2 gap-4">
            <OAuthButtons />
          </div>
        </div>
      </Card>
      <p className="mt-8 text-center text-sm text-gray-400">
        By signing up, you agree to our{" "}
        <Link href="/terms" className="font-medium text-blue-400 hover:underline">
          Terms of Service
        </Link>{" "}
        and{" "}
        <Link href="/privacy" className="font-medium text-blue-400 hover:underline">
          Privacy Policy
        </Link>
        .
      </p>
    </div>
  )
}
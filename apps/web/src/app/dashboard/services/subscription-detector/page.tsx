"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { FileUpload } from "@/components/file-upload"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { createClient } from "@/lib/supabase/client"

// API Helper
const API_URL = process.env.NEXT_PUBLIC_SUBSCRIPTION_SERVICE_URL || "http://localhost:8001/v1";
const API_KEY = process.env.NEXT_PUBLIC_SUBSCRIPTION_API_KEY || "demo-key";

export default function SubscriptionDetectorPage() {
  const router = useRouter()
  const [isLoading, setIsLoading] = useState(false)
  const [analyses, setAnalyses] = useState<any[]>([])
  const supabase = createClient()

  useEffect(() => {
    fetchAnalyses()
  }, [])

  const getHeaders = async () => {
    const { data: { session } } = await supabase.auth.getSession()
    const accountId = session?.user?.id || "00000000-0000-0000-0000-000000000000";

    return {
      "X-API-Key": API_KEY,
      "X-Account-ID": accountId,
      "X-User-ID": session?.user?.id || "",
    }
  }

  const fetchAnalyses = async () => {
    try {
        const headers = await getHeaders();
        const res = await fetch(`${API_URL}/analyses`, { headers });
        if (res.ok) {
            const data = await res.json();
            setAnalyses(data.data || []);
        }
    } catch (e) {
        console.error(e)
    }
  }

  const handleUpload = async (file: File) => {
    setIsLoading(true)
    try {
      const headers = await getHeaders();
      const formData = new FormData()
      formData.append("file", file)

      const res = await fetch(`${API_URL}/analyses`, {
        method: "POST",
        headers: {
            ...headers,
        },
        body: formData
      })

      if (!res.ok) throw new Error("Upload failed")

      const data = await res.json()

      // Start analysis
      await fetch(`${API_URL}/analyses/${data.analysis_id}/run`, {
        method: "POST",
        headers
      })

      router.push(`/dashboard/services/subscription-detector/${data.analysis_id}`)
    } catch (error) {
      console.error(error)
      alert("Error uploading file")
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="container mx-auto py-10 space-y-8">
      <div className="flex flex-col space-y-2">
        <h1 className="text-3xl font-bold">Subscription Leak Detector</h1>
        <p className="text-muted-foreground">Upload your bank statement to find hidden subscriptions.</p>
      </div>

      <FileUpload onUpload={handleUpload} isLoading={isLoading} />

      <div className="space-y-4">
        <h2 className="text-xl font-semibold">Recent Analyses</h2>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {analyses.map((analysis) => (
                <Card key={analysis.id} className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => router.push(`/dashboard/services/subscription-detector/${analysis.id}`)}>
                    <CardHeader>
                        <CardTitle className="text-base truncate">{analysis.filename}</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="flex justify-between text-sm">
                            <span className="capitalize text-muted-foreground">{analysis.status}</span>
                            <span>{new Date(analysis.created_at).toLocaleDateString()}</span>
                        </div>
                        {analysis.status === 'completed' && (
                            <div className="mt-2 text-sm font-medium text-green-600">
                                Found {analysis.subscriptions_found} subscriptions
                            </div>
                        )}
                    </CardContent>
                </Card>
            ))}
            {analyses.length === 0 && (
                <p className="text-muted-foreground col-span-full">No analyses found.</p>
            )}
        </div>
      </div>
    </div>
  )
}

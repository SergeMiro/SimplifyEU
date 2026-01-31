"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { useTheme } from "next-themes"
import { FileUpload } from "@/components/file-upload"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { createClient } from "@/lib/supabase/client"
import { Trash2, Sparkles, Moon, Sun, Loader2 } from "lucide-react"
import { toast } from "sonner" // Assuming sonner is installed as per package.json

// API Helper
const API_URL = process.env.NEXT_PUBLIC_SUBSCRIPTION_SERVICE_URL || "http://localhost:8001/v1";
const API_KEY = process.env.NEXT_PUBLIC_SUBSCRIPTION_API_KEY || "demo-key";

export default function SubscriptionDetectorPage() {
  const router = useRouter()
  const { setTheme, theme } = useTheme()
  const [isLoading, setIsLoading] = useState(false)
  const [isDeleting, setIsDeleting] = useState<string | null>(null)
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

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation() // Prevent card click
    if (!confirm("Are you sure you want to delete this analysis?")) return;

    setIsDeleting(id)
    try {
        const headers = await getHeaders();
        const res = await fetch(`${API_URL}/analyses/${id}`, { 
            method: 'DELETE',
            headers 
        });
        
        if (res.ok) {
            toast.success("Analysis deleted")
            setAnalyses(prev => prev.filter(a => a.id !== id))
        } else {
            throw new Error("Failed to delete")
        }
    } catch (e) {
        toast.error("Error deleting analysis")
        console.error(e)
    } finally {
        setIsDeleting(null)
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
      toast.error("Error uploading file")
    } finally {
      setIsLoading(false)
    }
  }

  const handleUpgrade = () => {
      // Mock Stripe Checkout
      toast.info("Redirecting to Stripe Checkout...")
      setTimeout(() => {
          alert("This would open the Stripe payment page in production.")
      }, 1000)
  }

  return (
    <div className="container mx-auto py-10 space-y-8">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div className="flex flex-col space-y-2">
            <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-violet-600">
                Subscription Leak Detector
            </h1>
            <p className="text-muted-foreground">Upload your bank statement to find hidden subscriptions.</p>
        </div>
        
        <div className="flex items-center gap-2">
            <Button variant="outline" size="icon" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}>
                <Sun className="h-[1.2rem] w-[1.2rem] rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
                <Moon className="absolute h-[1.2rem] w-[1.2rem] rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
                <span className="sr-only">Toggle theme</span>
            </Button>
            <Button onClick={handleUpgrade} className="bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-600 hover:to-orange-700 text-white border-0">
                <Sparkles className="mr-2 h-4 w-4" />
                Upgrade to PRO
            </Button>
        </div>
      </div>

      <FileUpload onUpload={handleUpload} isLoading={isLoading} />

      <div className="space-y-4">
        <h2 className="text-xl font-semibold">Recent Analyses</h2>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {analyses.map((analysis) => (
                <Card key={analysis.id} className="group cursor-pointer hover:shadow-md transition-all hover:border-primary/50 relative overflow-hidden" onClick={() => router.push(`/dashboard/services/subscription-detector/${analysis.id}`)}>
                    <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity z-10">
                        <Button 
                            variant="destructive" 
                            size="icon" 
                            className="h-8 w-8"
                            onClick={(e) => handleDelete(e, analysis.id)}
                            disabled={isDeleting === analysis.id}
                        >
                            {isDeleting === analysis.id ? <Loader2 className="h-4 w-4 animate-spin"/> : <Trash2 className="h-4 w-4" />}
                        </Button>
                    </div>
                    <CardHeader>
                        <CardTitle className="text-base truncate pr-8">{analysis.filename}</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="flex justify-between text-sm">
                            <span className={`capitalize px-2 py-0.5 rounded-full text-xs font-medium ${
                                analysis.status === 'completed' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' : 
                                analysis.status === 'failed' ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400' :
                                'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
                            }`}>
                                {analysis.status}
                            </span>
                            <span className="text-muted-foreground">{new Date(analysis.created_at).toLocaleDateString()}</span>
                        </div>
                        {analysis.status === 'completed' && (
                            <div className="mt-3 text-sm font-medium">
                                <span className="text-primary">{analysis.subscriptions_found} subscriptions</span>
                                {analysis.potential_savings_eur > 0 && (
                                    <span className="block text-xs text-muted-foreground mt-1">
                                        Potential savings: €{analysis.potential_savings_eur.toFixed(2)}/mo
                                    </span>
                                )}
                            </div>
                        )}
                    </CardContent>
                </Card>
            ))}
            {analyses.length === 0 && (
                <div className="col-span-full text-center py-10 border-2 border-dashed rounded-lg">
                    <p className="text-muted-foreground">No analyses found. Upload your first statement above!</p>
                </div>
            )}
        </div>
      </div>
    </div>
  )
}

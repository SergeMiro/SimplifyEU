"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { useTheme } from "next-themes"
import { FileUpload } from "@/components/file-upload"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { authClient, getAuthToken } from "@/lib/auth-client"
import { 
    Trash2, 
    Sparkles, 
    Moon, 
    Sun, 
    Loader2, 
    TrendingUp,
    FileText,
    Calendar,
    ChevronRight
} from "lucide-react"
import { toast } from "sonner"

const API_URL = process.env.NEXT_PUBLIC_SUBSCRIPTION_SERVICE_URL || "http://localhost:8001/v1";
// WARNING: NEXT_PUBLIC_ vars are exposed to the browser. Do NOT put secret API keys here.
// TODO: Migrate API calls to a Next.js API route to keep keys server-side.
const API_KEY = process.env.NEXT_PUBLIC_SUBSCRIPTION_API_KEY || "";
if (!API_KEY && typeof window !== "undefined") {
  console.warn("Subscription API key is not configured. Set NEXT_PUBLIC_SUBSCRIPTION_API_KEY in environment.");
}

export default function SubscriptionDetectorPage() {
  const router = useRouter()
  const { setTheme, theme } = useTheme()
  const [isLoading, setIsLoading] = useState(false)
  const [isDeleting, setIsDeleting] = useState<string | null>(null)
  const [analyses, setAnalyses] = useState<any[]>([])
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
    fetchAnalyses()
  }, [])

  const getHeaders = async () => {
    const { data: session } = await authClient.getSession()
    const accountId = session?.user?.id || "00000000-0000-0000-0000-000000000000";
    const token = await getAuthToken()

    return {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      "X-API-Key": API_KEY,
      "X-Account-ID": accountId,
      "X-User-ID": session?.user?.id || "anonymous",
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
    e.stopPropagation()
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
      toast.info("Redirecting to Stripe Checkout...")
      setTimeout(() => {
          alert("This would open the Stripe payment page in production.")
      }, 1000)
  }

  const getStatusStyles = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-400 border-emerald-200 dark:border-emerald-800'
      case 'failed':
        return 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400 border-red-200 dark:border-red-800'
      case 'processing':
        return 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-400 border-blue-200 dark:border-blue-800'
      default:
        return 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-400 border-amber-200 dark:border-amber-800'
    }
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric',
      year: date.getFullYear() !== new Date().getFullYear() ? 'numeric' : undefined
    })
  }

  return (
    <div className="container mx-auto py-10 space-y-10">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div className="space-y-2">
            <h1 className="text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-600 via-violet-600 to-purple-600">
                Subscription Leak Detector
            </h1>
            <p className="text-muted-foreground text-lg">
                Upload your bank statement to find hidden subscriptions and save money.
            </p>
        </div>
        
        <div className="flex items-center gap-3">
            {mounted && (
              <Button 
                variant="outline" 
                size="icon" 
                onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
                className="relative overflow-hidden"
              >
                  <Sun className="h-[1.2rem] w-[1.2rem] rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
                  <Moon className="absolute h-[1.2rem] w-[1.2rem] rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
                  <span className="sr-only">Toggle theme</span>
              </Button>
            )}
            <Button 
              onClick={handleUpgrade} 
              className="bg-gradient-to-r from-amber-500 via-orange-500 to-red-500 hover:from-amber-600 hover:via-orange-600 hover:to-red-600 text-white border-0 shadow-lg shadow-orange-500/25"
            >
                <Sparkles className="mr-2 h-4 w-4" />
                Upgrade to PRO
            </Button>
        </div>
      </div>

      {/* File Upload */}
      <FileUpload onUpload={handleUpload} isLoading={isLoading} />

      {/* Recent Analyses */}
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-semibold flex items-center gap-2">
            <FileText className="h-6 w-6 text-primary" />
            Recent Analyses
          </h2>
          {analyses.length > 0 && (
            <span className="text-sm text-muted-foreground">
              {analyses.length} {analyses.length === 1 ? 'analysis' : 'analyses'}
            </span>
          )}
        </div>
        
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {analyses.map((analysis) => (
                <Card 
                  key={analysis.id} 
                  className="group cursor-pointer transition-all duration-300 hover:shadow-lg hover:shadow-primary/5 hover:border-primary/30 hover:-translate-y-1 relative overflow-hidden bg-card/50 backdrop-blur-sm" 
                  onClick={() => router.push(`/dashboard/services/subscription-detector/${analysis.id}`)}
                >
                    {/* Gradient Accent */}
                    <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-blue-500 via-violet-500 to-purple-500 opacity-0 group-hover:opacity-100 transition-opacity" />
                    
                    {/* Delete Button */}
                    <div className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 transition-all z-10">
                        <Button 
                            variant="destructive" 
                            size="icon" 
                            className="h-8 w-8 shadow-md"
                            onClick={(e) => handleDelete(e, analysis.id)}
                            disabled={isDeleting === analysis.id}
                        >
                            {isDeleting === analysis.id ? (
                              <Loader2 className="h-4 w-4 animate-spin"/>
                            ) : (
                              <Trash2 className="h-4 w-4" />
                            )}
                        </Button>
                    </div>

                    <CardHeader className="pb-3">
                        <CardTitle className="text-base font-medium truncate pr-10 flex items-center gap-2">
                          <FileText className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                          {analysis.filename}
                        </CardTitle>
                    </CardHeader>

                    <CardContent className="space-y-4">
                        {/* Status & Date Row */}
                        <div className="flex justify-between items-center">
                            <span className={`capitalize px-2.5 py-1 rounded-full text-xs font-medium border ${getStatusStyles(analysis.status)}`}>
                                {analysis.status}
                            </span>
                            <span className="text-xs text-muted-foreground flex items-center gap-1">
                                <Calendar className="h-3 w-3" />
                                {formatDate(analysis.created_at)}
                            </span>
                        </div>

                        {/* Stats */}
                        {analysis.status === 'completed' && (
                            <div className="pt-2 border-t border-border/50">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <p className="text-2xl font-bold text-primary">
                                            {analysis.subscriptions_found}
                                        </p>
                                        <p className="text-xs text-muted-foreground">
                                            subscriptions
                                        </p>
                                    </div>
                                    {analysis.potential_savings_eur > 0 && (
                                        <div className="text-right">
                                            <p className="text-lg font-semibold text-amber-600 dark:text-amber-400 flex items-center gap-1">
                                                <TrendingUp className="h-4 w-4" />
                                                €{analysis.potential_savings_eur.toFixed(0)}
                                            </p>
                                            <p className="text-xs text-muted-foreground">
                                                /month savings
                                            </p>
                                        </div>
                                    )}
                                </div>
                            </div>
                        )}

                        {/* Processing State */}
                        {analysis.status === 'processing' && (
                            <div className="pt-2 border-t border-border/50 flex items-center gap-2 text-sm text-muted-foreground">
                                <Loader2 className="h-4 w-4 animate-spin" />
                                Analyzing...
                            </div>
                        )}

                        {/* View Details */}
                        <div className="flex items-center justify-end text-xs text-muted-foreground group-hover:text-primary transition-colors">
                            View details
                            <ChevronRight className="h-3 w-3 ml-1 group-hover:translate-x-1 transition-transform" />
                        </div>
                    </CardContent>
                </Card>
            ))}

            {/* Empty State */}
            {analyses.length === 0 && (
                <div className="col-span-full">
                    <div className="text-center py-16 border-2 border-dashed rounded-2xl bg-muted/30">
                        <div className="mx-auto w-16 h-16 rounded-full bg-muted flex items-center justify-center mb-4">
                            <FileText className="h-8 w-8 text-muted-foreground" />
                        </div>
                        <h3 className="text-lg font-medium mb-2">No analyses yet</h3>
                        <p className="text-muted-foreground max-w-sm mx-auto">
                            Upload your first bank statement above to discover your hidden subscriptions.
                        </p>
                    </div>
                </div>
            )}
        </div>
      </div>
    </div>
  )
}

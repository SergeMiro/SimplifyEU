"use client"

import { useState, useEffect } from "react"
import { useParams, useRouter } from "next/navigation"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { SubscriptionCard } from "@/components/subscription-card"
import { authClient, getAuthToken } from "@/lib/auth-client"
import { toast } from "sonner"
import { 
    ArrowLeft, 
    Download, 
    Mail, 
    Loader2, 
    CheckCircle2, 
    XCircle, 
    Clock,
    TrendingUp,
    CreditCard,
    Sparkles,
    X
} from "lucide-react"

const API_URL = process.env.NEXT_PUBLIC_SUBSCRIPTION_SERVICE_URL || "http://localhost:8001/v1";
const API_KEY = process.env.NEXT_PUBLIC_SUBSCRIPTION_API_KEY || "demo-key";

export default function AnalysisResultPage() {
    const params = useParams()
    const router = useRouter()
    const analysisId = params.analysisId as string
    const [analysis, setAnalysis] = useState<any>(null)
    const [loading, setLoading] = useState(true)
    const [downloadingPdf, setDownloadingPdf] = useState(false)
    const [sendingEmail, setSendingEmail] = useState(false)
    const [showEmailModal, setShowEmailModal] = useState(false)
    const [emailAddress, setEmailAddress] = useState("")
    const [emailConfigured, setEmailConfigured] = useState(false)

    useEffect(() => {
        let interval: NodeJS.Timeout

        const fetchAnalysis = async () => {
            try {
                const { data: session } = await authClient.getSession()
                const accountId = session?.user?.id || "00000000-0000-0000-0000-000000000000"
                const token = await getAuthToken()
                const headers = {
                    ...(token ? { Authorization: `Bearer ${token}` } : {}),
                    "X-API-Key": API_KEY,
                    "X-Account-ID": accountId,
                    "X-User-ID": session?.user?.id || "anonymous",
                }

                const res = await fetch(`${API_URL}/analyses/${analysisId}`, { headers })
                if (res.ok) {
                    const data = await res.json()
                    setAnalysis(data)
                    if (data.status === 'completed' || data.status === 'failed') {
                        setLoading(false)
                        clearInterval(interval)
                    }
                }
            } catch (e) {
                console.error(e)
            }
        }

        const checkEmailStatus = async () => {
            try {
                const res = await fetch(`${API_URL}/capabilities`)
                if (res.ok) {
                    const data = await res.json()
                    setEmailConfigured(data.email_support?.available || false)
                }
            } catch (e) {
                console.warn("Could not check email status")
            }
        }

        fetchAnalysis()
        checkEmailStatus()
        interval = setInterval(fetchAnalysis, 2000)

        return () => clearInterval(interval)
    }, [analysisId])

    const downloadReport = async () => {
        setDownloadingPdf(true)
        try {
             const { data: session } = await authClient.getSession()
             const accountId = session?.user?.id || "00000000-0000-0000-0000-000000000000"
             const token = await getAuthToken()

             const response = await fetch(`${API_URL}/analyses/${analysisId}/report`, {
                headers: {
                    ...(token ? { Authorization: `Bearer ${token}` } : {}),
                    "X-API-Key": API_KEY,
                    "X-Account-ID": accountId,
                    "X-User-ID": session?.user?.id || "anonymous",
                }
             })

             if (response.ok) {
                 const blob = await response.blob()
                 const url = window.URL.createObjectURL(blob)
                 const a = document.createElement('a')
                 a.href = url
                 a.download = `SimplifyEU_Report_${analysisId}.pdf`
                 document.body.appendChild(a)
                 a.click()
                 window.URL.revokeObjectURL(url)
                 toast.success("Report downloaded!")
             } else {
                 throw new Error("Download failed")
             }
        } catch (e) {
            console.error(e)
            toast.error("Failed to download report")
        } finally {
            setDownloadingPdf(false)
        }
    }

    const sendReportEmail = async () => {
        if (!emailAddress || !emailAddress.includes('@')) {
            toast.error("Please enter a valid email address")
            return
        }

        setSendingEmail(true)
        try {
            const { data: session } = await authClient.getSession()
            const accountId = session?.user?.id || "00000000-0000-0000-0000-000000000000"
            const token = await getAuthToken()

            const response = await fetch(`${API_URL}/analyses/${analysisId}/send-report`, {
                method: "POST",
                headers: {
                    ...(token ? { Authorization: `Bearer ${token}` } : {}),
                    "X-API-Key": API_KEY,
                    "X-Account-ID": accountId,
                    "X-User-ID": session?.user?.id || "anonymous",
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    email: emailAddress,
                    include_pdf: true
                })
            })

            if (response.ok) {
                toast.success(`Report sent to ${emailAddress}!`)
                setShowEmailModal(false)
                setEmailAddress("")
            } else {
                const error = await response.json()
                throw new Error(error.detail || "Failed to send email")
            }
        } catch (e: any) {
            console.error(e)
            toast.error(e.message || "Failed to send email")
        } finally {
            setSendingEmail(false)
        }
    }

    const getStatusIcon = (status: string) => {
        switch (status) {
            case 'completed':
                return <CheckCircle2 className="h-6 w-6 text-green-500" />
            case 'failed':
                return <XCircle className="h-6 w-6 text-red-500" />
            case 'processing':
                return <Loader2 className="h-6 w-6 text-blue-500 animate-spin" />
            default:
                return <Clock className="h-6 w-6 text-yellow-500" />
        }
    }

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'completed':
                return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
            case 'failed':
                return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
            case 'processing':
                return 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
            default:
                return 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
        }
    }

    if (!analysis) return (
        <div className="flex items-center justify-center min-h-[60vh]">
            <div className="text-center space-y-4">
                <Loader2 className="h-12 w-12 animate-spin text-primary mx-auto" />
                <p className="text-muted-foreground">Loading analysis...</p>
            </div>
        </div>
    )

    return (
        <div className="container mx-auto py-10 space-y-8">
            {/* Header */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div className="flex items-center gap-4">
                    <Button 
                        variant="ghost" 
                        size="icon"
                        onClick={() => router.push('/dashboard/services/subscription-detector')}
                    >
                        <ArrowLeft className="h-5 w-5" />
                    </Button>
                    <div>
                        <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-violet-600">
                            Analysis Results
                        </h1>
                        <p className="text-sm text-muted-foreground mt-1">
                            {analysis.filename} • {new Date(analysis.created_at).toLocaleDateString()}
                        </p>
                    </div>
                </div>
                
                {analysis.status === 'completed' && (
                    <div className="flex items-center gap-2">
                        {emailConfigured && (
                            <Button 
                                variant="outline"
                                onClick={() => setShowEmailModal(true)}
                                className="gap-2"
                            >
                                <Mail className="h-4 w-4" />
                                Send to Email
                            </Button>
                        )}
                        <Button 
                            onClick={downloadReport}
                            disabled={downloadingPdf}
                            className="bg-gradient-to-r from-blue-600 to-violet-600 hover:from-blue-700 hover:to-violet-700 text-white gap-2"
                        >
                            {downloadingPdf ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                                <Download className="h-4 w-4" />
                            )}
                            Download PDF
                        </Button>
                    </div>
                )}
            </div>

            {/* Summary Cards */}
            <div className="grid gap-4 md:grid-cols-3">
                <Card className="relative overflow-hidden">
                    <div className="absolute top-0 right-0 w-20 h-20 bg-gradient-to-br from-primary/10 to-transparent rounded-bl-full" />
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                            <div className={`p-1.5 rounded-lg ${getStatusColor(analysis.status)}`}>
                                {getStatusIcon(analysis.status)}
                            </div>
                            Status
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className={`text-2xl font-bold capitalize inline-flex px-3 py-1 rounded-full text-sm ${getStatusColor(analysis.status)}`}>
                            {analysis.status}
                        </div>
                        {analysis.source_type && (
                            <p className="text-xs text-muted-foreground mt-2">
                                Source: {analysis.source_type.toUpperCase()}
                            </p>
                        )}
                    </CardContent>
                </Card>

                <Card className="relative overflow-hidden">
                    <div className="absolute top-0 right-0 w-20 h-20 bg-gradient-to-br from-blue-500/10 to-transparent rounded-bl-full" />
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                            <div className="p-1.5 rounded-lg bg-blue-100 dark:bg-blue-900/30">
                                <CreditCard className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                            </div>
                            Subscriptions Found
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-4xl font-bold text-blue-600 dark:text-blue-400">
                            {analysis.subscriptions_found || 0}
                        </div>
                        <p className="text-xs text-muted-foreground mt-1">
                            {analysis.total_transactions || 0} transactions analyzed
                        </p>
                    </CardContent>
                </Card>

                <Card className="relative overflow-hidden">
                    <div className="absolute top-0 right-0 w-20 h-20 bg-gradient-to-br from-amber-500/10 to-transparent rounded-bl-full" />
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                            <div className="p-1.5 rounded-lg bg-amber-100 dark:bg-amber-900/30">
                                <TrendingUp className="h-5 w-5 text-amber-600 dark:text-amber-400" />
                            </div>
                            Potential Savings
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-4xl font-bold text-amber-600 dark:text-amber-400">
                            €{analysis.potential_savings_eur?.toFixed(2) || '0.00'}
                        </div>
                        <p className="text-xs text-muted-foreground mt-1">per month</p>
                    </CardContent>
                </Card>
            </div>

            {/* Items */}
            {analysis.status === 'completed' && (
                <div className="space-y-4">
                    <div className="flex items-center gap-2">
                        <Sparkles className="h-5 w-5 text-primary" />
                        <h2 className="text-xl font-semibold">Detected Subscriptions</h2>
                    </div>
                    <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                        {analysis.items?.map((item: any) => (
                            <SubscriptionCard key={item.id} item={item} />
                        ))}
                    </div>
                    {(!analysis.items || analysis.items.length === 0) && (
                        <div className="text-center py-10 border-2 border-dashed rounded-lg">
                            <p className="text-muted-foreground">No subscriptions detected in this statement.</p>
                        </div>
                    )}
                </div>
            )}

            {analysis.status === 'processing' && (
                <div className="text-center py-20 space-y-4">
                    <div className="relative mx-auto w-20 h-20">
                        <div className="absolute inset-0 rounded-full border-4 border-primary/20" />
                        <div className="absolute inset-0 rounded-full border-4 border-primary border-t-transparent animate-spin" />
                    </div>
                    <p className="text-xl text-muted-foreground">Analyzing transactions...</p>
                    <p className="text-sm text-muted-foreground">This may take a few moments</p>
                </div>
            )}

            {analysis.status === 'failed' && (
                <div className="text-center py-20 space-y-4">
                    <XCircle className="h-16 w-16 text-destructive mx-auto" />
                    <p className="text-xl text-destructive">Analysis Failed</p>
                    <p className="text-sm text-muted-foreground max-w-md mx-auto">
                        {analysis.error_message || "An error occurred during analysis. Please try again with a different file."}
                    </p>
                    <Button 
                        variant="outline"
                        onClick={() => router.push('/dashboard/services/subscription-detector')}
                    >
                        Try Another File
                    </Button>
                </div>
            )}

            {/* Email Modal */}
            {showEmailModal && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                    <Card className="w-full max-w-md">
                        <CardHeader className="flex flex-row items-center justify-between">
                            <CardTitle>Send Report via Email</CardTitle>
                            <Button 
                                variant="ghost" 
                                size="icon"
                                onClick={() => setShowEmailModal(false)}
                            >
                                <X className="h-4 w-4" />
                            </Button>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="space-y-2">
                                <label className="text-sm font-medium">Email Address</label>
                                <Input
                                    type="email"
                                    placeholder="your@email.com"
                                    value={emailAddress}
                                    onChange={(e) => setEmailAddress(e.target.value)}
                                    onKeyDown={(e) => e.key === 'Enter' && sendReportEmail()}
                                />
                            </div>
                            <p className="text-xs text-muted-foreground">
                                We'll send a beautiful HTML report with PDF attachment to this address.
                            </p>
                            <div className="flex gap-2 justify-end">
                                <Button 
                                    variant="outline"
                                    onClick={() => setShowEmailModal(false)}
                                >
                                    Cancel
                                </Button>
                                <Button 
                                    onClick={sendReportEmail}
                                    disabled={sendingEmail}
                                    className="bg-gradient-to-r from-blue-600 to-violet-600 hover:from-blue-700 hover:to-violet-700 text-white"
                                >
                                    {sendingEmail ? (
                                        <>
                                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                            Sending...
                                        </>
                                    ) : (
                                        <>
                                            <Mail className="mr-2 h-4 w-4" />
                                            Send Report
                                        </>
                                    )}
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                </div>
            )}
        </div>
    )
}

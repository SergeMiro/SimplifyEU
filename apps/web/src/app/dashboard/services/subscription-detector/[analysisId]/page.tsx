"use client"

import { useState, useEffect } from "react"
import { useParams } from "next/navigation"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { SubscriptionCard } from "@/components/subscription-card"
import { createClient } from "@/lib/supabase/client"

const API_URL = process.env.NEXT_PUBLIC_SUBSCRIPTION_SERVICE_URL || "http://localhost:8001/v1";
const API_KEY = process.env.NEXT_PUBLIC_SUBSCRIPTION_API_KEY || "demo-key";

export default function AnalysisResultPage() {
    const params = useParams()
    const analysisId = params.analysisId as string
    const [analysis, setAnalysis] = useState<any>(null)
    const [loading, setLoading] = useState(true)
    const supabase = createClient()

    useEffect(() => {
        let interval: NodeJS.Timeout

        const fetchAnalysis = async () => {
            try {
                const { data: { session } } = await supabase.auth.getSession()
                const accountId = session?.user?.id || "00000000-0000-0000-0000-000000000000"
                const headers = {
                    "X-API-Key": API_KEY,
                    "X-Account-ID": accountId,
                    "X-User-ID": session?.user?.id || "",
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

        fetchAnalysis()
        interval = setInterval(fetchAnalysis, 2000) // Poll every 2s

        return () => clearInterval(interval)
    }, [analysisId])

    const downloadReport = async () => {
        try {
             const { data: { session } } = await supabase.auth.getSession()
             const accountId = session?.user?.id || "00000000-0000-0000-0000-000000000000"

             const response = await fetch(`${API_URL}/analyses/${analysisId}/report`, {
                headers: {
                    "X-API-Key": API_KEY,
                    "X-Account-ID": accountId,
                    "X-User-ID": session?.user?.id || "",
                }
             })

             if (response.ok) {
                 const blob = await response.blob()
                 const url = window.URL.createObjectURL(blob)
                 const a = document.createElement('a')
                 a.href = url
                 a.download = `report-${analysisId}.pdf`
                 document.body.appendChild(a)
                 a.click()
                 window.URL.revokeObjectURL(url)
             }
        } catch (e) {
            console.error(e)
        }
    }

    if (!analysis) return <div className="p-10 text-center">Loading...</div>

    return (
        <div className="container mx-auto py-10 space-y-8">
            <div className="flex justify-between items-center">
                <h1 className="text-3xl font-bold">Analysis Results</h1>
                <div className="space-x-2">
                    {analysis.status === 'completed' && (
                         <Button onClick={downloadReport}>Download PDF Report</Button>
                    )}
                </div>
            </div>

            {/* Summary */}
            <div className="grid gap-4 md:grid-cols-3">
                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium">Status</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold capitalize">{analysis.status}</div>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium">Subscriptions Found</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{analysis.subscriptions_found}</div>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium">Potential Savings</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">€{analysis.potential_savings_eur?.toFixed(2)}</div>
                    </CardContent>
                </Card>
            </div>

            {/* Items */}
            {analysis.status === 'completed' && (
                <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                    {analysis.items?.map((item: any) => (
                        <SubscriptionCard key={item.id} item={item} />
                    ))}
                </div>
            )}

            {analysis.status === 'processing' && (
                <div className="text-center py-20">
                    <p className="text-xl text-muted-foreground animate-pulse">Analyzing transactions...</p>
                </div>
            )}
        </div>
    )
}
